import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from dotenv import load_dotenv
load_dotenv()

try:
    from scripts.log_manager import setup_logger
    logger = setup_logger("nlm-watchdog")
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("nlm-watchdog")

VAULT_DIR = Path(os.environ.get("OBSIDIAN_VAULT_PATH", r"D:\Documents\Obsidian Vault\Second_Brain"))
QUEUE_DIR = VAULT_DIR / "01_Inbox" / "nLM_Queue"

class QueueHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.script_path = Path(__file__).parent / "process_nlm_queue.py"
        self.is_processing = False

    def on_any_event(self, event):
        if event.is_directory:
            return
        
        path = getattr(event, 'dest_path', event.src_path)
        if path.endswith('.md'):
            logger.info(f"Обнаружено событие ({event.event_type}) с файлом в очереди: {os.path.basename(path)}")
            time.sleep(2)
            self.run_processor()

    def run_processor(self):
        if self.is_processing:
            return
            
        self.is_processing = True
        try:
            logger.info("Запускаю процесс обработки NotebookLM...")
            python_exe = sys.executable
            subprocess.run([python_exe, str(self.script_path)], check=True)
            logger.info("Обработка завершена. Жду новые файлы...")
        except BaseException as e:
            logger.error(f"Ошибка запуска процессора: {e}")
        finally:
            self.is_processing = False

def start_watcher():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    
    event_handler = QueueHandler()
    observer = Observer()
    observer.schedule(event_handler, str(QUEUE_DIR), recursive=False)
    
    logger.info(f"Watchdog запущен!")
    logger.info(f"Отслеживаемая папка: {QUEUE_DIR}")
    
    observer.start()
    
    # Если в очереди уже есть файлы - обрабатываем их сразу
    if any(QUEUE_DIR.glob("*.md")):
        logger.info("Найдены файлы в очереди при запуске! Начинаю обработку...")
        event_handler.run_processor()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Watchdog остановлен пользователем.")
    observer.join()

if __name__ == "__main__":
    start_watcher()
