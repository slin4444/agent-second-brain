@echo off
chcp 65001 >nul
cd /d "C:\Projects\second_brain"

echo ========================================
echo [Second Brain] FORCE SYNC S S3
echo ========================================

:: Добавляем флаг --ignore-times и --checksum для гарантии обновления
rclone sync obsidian_s3:58a1c4e17db0-obsidian/Second_Brain "D:\Documents\Obsidian Vault\Second_Brain" --progress --ignore-times --checksum

echo.
echo [!] Gotovo! Prover'te papku 02_AI_Review/Daily
timeout /t 3 >nul
