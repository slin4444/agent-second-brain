import asyncio
import os
from datetime import datetime
from pathlib import Path
from notebooklm import NotebookLMClient

# Конфигурация
VAULT_PATH = Path(r"D:\Documents\Obsidian Vault\Second_Brain")
OUTPUT_DIR = VAULT_PATH / "03_Knowledge_Base" / "sources"
YOUTUBE_URL = "https://youtu.be/3HwsI-9hss0?si=SbJByJDzAqylgiNP"
AUTH_PATH = Path(r"C:\Users\slin4.VOSTRO\.notebooklm\storage_state.json")

import re
def format_obsidian_note(content: str, url: str) -> str:
    tags = ["study_guide"]
    match = re.search(r'(?i)(?:теги|tags|ключевые слова|keywords):\s*([^\n]+)', content)
    if match:
        for t in match.group(1).split(','):
            cleaned = re.sub(r'[^\w\sа-яА-ЯёЁ]', '', t).strip()
            if cleaned:
                words = cleaned.split()
                if len(words) > 1:
                    tags.append("".join(w.capitalize() for w in words))
                else:
                    tags.append(words[0].lower())
    
    content = re.sub(r'(?i)\n*(?:теги|tags|ключевые слова|keywords):\s*([^\n]+)\n*', '\n\n', content)
    content = re.sub(r'^# Анализ видео:.*\n+', '', content).strip()
    
    unique_tags = []
    for t in tags:
        if t not in unique_tags: unique_tags.append(t)
            
    tags_yaml = "\n".join(f"  - {t}" for t in unique_tags)
    frontmatter = f"---\nsource: {url}\ntype: deep_analysis\ndate: {datetime.now().strftime('%Y-%m-%d')}\ntags:\n{tags_yaml}\n---\n\n"
    return f"{frontmatter}# Анализ: {url}\n\n{content}"

async def analyze():
    print(f"🚀 Начинаю анализ видео: {YOUTUBE_URL}")
    
    # 1. Инициализация клиента через контекстный менеджер (рекомендуемый способ)
    try:
        async with await NotebookLMClient.from_storage(str(AUTH_PATH)) as nlm:
            print("✅ Соединение с NotebookLM установлено!")

            # 2. Создание блокнота
            print("📓 Создаю блокнот для анализа...")
            nb = await nlm.notebooks.create(title=f"Wiki-Brain: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            nb_id = nb.id
            print(f"✅ Блокнот создан: {nb_id}")

            # 3. Добавление источника
            print("🔗 Добавляю YouTube-видео...")
            source = await nlm.sources.add_url(notebook_id=nb_id, url=YOUTUBE_URL)
            source_id = source.id
            print(f"⏳ Ожидаю обработки (транскрибации) источника {source_id}...")
            await nlm.sources.wait_until_ready(notebook_id=nb_id, source_id=source_id)

            # 4. Генерация конспекта
            print("📝 Генерирую Study Guide (это может занять до 2 минут)...")
            status = await nlm.artifacts.generate_study_guide(
                notebook_id=nb_id, 
                language="ru",
                extra_instructions="В конце документа ОБЯЗАТЕЛЬНО добавь раздел 'Ключевые слова:' и перечисли 5-7 релевантных тегов (одно или два слова каждый) через запятую."
            )
            await nlm.artifacts.wait_for_completion(notebook_id=nb_id, task_id=status.task_id)
            
            # 5. Сохранение результата
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            file_name = f"Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            file_path = OUTPUT_DIR / file_name
            
            # Загружаем последнй сгенерированный отчет (Study Guide)
            await nlm.artifacts.download_report(notebook_id=nb_id, output_path=str(file_path))
            
            # Дописываем заголовок исходного видео и теги
            with open(file_path, "r+", encoding="utf-8") as f:
                content = f.read()
                f.seek(0, 0)
                formatted_content = format_obsidian_note(content, YOUTUBE_URL)
                f.write(formatted_content)

                
            print(f"🎉 ГОТОВО! Отчет сохранен: {file_path}")
            
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze())
