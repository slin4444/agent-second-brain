import sys
import os
import logging
from pathlib import Path

# Добавляем корень проекта в путь поиска модулей
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Настраиваем логирование: файл + консоль
try:
    from scripts.log_manager import setup_logger
    logger = setup_logger("telegram-listener")
    logger.info(f"Логи пишутся в: {project_root / 'logs'}")
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("telegram-listener")

from src.d_brain.services.telegram_listener import TelegramListener

if __name__ == "__main__":
    try:
        logger.info("=== Запуск Telegram-listener ===")
        listener = TelegramListener()
        listener.start()
    except KeyboardInterrupt:
        logger.info("Остановка пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
