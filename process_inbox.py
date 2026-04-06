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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL") # Используем тот же прокси, что и для Telegram

ALLOWED_FOLDERS = ["03_Knowledge_Base/AI_Hub", "03_Knowledge_Base/Concepts", "03_Knowledge_Base/Sources", "04_Projects"]

def get_yt_id(url):
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', r'youtu\.be\/([0-9A-Za-z_-]{11})']
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def get_yt_transcript(video_id):
    if not HAS_YT_API: return None
    try:
        proxies = None
        if PROXY_URL:
            proxies = {"http": PROXY_URL, "https": PROXY_URL}
        
        # Исправленный вызов согласно dir(): list вместо list_transcripts
        transcript_list = YouTubeTranscriptApi.list(video_id, proxies=proxies)
        transcript = transcript_list.find_transcript(['ru', 'en'])
        return " ".join([t['text'] for t in transcript.fetch()])
    except Exception as e:
        logger.warning(f"YT Transcript fall: {e}")
        return None

def get_yt_oembed(url):
    logger.info(f"--- YT OEMBED: {url} ---")
    try:
        # oEmbed не требует авторизации и часто работает без прокси
        api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        with urllib.request.urlopen(api_url, timeout=10) as res:
            data = json.loads(res.read().decode())
            return f"TITLE: {data.get('title')}\nAUTHOR: {data.get('author_name')}"
    except Exception as e:
        logger.warning(f"YT oEmbed fail: {e}")
        return None

def get_yt_metadata(url):
    if not HAS_YT_DLP: return None
    logger.info(f"--- YT-DLP METADATA: {url} ---")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
    }
    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            description = info.get('description', 'No description available')
            return f"TITLE: {title}\nDESCRIPTION: {description}"
    except Exception as e:
        logger.error(f"YT-DLP error: {e}")
        return None

def scrape_url(url):
    # Пытаемся сначала через YouTube API
    yt_id = get_yt_id(url)
    if yt_id:
        # Каскад: Транскрипт -> oEmbed -> yt-dlp
        transcript = get_yt_transcript(yt_id)
        if transcript:
            logger.info(f"--- YT-API УСПЕХ: {yt_id} ---")
            return f"[YouTube Transcript]\n{transcript[:15000]}"
        
        oembed = get_yt_oembed(url)
        if oembed:
             return f"[YouTube oEmbed Metadata]\n{oembed}"
        
        # Если даже oEmbed не сработал (редко), пробуем yt-dlp
        metadata = get_yt_metadata(url)
        if metadata:
            return f"[YouTube Metadata (yt-dlp)]\n{metadata}"

    # Если не YouTube или API не сработало — используем Firecrawl
    if not FIRECRAWL_API_KEY: return "No Firecrawl key"
    if yt_id:
         # Для YouTube ссылок Firecrawl часто выдает 408/403, если основной метод провалился, 
         # скорее всего и тут будет ошибка, но попробуем.
         logger.info(f"--- FIRECRAWL (Fallback for YT): {url} ---")
    else:
         logger.info(f"--- FIRECRAWL СКРАПИНГ: {url} ---")
         
    try:
        data = json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True}).encode()
        req = urllib.request.Request("https://api.firecrawl.dev/v1/scrape", data=data, 
                                     headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as res:
            text = json.loads(res.read().decode()).get("data", {}).get("markdown", "")
            if not text: return "Scrape result is empty"
            return text[:12000]
    except Exception as e: 
        logger.error(f"Scrape failed: {e}")
        return f"ERROR_SCRAPING: {e}"

def clean_json(text):
    text = re.sub(r'^```json\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
    try: return json.loads(text)
    except:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(1))
        raise

def process_file(path):
    logger.info(f"=== ОБРАБОТКА: {path.name} ===")
    raw_input = path.read_text(encoding="utf-8")
    urls = re.findall(r'https?://[^\s]+', raw_input)
    scraped_content = scrape_url(urls[0]) if urls else ""

    system_prompt = f"""Ты — Профессиональный PKM-Аналитик (Obsidian Specialist).
Твоя задача: Создать глубокую, визуально богатую заметку.

ИСПОЛЬЗУЙ СТАНДАРТЫ OBSIDIAN:
- Callouts: > [!info], > [!important], > [!tip] для акцентов.
- Highlights: ==термины== для выделения.
- Фреймворк: STAR (Situation, Task, Action, Result) и R-I-S-E.

ОСОБЫЕ ИНСТРУКЦИИ:
- Если контент содержит "ERROR_SCRAPING", НЕ АНАЛИЗИРУЙ ТЕКСТ ОШИБКИ. Вместо этого напиши, что данные не удалось извлечь, и оформи заметку на основе ссылки и доступных метаданных.
- Если доступен только [YouTube oEmbed Metadata] или [YouTube Metadata (yt-dlp)], сделай резюме на основе заголовка и автора/описания видео. Сформулируй краткое содержание исходя из темы, указанной в заголовке.

Верни JSON:
- meta_title (RU)
- meta_source (URL)
- meta_description (1 sentence)
- meta_tags (list)
- content_summary (используй highlights)
- content_star (STAR блок с использованием callouts)
- content_insights (список инсайтов)
- official_description (метаданные/описание из скрапинга)
- target_folder (из {ALLOWED_FOLDERS})
- filename (En_snake_case)"""

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"ВВОДНЫЕ:\n{raw_input}\n\nКОНТЕНТ:\n{scraped_content}"}
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            res = clean_json(json.loads(response.read().decode())["choices"][0]["message"]["content"])
            
            tags_list = "\n".join([f"  - {t}" for t in res.get("meta_tags", ["brain"])])
            
            final_note = f"""---
date: {datetime.now().strftime('%Y-%m-%d')}
source: "{res.get('meta_source', '')}"
tags:
{tags_list}
status: processed
description: "{res.get('meta_description', '').replace('"', "'")}"
---

# {res.get('meta_title', 'Без названия')}

## 📝 Краткое Резюме
{res.get('content_summary', '')}

## 🚀 Анализ STAR (Situation, Task, Action, Result)
{res.get('content_star', '')}

## 💡 Ключевые идеи и Инсайты
{res.get('content_insights', '')}

## 📋 Оригинальное Описание
> [!info] Источник
> {res.get('official_description', 'Детали извлечены из контента.')}

## 🔗 Ресурсы
- Оригинал: {res.get('meta_source', '')}
"""
            target = res.get("target_folder", "03_Knowledge_Base/Sources")
            dest = VAULT_DIR / (target if target in ALLOWED_FOLDERS else "03_Knowledge_Base/Sources")
            dest.mkdir(parents=True, exist_ok=True)
            fname = re.sub(r'[^a-zA-Z0-9_]', '_', res.get("filename", "note")).strip("_") + ".md"
            (dest / fname).write_text(final_note, encoding="utf-8")
            path.unlink()
            logger.info(f"=== УСПЕХ (PRO): {fname} ===")
    except Exception as e: logger.error(f"Error: {e}")

if __name__ == "__main__":
    if INBOX_DIR.exists():
        for f in list(INBOX_DIR.glob("*.md")): process_file(f)
