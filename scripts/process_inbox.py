#!/usr/bin/env python3
import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Настройка логирования для systemd ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BrainAgent")

# --- Константы путей ---
VAULT_DIR = Path("/root/obsidian-vault")
INBOX_DIR = VAULT_DIR / "inbox"
CLAUDE_MD = VAULT_DIR / "CLAUDE.md"
INDEX_MD = VAULT_DIR / "000_Vault_Index.md"

API_KEY: Optional[str] = os.environ.get("OPENROUTER_API_KEY")

def call_deepseek(system_prompt: str, user_content: str) -> Optional[str]:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode("utf-8"))
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            resp: Dict[str, Any] = json.loads(response.read().decode("utf-8"))
            return resp["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Ошибка вызова OpenRouter API: {e}")
        return None

def clean_json_output(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"): text = text.replace("```json", "", 1)
    if text.startswith("```"): text = text.replace("```", "", 1)
    if text.endswith("```"): text = text[::-1].replace("```", "", 1)[::-1]
    return text.strip()

def process_inbox() -> None:
    if not API_KEY:
        logger.critical("Неведим OPENROUTER_API_KEY в переменных среды!")
        return

    if not INBOX_DIR.exists():
        logger.info("Папка Inbox отсутствует. Отдыхаем.")
        return

    inbox_files: List[Path] = list(INBOX_DIR.rglob("*.md"))
    if not inbox_files:
        logger.info("Папка Inbox пуста.")
        return

    rules = CLAUDE_MD.read_text(encoding="utf-8") if CLAUDE_MD.exists() else "Организуй заметку и добавь теги."

    system_prompt = f"""Ты — ИИ-ассистент по управлению Obsidian Vault.
ПРАВИЛА ИЗ CLAUDE.md:
{rules}

Твоя задача — рассортировать входную заметку и вернуть СТРОГИЙ JSON без markdown блоков:
{{
  "folder": "целевая_папка_в_хранилище",
  "filename": "Умное_Название.md",
  "content": "Полное обновленное содержимое с тегами",
  "index_summary": "- [[Умное_Название]] (дата) - Краткое описание о чем эта заметка для общего индекса"
}}
"""

    completed = 0
    for file_path in inbox_files:
        logger.info(f"Обработка заметки: {file_path.name} ...")
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Не удалось прочитать {file_path.name}: {e}"); continue
            
        result_text = call_deepseek(system_prompt, content)
        if not result_text: continue
            
        try:
            clean_json = clean_json_output(result_text)
            data: dict = json.loads(clean_json)
            
            # Строим пути безопасно
            target_folder = VAULT_DIR / str(data["folder"]).strip("/\\ ")
            target_path = target_folder / data["filename"]
            
            target_folder.mkdir(parents=True, exist_ok=True)
            target_path.write_text(data["content"], encoding="utf-8")
                
            if data.get("index_summary"):
                try:
                    with INDEX_MD.open("a", encoding="utf-8") as idx_file:
                        idx_file.write(f"\n{data['index_summary']}")
                except Exception as index_e:
                    logger.warning(f"Не вышло обновить Индекс: {index_e}")
                    
            file_path.unlink() # Удаляем исходный файл
            logger.info(f"Супер! {file_path.name} -> {target_path}")
            completed += 1
            
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить JSON от ИИ: {e}")
        except Exception as e:
            logger.error(f"Критическая ошибка файла: {file_path.name}: {e}")
            
    logger.info(f"Обработка завершена. Всего отсортировано: {completed}")

if __name__ == "__main__":
    process_inbox()
