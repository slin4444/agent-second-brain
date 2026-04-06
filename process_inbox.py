# -*- coding: utf-8 -*-
import os, json, logging, urllib.request, re, sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Попытка импорта YouTube API и yt-dlp
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT_API = True
except ImportError:
    HAS_YT_API = False

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path("/root/agent-second-brain/.env") if os.name != 'nt' else Path(".env"))

VAULT_DIR = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "/root/Second_Brain"))
INBOX_DIR = VAULT_DIR / "01_Inbox" / "Telegram"
WIKI_DIR = VAULT_DIR / "03_Knowledge_Base"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL")

# Папки для распределения
WIKI_PATHS = {
    "source": WIKI_DIR / "sources",
    "entity": WIKI_DIR / "entities",
    "concept": WIKI_DIR / "concepts",
    "analysis": WIKI_DIR / "analysis"
}

def get_yt_id(url):
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r'youtu\.be\/([0-9A-Za-z_-]{11})']
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def get_yt_transcript(video_id):
    if not HAS_YT_API: return None
    try:
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        transcript_list = YouTubeTranscriptApi.list(video_id, proxies=proxies)
        transcript = transcript_list.find_transcript(['ru', 'en'])
        return " ".join([t['text'] for t in transcript.fetch()])
    except Exception as e:
        logger.warning(f"YT Transcript fail: {e}")
        return None

def get_yt_oembed(url):
    try:
        api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        with urllib.request.urlopen(api_url, timeout=10) as res:
            data = json.loads(res.read().decode())
            return f"TITLE: {data.get('title')}\nAUTHOR: {data.get('author_name')}"
    except Exception as e:
        logger.warning(f"YT oEmbed fail: {e}")
        return None

def get_yt_metadata(url):
    if not HAS_YT_DLP: return None
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True}
    if PROXY_URL: ydl_opts['proxy'] = PROXY_URL
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return f"TITLE: {info.get('title', 'Unknown')}\nDESCRIPTION: {info.get('description', '')}"
    except: return None

def scrape_url(url):
    yt_id = get_yt_id(url)
    if yt_id:
        transcript = get_yt_transcript(yt_id)
        if transcript: return True, f"[YouTube Transcript]\n{transcript[:15000]}"
        oembed = get_yt_oembed(url)
        if oembed: return True, f"[YouTube oEmbed Metadata]\n{oembed}"
        metadata = get_yt_metadata(url)
        if metadata: return True, f"[YouTube Metadata (yt-dlp)]\n{metadata}"

    if not FIRECRAWL_API_KEY: return False, "No Firecrawl key"
    try:
        data = json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True}).encode()
        req = urllib.request.Request("https://api.firecrawl.dev/v1/scrape", data=data, 
                                     headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"})
        # Увеличен таймаут до 90 секунд для стабильности
        with urllib.request.urlopen(req, timeout=90) as res:
            text = json.loads(res.read().decode()).get("data", {}).get("markdown", "")
            if not text: return False, "Empty content"
            return True, text[:12000]
    except Exception as e: return False, f"HTTP Error {e}"

def read_wiki_context():
    idx = WIKI_DIR / "index.md"
    hot = WIKI_DIR / "hot.md"
    ctx = ""
    if idx.exists(): ctx += f"--- CURRENT INDEX ---\n{idx.read_text(encoding='utf-8')[:3000]}\n"
    if hot.exists(): ctx += f"--- HOT CACHE ---\n{hot.read_text(encoding='utf-8')[:1000]}\n"
    return ctx

def clean_json(text):
    text = re.sub(r'^```json\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
    try: return json.loads(text)
    except:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(1))
        raise

def process_file(path):
    logger.info(f"=== WIKI INGEST: {path.name} ===")
    raw_input = path.read_text(encoding="utf-8")
    urls = re.findall(r'https?://[^\s]+', raw_input)
    
    success, scraped_content = (True, "")
    if urls:
        success, scraped_content = scrape_url(urls[0])
    
    context = read_wiki_context()
    
    # Режим обработки ошибок в промпте
    error_instr = ""
    if not success:
        logger.warning(f"SCRAPE FAILED for {path.name}: {scraped_content}")
        error_instr = f"\n!!! ВНИМАНИЕ: Контент по ссылке НЕ ПОЛУЧЕН (Ошибка: {scraped_content}). Создай КРАТКУЮ заметку-заглушку (Stub) только на основе текста пользователя. Поставь статус 'stub' в YAML.\n"

    system_prompt = f"""Ты — Expert LLM Wiki Maintainer (на основе паттерна Карпатого).
Твоя задача: Разложить входящий контент на составляющие базы знаний.

ЯЗЫКОВАЯ ПОЛИТИКА:
- ВСЕГДА создавай контент (content) на РУССКОМ языке, даже если источник на английском.
- Имена файлов (path) оставляй на английском (snake_case).

{error_instr}
ИНСТРУКЦИИ:
1. Изучи ТЕКУЩИЙ ИНДЕКС, чтобы найти существующие связи.
2. Создай ОСНОВНУЮ заметку (Source) по стандартам STAR/RISE.
3. Выдели СУЩНОСТИ (Инструменты, Люди) и КОНЦЕПЦИИ (Технологии, Идеи).
4. Если сущность/концепция уже есть в индексе — предложи ОБНОВЛЕНИЕ файла. Если нет — предложи СОЗДАНИЕ.
5. Обнови INDEX и LOG.

ВЫХОДНЫЕ ДАННЫЕ (только JSON):
{{
  "actions": [
    {{
      "type": "create",
      "path": "sources/filename.md",
      "content": "Полный текст заметки по стандартам STAR/RISE/Callouts"
    }},
    {{
      "type": "update_or_create",
      "path": "entities/entity_name.md",
      "content": "Краткое описание сущности со ссылкой на исходный source"
    }},
    {{
      "type": "log",
      "entry": "## [DATE] ingest | Title (Short desc)"
    }},
    {{
      "type": "index_update",
      "category": "Concepts|Entities|Sources",
      "line": "- [[Link]] | Краткое описание"
    }}
  ],
  "hot_cache_update": "Кратчайшая выжимка (50 слов) для hot.md"
}}"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"WIKI CONTEXT:\n{context}\n\nINPUT:\n{raw_input}\n\nCONTENT:\n{scraped_content}"}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            res = clean_json(json.loads(response.read().decode())["choices"][0]["message"]["content"])
            
            # Обработка действий
            for action in res.get("actions", []):
                a_type = action.get("type")
                if a_type in ["create", "update_or_create"]:
                    p = WIKI_DIR / action.get("path")
                    p.parent.mkdir(parents=True, exist_ok=True)
                    if a_type == "update_or_create" and p.exists():
                        old_content = p.read_text(encoding="utf-8")
                        new_content = old_content + "\n\n### Update " + datetime.now().strftime('%Y-%m-%d') + "\n" + action.get("content")
                        p.write_text(new_content, encoding="utf-8")
                    else:
                        p.write_text(action.get("content"), encoding="utf-8")
                
                elif a_type == "log":
                    lp = WIKI_DIR / "log.md"
                    entry = action.get("entry").replace("[DATE]", datetime.now().strftime('%Y-%m-%d'))
                    if lp.exists():
                        log_content = lp.read_text(encoding="utf-8")
                        lp.write_text(log_content + "\n" + entry, encoding="utf-8")

                elif a_type == "index_update":
                    ip = WIKI_DIR / "index.md"
                    if ip.exists():
                        idx_text = ip.read_text(encoding="utf-8")
                        cat = action.get("category")
                        line = action.get("line")
                        # Гибкий поиск заголовка (игнорируем эмодзи и лишние пробелы)
                        pattern = rf"(###\s*.*{cat}.*)"
                        if re.search(pattern, idx_text) and line not in idx_text:
                            idx_text = re.sub(pattern, rf"\1\n{line}", idx_text, count=1)
                            ip.write_text(idx_text, encoding="utf-8")

            # Обновление Hot Cache
            hp = WIKI_DIR / "hot.md"
            hot_text = res.get("hot_cache_update", "")
            if hot_text:
                hp.write_text(f"# 🔥 Hot Cache\n> Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{hot_text}", encoding="utf-8")

            # Логика очистки/карантина
            if success:
                path.unlink()
                logger.info(f"=== SUCCESS (PRO): {res.get('actions', [{}])[0].get('path', 'unknown')} ===")
            else:
                err_path = INBOX_DIR.parent / "Errors" / path.name
                path.replace(err_path)
                logger.warning(f"=== MOVED TO ERRORS: {path.name} ===")
    except Exception as e: logger.error(f"Wiki Ingest Error: {e}")

if __name__ == "__main__":
    if INBOX_DIR.exists():
        for f in list(INBOX_DIR.glob("*.md")): process_file(f)
