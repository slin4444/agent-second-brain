import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь поиска модулей
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.d_brain.services.telegram_listener import TelegramListener

if __name__ == "__main__":
    try:
        listener = TelegramListener()
        listener.get_updates = listener.get_updates # Trigger offset 0
        listener.start()
    except KeyboardInterrupt:
        print("\nОстановка пользователем")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
