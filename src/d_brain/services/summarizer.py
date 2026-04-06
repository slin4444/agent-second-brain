import os, json, logging, asyncio, urllib.request, re
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=Path("/root/agent-second-brain/.env") if os.name != 'nt' else Path(".env"))

VAULT_DIR = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "/root/Second_Brain"))
DAILY_DIR = VAULT_DIR / "02_AI_Review" / "Daily"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_html(html_text):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # Очистка текста от лишних markdown-артефактов, если они пролезли
        clean_html = re.sub(r'---.*?---', '', html_text, flags=re.DOTALL)
        clean_html = clean_html.replace("```markdown", "").replace("```", "").strip()
        
        limit = 4000
        parts = [clean_html[i:i+limit] for i in range(0, len(clean_html), limit)]
        
        for part in parts:
            data = json.dumps({
                "chat_id": CHAT_ID, 
                "text": part, 
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }).encode()
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            try:
                urllib.request.urlopen(req, timeout=15)
            except Exception as e:
                logger.error(f"HTML send failed, fallback to plain text: {e}")
                # Fallback to plain text WITHOUT tags
                plain_text = re.sub('<[^<]+?>', '', part)
                data_plain = json.dumps({"chat_id": CHAT_ID, "text": plain_text}).encode()
                req_plain = urllib.request.Request(url, data=data_plain, headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req_plain, timeout=15)

    except Exception as e: logger.error(f"Telegram general error: {e}")

async def generate_summary():
    logger.info("🎬 ГЕНЕРАЦИЯ ЕЖЕДНЕВНОЙ СВОДКИ (HTML-PREMIUM)...")
    yesterday = datetime.now() - timedelta(days=1)
    notes = []
    
    KB_DIRS = [VAULT_DIR / "03_Knowledge_Base", VAULT_DIR / "04_Projects"]
    
    for kb_dir in KB_DIRS:
        if not kb_dir.exists(): continue
        for note_file in kb_dir.rglob("*.md"):
            try:
                if datetime.fromtimestamp(note_file.stat().st_mtime) > yesterday:
                    content = note_file.read_text(encoding='utf-8')[:600]
                    notes.append(f"ФАЙЛ: [[{note_file.stem}]]\nТЕКСТ:\n{content}")
            except: continue
    
    if not notes: return

    prompt = f"""Ты — Профессиональный Редактор Знаний. Сделай итоговый отчет дня.

ДЛЯ TELEGRAM (используй СТРОГО HTML):
- Используй <b>ЖИРНЫЙ</b> для заголовков.
- Используй <i>КУРСИВ</i> для ключевых слов.
- Объединяй заметки по смыслу (Категории).
- Для ссылок на Obsidian используй точное имя файла в [[скобках]].
- Добавь в конце блок "🎯 ACTION ITEMS" (что нужно сделать на основе этих знаний).

ДАННЫЕ ЗА ДЕНЬ {datetime.now().strftime('%Y-%m-%d')}:
""" + "\n\n".join(notes)

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": "Будь лаконичен, структурно безупречен. Используй русский язык."}, 
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            res = json.loads(response.read().decode())["choices"][0]["message"]["content"]
            
            # Сохранение в Obsidian (как Markdown)
            DAILY_DIR.mkdir(parents=True, exist_ok=True)
            (DAILY_DIR / f"Summary_{datetime.now().strftime('%Y-%m-%d')}.md").write_text(res, encoding="utf-8")
            (DAILY_DIR / "Summary_Latest.md").write_text(res, encoding="utf-8")
            
            # Отправка в Telegram (через HTML)
            send_telegram_html(res)
            logger.info("✅ СВОДКА УСПЕШНО ОТПРАВЛЕНА!")
    except Exception as e: logger.error(f"Summary generator error: {e}")

if __name__ == "__main__":
    asyncio.run(generate_summary())
