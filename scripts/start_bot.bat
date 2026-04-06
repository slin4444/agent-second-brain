@echo off
setlocal
cd /d %~dp0\..

echo ========================================
echo Zapusk Telegram Listener (second_brain)
echo ========================================

REM Проверка зависимостей и запуск через uv
uv run python scripts/run_listener.py

if errorlevel 1 (
    echo.
    echo [!] OSHIBKA: Bot umer. Prover' .env i soedinenie.
    pause
)
endlocal
