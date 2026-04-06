@echo off
chcp 65001 > nul
setlocal

:: Путь к вашему проекту
set PROJECT_DIR=c:\Projects\second_brain
cd /d %PROJECT_DIR%

echo [Wiki-Brain] Синхронизация очереди из облака...
git pull origin main

echo [Wiki-Brain] Запуск глубокого анализа NotebookLM...
python scripts/process_nlm_queue.py

echo [Wiki-Brain] Финальный инжест знаний в Obsidian...
python process_inbox.py

echo [Wiki-Brain] Готово! Все новые знания добавлены.
timeout /t 10
exit
