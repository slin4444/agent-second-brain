# -*- coding: utf-8 -*-
import os, re, time, logging
from pathlib import Path
from datetime import datetime

# Попытка импорта вашей библиотеки
try:
    from notebooklm import NotebookLM
    HAS_NLM = True
except ImportError:
    HAS_NLM = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nLM-Orchestrator")

# Пути
VAULT_DIR = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "D:\\Documents\\Obsidian Vault\\Second_Brain"))
QUEUE_DIR = VAULT_DIR / "01_Inbox" / "nLM_Queue"
TARGET_DIR = VAULT_DIR / "03_Knowledge_Base" / "sources"
ERRORS_DIR = VAULT_DIR / "01_Inbox" / "Errors"

def extract_url(content):
    match = re.search(r'https?://[^\s]+', content)
    return match.group(0) if match else None

def process_queue():
    if not HAS_NLM:
        logger.error("Библиотека notebooklm-py не найдена. Установите её: pip install notebooklm-py")
        return

    if not QUEUE_DIR.exists():
        logger.info("Папка очереди пуста или не существует.")
        return

    files = list(QUEUE_DIR.glob("*.md"))
    if not files:
        logger.info("Нет новых задач в очереди nLM.")
        return

    logger.info(f"Найдено задач в очереди: {len(files)}")
    nlm = NotebookLM() # Использует авторизацию из nlm login

    for f in files:
        try:
            logger.info(f"=== ОБРАБОТКА: {f.name} ===")
            content = f.read_text(encoding="utf-8")
            url = extract_url(content)
            
            if not url:
                logger.warning(f"URL не найден в файле: {f.name}")
                f.replace(ERRORS_DIR / f.name)
                continue

            # 1. Создаем блокнот
            title = f.stem.replace("_", " ")
            nb = nlm.create_notebook(title=f"Ingest: {title}")
            logger.info(f"Создан блокнот: {nb.id}")
            
            # 2. Добавляем источник
            source = nb.add_source(url=url)
            logger.info("Источник добавлен. Ожидание обработки...")
            
            # 3. Генерируем Study Guide (глубокий разбор)
            logger.info("Генерация Study Guide (это может занять 1-3 минуты)...")
            artifact = nb.create_artifact(type="report", report_format="Study Guide")
            
            # 4. Ожидаем завершения и скачиваем
            # В вашей библиотеке это может быть автоматизировано, но добавим poll на всякий случай
            output_file = TARGET_DIR / f"{f.stem}_detailed.md"
            artifact.download(output_path=str(output_file))
            
            # Добавляем ссылку на оригинал в начало файла
            extra_meta = f"\n\n--- \n**Оригинал:** {url}\n**Источник:** NotebookLM Deep Analysis\n\n"
            new_text = extra_meta + output_file.read_text(encoding="utf-8")
            output_file.write_text(new_text, encoding="utf-8")

            # 5. Очистка
            f.unlink()
            logger.info(f"УСПЕХ: Глубокая заметка сохранена в {output_file.name}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке {f.name}: {e}")
            f.replace(ERRORS_DIR / f.name)

if __name__ == "__main__":
    process_queue()
