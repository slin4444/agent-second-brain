# -*- coding: utf-8 -*-
"""
Модуль управления логами для Second Brain.
- Ежедневная ротация: logs/daily/YYYY-MM-DD.log
- Критические ошибки накапливаются: logs/errors/critical.log
- logs/latest.log — всегда указывает на лог текущего дня
- Автоматическая очистка логов старше 30 дней
"""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

# Корневая папка логов
LOGS_DIR = Path(__file__).parent.parent / "logs"
DAILY_DIR = LOGS_DIR / "daily"
ERRORS_DIR = LOGS_DIR / "errors"
LATEST_LOG = LOGS_DIR / "latest.log"
CRITICAL_LOG = ERRORS_DIR / "critical.log"

KEEP_DAYS = 30  # Сколько дней хранить ежедневные логи


def setup_logger(name: str = "second_brain") -> logging.Logger:
    """
    Настраивает и возвращает логгер с двумя хендлерами:
    1. Ежедневный файл (перезаписывается раз в сутки)
    2. Файл критических ошибок (только ERROR+, накапливается)
    3. Консоль (INFO+)
    """
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    daily_log = DAILY_DIR / f"{today}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Очищаем старые хендлеры при повторном вызове
    if logger.hasHandlers():
        logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Хендлер 1: Ежедневный файл (INFO+) ---
    daily_handler = logging.FileHandler(daily_log, encoding="utf-8", mode="a")
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(fmt)
    logger.addHandler(daily_handler)

    # Обновляем latest.log — копируем содержимое текущего дня
    try:
        import shutil
        shutil.copy2(daily_log, LATEST_LOG)
    except Exception:
        pass

    # --- Хендлер 2: Критические ошибки (ERROR+, только APPEND) ---
    critical_handler = CriticalFileHandler(CRITICAL_LOG, encoding="utf-8")
    critical_handler.setLevel(logging.ERROR)
    critical_handler.setFormatter(fmt)
    logger.addHandler(critical_handler)

    # --- Хендлер 3: Консоль (INFO+) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # Очистка старых логов
    _cleanup_old_logs()

    return logger


class CriticalFileHandler(logging.FileHandler):
    """
    Хендлер для накопления критических ошибок.
    Никогда не перезаписывает файл — только дополняет.
    Добавляет разделитель с датой при каждом запуске сессии.
    """
    _session_started = set()

    def __init__(self, filename, **kwargs):
        kwargs["mode"] = "a"  # всегда append
        super().__init__(filename, **kwargs)
        self._add_session_header(filename)

    def _add_session_header(self, filename):
        key = str(filename)
        if key not in CriticalFileHandler._session_started:
            CriticalFileHandler._session_started.add(key)
            try:
                with open(filename, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"СЕССИЯ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*60}\n")
            except Exception:
                pass


def _cleanup_old_logs():
    """Удаляет ежедневные логи старше KEEP_DAYS дней."""
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    try:
        for f in DAILY_DIR.glob("*.log"):
            try:
                date_str = f.stem  # YYYY-MM-DD
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    f.unlink()
            except ValueError:
                pass  # Файл не по формату — пропускаем
    except Exception:
        pass


def get_log_paths() -> dict:
    """Возвращает пути к актуальным логам (для диагностики)."""
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "today": str(DAILY_DIR / f"{today}.log"),
        "latest": str(LATEST_LOG),
        "critical": str(CRITICAL_LOG),
        "logs_dir": str(LOGS_DIR),
    }


if __name__ == "__main__":
    # Тест
    log = setup_logger("test")
    log.info("✅ Логгер работает корректно.")
    log.warning("⚠️ Тестовое предупреждение.")
    log.error("🔴 Тестовая ошибка (попадает в critical.log).")
    paths = get_log_paths()
    print("\nПути к логам:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
