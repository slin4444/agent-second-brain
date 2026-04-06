import os
import shutil
from pathlib import Path

# Конфигурация путей
VAULT_PATH = Path(r"D:\Documents\Obsidian Vault\Second_Brain")
INBOX_TELEGRAM = VAULT_PATH / "01_Inbox" / "Telegram"
INBOX_QUEUE = VAULT_PATH / "01_Inbox" / "nLM_Queue"
KNOWLEDGE_BASE = VAULT_PATH / "03_Knowledge_Base"

def cleanup():
    # 1. Создаем очередь, если ее нет
    INBOX_QUEUE.mkdir(parents=True, exist_ok=True)
    
    # 2. Переносим YouTube-ссылки
    if INBOX_TELEGRAM.exists():
        print(f"Checking {INBOX_TELEGRAM} for YouTube links...")
        for f in INBOX_TELEGRAM.glob("*.md"):
            try:
                content = f.read_text(encoding='utf-8').lower()
                if "youtube.com" in content or "youtu.be" in content:
                    print(f"Moving {f.name} to Queue...")
                    shutil.move(str(f), str(INBOX_QUEUE / f.name))
            except Exception as e:
                print(f"Error processing {f.name}: {e}")

    # 3. Удаляем ошибочные заметки из concepts
    concepts_dir = KNOWLEDGE_BASE / "concepts"
    errors_to_delete = [
        "http_error_408_request_timeout.md",
        "scrape_http_error_408_analysis.md"
    ]
    if concepts_dir.exists():
        for err_file in errors_to_delete:
            file_to_del = concepts_dir / err_file
            if file_to_del.exists():
                print(f"Deleting error log: {err_file}")
                file_to_del.unlink()

if __name__ == "__main__":
    cleanup()
    print("Done!")
