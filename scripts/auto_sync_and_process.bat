@echo off
chcp 65001 >nul
setlocal

set PROJECT_DIR=C:\Projects\second_brain
set VENV_PYTHON=%PROJECT_DIR%\nlm_skill\.venv\Scripts\python.exe
set QUEUE_DIR=D:\Documents\Obsidian Vault\Second_Brain\01_Inbox\nLM_Queue
set TODAY=%date:~6,4%-%date:~3,2%-%date:~0,2%
set LOG_FILE=%PROJECT_DIR%\logs\daily\%TODAY%.log

:: Создаем папку для логов
if not exist "%PROJECT_DIR%\logs\daily" mkdir "%PROJECT_DIR%\logs\daily"
if not exist "%PROJECT_DIR%\logs\errors" mkdir "%PROJECT_DIR%\logs\errors"

echo [%date% %time%] === АВТО-СИНХРОНИЗАЦИЯ СТАРТ === >> "%LOG_FILE%"

:: 1. Скачиваем новые файлы из S3 (только папку nLM_Queue)
echo [%date% %time%] Синхронизация nLM_Queue из S3... >> "%LOG_FILE%"
rclone sync "obsidian_s3:58a1c4e17db0-obsidian/Second_Brain/01_Inbox/nLM_Queue" "%QUEUE_DIR%" --progress >> "%LOG_FILE%" 2>&1

:: 2. Если в очереди есть .md файлы — запускаем обработку NotebookLM
set HAS_FILES=0
for %%f in ("%QUEUE_DIR%\*.md") do set HAS_FILES=1

if %HAS_FILES%==1 (
    echo [%date% %time%] Найдены файлы в очереди. Запускаю NotebookLM... >> "%LOG_FILE%"
    "%VENV_PYTHON%" "%PROJECT_DIR%\scripts\process_nlm_queue.py" >> "%LOG_FILE%" 2>&1
    
    :: 3. Синхронизируем результаты обратно в S3
    echo [%date% %time%] Отправляем результаты в S3... >> "%LOG_FILE%"
    rclone sync "D:\Documents\Obsidian Vault\Second_Brain\03_Knowledge_Base\sources" "obsidian_s3:58a1c4e17db0-obsidian/Second_Brain/03_Knowledge_Base/sources" >> "%LOG_FILE%" 2>&1
) else (
    echo [%date% %time%] Очередь пуста. >> "%LOG_FILE%"
)

echo [%date% %time%] === ГОТОВО === >> "%LOG_FILE%"
exit /b 0
