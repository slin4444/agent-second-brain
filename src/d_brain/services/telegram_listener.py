import os
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramListener")

class TelegramListener:
    """Слушатель Telegram Bot API для сохранения постов в Obsidian."""
    
    def __init__(self):
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channels_str = os.getenv("TELEGRAM_CHANNELS", "")
        self.vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        self.proxy_url = os.getenv("TELEGRAM_PROXY_URL", "")
        
        self._validate_config()
        
        self.channels = [c.strip().lower().lstrip("@") for c in self.channels_str.split(",") if c.strip()]
        
        # Обновленный путь для новой структуры Second Brain
        self.output_dir = Path(self.vault_path) / "01_Inbox" / "Telegram"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
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
            except: continue
        return text

    def save_note(self, message, source_handle, source_title):
        msg_id = message.get("message_id")
        date_ts = message.get("date", time.time())
        date_str = datetime.fromtimestamp(date_ts).strftime('%Y-%m-%d %H:%M:%S')
        raw_text = message.get("text") or message.get("caption") or ""
        entities = message.get("entities") or message.get("caption_entities") or []
        
        text = self.format_telegram_text(raw_text, entities)
        
        # Умный поиск заголовка: берем первую строку
        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        display_title = lines[0] if lines else "Пост без названия"
        
        import re
        safe_title = re.sub(r'[^\w\s-]', '', display_title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)[:50]
        filename = f"{safe_title or source_handle}.md"

        # Детекция YouTube для NotebookLM
        is_yt = any(domain in raw_text.lower() for domain in ["youtube.com", "youtu.be"])
        target_dir = self.output_dir
        tags = ["inbox", "telegram"]
        
        if is_yt:
            target_dir = self.output_dir.parent / "nLM_Queue"
            tags.append("nlm_queue")
            logger.info(f"Обнаружена YouTube ссылка, направляю в nLM_Queue: {filename}")

        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        link = f"https://t.me/{source_handle}/{msg_id}" if source_handle != "private" else ""
        
        tags_str = ", ".join(tags)
        content = f"""---
date: {date_str}
source: telegram
channel: "{source_title}"
url: {link}
tags: [{tags_str}]
---

# {display_title}

{text}

---
[Оригинал в Telegram]({link})
"""
        try:
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"Сохранено: {file_path}")
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
