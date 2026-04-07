import os
import re
import time
import logging
import tempfile
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramListener")

URL_PATTERN = re.compile(r'https?://[^\s]+')


class TelegramListener:

    def __init__(self):
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channels_str = os.getenv("TELEGRAM_CHANNELS", "")
        self.vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        self.proxy_url = os.getenv("TELEGRAM_PROXY_URL", "")
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "")
        self._validate_config()
        self.channels = [c.strip().lower().lstrip("@") for c in self.channels_str.split(",") if c.strip()]
        self.output_dir = Path(self.vault_path) / "01_Inbox" / "Telegram"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.web_dir = Path(self.vault_path) / "01_Inbox" / "Web"
        self.web_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0
        self.proxies = {"http": self.proxy_url, "https": self.proxy_url} if self.proxy_url else None
        if self.proxies:
            logger.info("Используется прокси для запросов к Telegram API")

    def _validate_config(self):
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN отсутствует в .env")
        if not self.vault_path:
            raise ValueError("OBSIDIAN_VAULT_PATH отсутствует в .env")
        if not self.firecrawl_key:
            logger.warning("FIRECRAWL_API_KEY не задан — скрейпинг URL отключён")
        logger.info(f"Target Channels: {self.channels_str}")

    def get_updates(self):
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.offset, "timeout": 30}
            resp = requests.get(url, params=params, timeout=40, proxies=self.proxies)
            if resp.status_code == 200:
                return resp.json().get("result", [])
            logger.error(f"Ошибка получения обновлений: {resp.text}")
            return []
        except Exception as e:
            logger.error(f"Ошибка соединения: {e}")
            time.sleep(5)
            return []

    def process_update(self, update):
        self.offset = update["update_id"] + 1
        message = update.get("channel_post") or update.get("message")
        if not message:
            return
        chat = message.get("chat", {})
        chat_username = chat.get("username", "").lower()
        chat_title = chat.get("title", "Private")
        is_targeted = chat_username in self.channels
        is_dm = chat.get("type") == "private"
        if not (is_targeted or is_dm):
            return
        logger.info(f"Обработка сообщения от {chat_title} (@{chat_username})")
        self.save_note(message, chat_username or "private", chat_title)

    @staticmethod
    def format_telegram_text(text: str, entities: list) -> str:
        if not entities or not text:
            return text
        encoded = text.encode('utf-16-le')
        for entity in sorted(entities, key=lambda e: e['offset'], reverse=True):
            e_type = entity.get('type')
            off = entity['offset'] * 2
            length = entity['length'] * 2
            try:
                before = encoded[:off].decode('utf-16-le')
                word = encoded[off:off+length].decode('utf-16-le')
                after = encoded[off+length:].decode('utf-16-le')
                if e_type == 'text_link':
                    text = f"{before}[{word}]({entity.get('url')}){after}"
                elif e_type == 'bold':
                    text = f"{before}**{word}**{after}"
                elif e_type == 'italic':
                    text = f"{before}*{word}*{after}"
                elif e_type in ['code', 'pre']:
                    text = f"{before}`{word}`{after}"
                encoded = text.encode('utf-16-le')
            except:
                continue
        return text

    def download_file(self, file_id: str) -> bytes | None:
        try:
            resp = requests.get(
                f"{self.base_url}/getFile",
                params={"file_id": file_id},
                proxies=self.proxies,
                timeout=15,
            )
            file_path = resp.json()["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            return requests.get(file_url, proxies=self.proxies, timeout=60).content
        except Exception as e:
            logger.error(f"Ошибка скачивания файла: {e}")
            return None

    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        if not HAS_PYMUPDF:
            return "[PDF получен, но pymupdf не установлен — текст не извлечён]"
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name
            doc = fitz.open(tmp_path)
            pages = []
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    pages.append(f"### Стр. {i + 1}\n{text}")
            doc.close()
            os.unlink(tmp_path)
            return "\n\n".join(pages) if pages else "[PDF не содержит извлекаемого текста]"
        except Exception as e:
            logger.error(f"Ошибка парсинга PDF: {e}")
            return f"[Ошибка извлечения текста: {e}]"

    def scrape_url(self, url: str) -> dict | None:
        """Скрейпит URL через Firecrawl. Возвращает {'title': ..., 'content': ...} или None."""
        if not self.firecrawl_key:
            return None
        try:
            logger.info(f"Firecrawl: скрейпим {url}")
            resp = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {self.firecrawl_key}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "formats": ["markdown"]},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    result = data.get("data", {})
                    return {
                        "title": result.get("metadata", {}).get("title", "") or url,
                        "content": result.get("markdown", "[Контент не извлечён]"),
                    }
            logger.error(f"Firecrawl ошибка {resp.status_code}: {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Ошибка Firecrawl: {e}")
            return None

    def save_web_article(self, url: str, scraped: dict, source_handle: str, msg_id: int, date_str: str) -> Path:
        """Сохраняет скрейпнутую статью в 01_Inbox/Web/."""
        title = scraped["title"]
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)[:60]
        filename = f"{safe_title or 'article'}.md"

        content = f"""---
date: {date_str}
source: web
url: {url}
tags: [inbox, web, clipping]
---

# {title}

> Оригинал: [{url}]({url})

{scraped["content"]}
"""
        path = self.web_dir / filename
        path.write_text(content, encoding="utf-8")
        logger.info(f"Сохранена статья: {path}")
        return path

    def save_note(self, message, source_handle, source_title):
        msg_id = message.get("message_id")
        date_ts = message.get("date", time.time())
        date_str = datetime.fromtimestamp(date_ts).strftime('%Y-%m-%d %H:%M:%S')
        raw_text = message.get("text") or message.get("caption") or ""
        entities = message.get("entities") or message.get("caption_entities") or []

        # PDF обработка
        document = message.get("document", {})
        pdf_content = ""
        pdf_filename = ""
        if document:
            mime = document.get("mime_type", "")
            file_name = document.get("file_name", "")
            if mime == "application/pdf" or file_name.lower().endswith(".pdf"):
                logger.info(f"PDF получен: {file_name}")
                pdf_bytes = self.download_file(document["file_id"])
                pdf_content = self.extract_pdf_text(pdf_bytes) if pdf_bytes else "[Не удалось скачать PDF]"
                pdf_filename = file_name

        text = self.format_telegram_text(raw_text, entities)

        is_yt = any(d in raw_text.lower() for d in ["youtube.com", "youtu.be"])

        # Определяем URL для скрейпинга (не YouTube, не пустой текст)
        web_url = None
        if not is_yt and not pdf_filename and self.firecrawl_key:
            urls = URL_PATTERN.findall(raw_text)
            # Берём первый URL если сообщение — это в основном ссылка (мало текста вокруг)
            if urls:
                non_url_text = URL_PATTERN.sub("", raw_text).strip()
                if len(non_url_text) < 80:  # мало текста кроме ссылки — скрейпим
                    web_url = urls[0]

        # Если это веб-статья — скрейпим и сохраняем отдельно
        if web_url:
            scraped = self.scrape_url(web_url)
            if scraped:
                self.save_web_article(web_url, scraped, source_handle, msg_id, date_str)
                chat_id = message.get("chat", {}).get("id")
                if chat_id:
                    requests.post(
                        f"{self.base_url}/sendMessage",
                        json={"chat_id": chat_id, "text": f"✅ Статья сохранена в Web Inbox: {scraped['title'][:60]}"},
                        proxies=self.proxies,
                    )
                return
            # Если Firecrawl не смог — падаем в обычный режим (сохраним как текст)

        if pdf_filename:
            display_title = pdf_filename.replace(".pdf", "").replace(".PDF", "")
        else:
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            display_title = lines[0] if lines else "Пост без названия"

        safe_title = re.sub(r'[^\w\s-]', '', display_title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)[:50]
        filename = f"{safe_title or source_handle}.md"

        target_dir = self.output_dir
        tags = ["inbox", "telegram"]

        if is_yt:
            target_dir = self.output_dir.parent / "nLM_Queue"
            tags.append("nlm_queue")
            logger.info(f"YouTube ссылка -> nLM_Queue: {filename}")
        elif pdf_content:
            tags.append("pdf")

        target_dir.mkdir(parents=True, exist_ok=True)
        link = f"https://t.me/{source_handle}/{msg_id}" if source_handle != "private" else ""
        tags_str = ", ".join(tags)
        pdf_section = f"\n\n## Содержимое PDF\n\n{pdf_content}" if pdf_content else ""

        content = f"""---
date: {date_str}
source: telegram
channel: "{source_title}"
url: {link}
tags: [{tags_str}]
---

# {display_title}

{text}{pdf_section}

---
[Оригинал в Telegram]({link})
"""
        try:
            (target_dir / filename).write_text(content, encoding="utf-8")
            logger.info(f"Сохранено: {target_dir / filename}")
            chat_id = message.get("chat", {}).get("id")
            if chat_id:
                if is_yt:
                    dest = "nLM_Queue (авто-анализ видео)"
                elif pdf_content:
                    dest = "Inbox (PDF извлечён)"
                else:
                    dest = "Inbox"
                requests.post(
                    f"{self.base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": f"✅ Заметка сохранена в {dest}!"},
                    proxies=self.proxies,
                )
        except Exception as e:
            logger.error(f"Не удалось сохранить файл: {e}")

    def start(self):
        logger.info("Запуск Telegram Listener (Polling)...")
        try:
            me = requests.get(f"{self.base_url}/getMe", proxies=self.proxies).json()
            logger.info(f"Подключено как: @{me.get('result', {}).get('username')}")
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            return
        while True:
            for update in self.get_updates():
                self.process_update(update)
            time.sleep(1)
