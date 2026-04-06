# -*- coding: utf-8 -*-
import os, re, time, logging, asyncio, urllib.request, json
from pathlib import Path
from datetime import datetime

try:
    from scripts.log_manager import setup_logger
    logger = setup_logger("nLM-Orchestrator")
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("nLM-Orchestrator")

# Попытка импорта библиотеки
try:
    from notebooklm import NotebookLMClient
    HAS_NLM = True
except ImportError:
    HAS_NLM = False

# Пути
VAULT_DIR = Path(os.environ.get("OBSIDIAN_VAULT_PATH", r"D:\Documents\Obsidian Vault\Second_Brain"))
QUEUE_DIR = VAULT_DIR / "01_Inbox" / "nLM_Queue"
TARGET_DIR = VAULT_DIR / "03_Knowledge_Base" / "sources"
ERRORS_DIR = VAULT_DIR / "01_Inbox" / "Errors"
AUTH_PATH = Path(r"C:\Users\slin4.VOSTRO\.notebooklm\storage_state.json")

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
    return f"{frontmatter}{content}"

def extract_url(content):
    urls = re.findall(r'https?://[^\s<>"\'\)\]]+', content)
    for u in urls:
        if "t.me" not in u:
            return u
    return None

def get_youtube_title(url: str) -> str:
    """Получает реальное название YouTube видео через oEmbed API."""
    try:
        api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        with urllib.request.urlopen(api_url, timeout=10) as res:
            data = json.loads(res.read().decode())
            return data.get("title", "")
    except Exception as e:
        logger.warning(f"Не удалось получить заголовок YouTube: {e}")
        return ""

def make_safe_filename(title: str) -> str:
    """Конвертирует заголовок в безопасное имя файла."""
    safe = re.sub(r'[^\w\sа-яА-ЯёЁ-]', '', title).strip()
    safe = re.sub(r'[-\s]+', '_', safe)[:80]
    return safe or "youtube_note"

async def process_queue():
    if not HAS_NLM:
        logger.error("Библиотека notebooklm-py не найдена. Установите её: pip install notebooklm-py")
        return

    # Создаем нужные директории
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)

    files = list(QUEUE_DIR.glob("*.md"))
    if not files:
        logger.info("В очереди nLM пока пусто.")
        return

    logger.info(f"Найдено ссылок в очереди: {len(files)}")
    
    # 1. Загружаем авторизацию и создаем клиента (как в analyze_video.py)
    async with await NotebookLMClient.from_storage(str(AUTH_PATH)) as nlm:
        logger.info("✅ Соединение с NotebookLM установлено!")
        
        for f in files:
            try:
                logger.info(f"=== ОБРАБОТКА: {f.name} ===")
                content = f.read_text(encoding="utf-8")
                url = extract_url(content)
                
                if not url:
                    logger.warning(f"URL не найден, файл перемещен в Errors: {f.name}")
                    os.replace(f, ERRORS_DIR / f.name)
                    continue

                # 1. Получаем реальное название видео
                yt_title = get_youtube_title(url)
                if yt_title:
                    logger.info(f"Название видео: {yt_title}")
                    safe_name = make_safe_filename(yt_title)
                else:
                    safe_name = f.stem
                date_prefix = datetime.now().strftime('%Y-%m-%d')
                
                # 2. Создаем блокнот с реальным названием
                nb = await nlm.notebooks.create(title=yt_title or safe_name)
                logger.info(f"Создан блокнот Google: {nb.id}")
                
                # 3. Добавляем источник
                source = await nlm.sources.add_url(notebook_id=nb.id, url=url)
                logger.info("Источник добавлен. Ждем завершения анализа...")
                await nlm.sources.wait_until_ready(notebook_id=nb.id, source_id=source.id)
                
                # 4. Генерируем Study Guide (глубокий разбор)
                logger.info("Генерация Study Guide (это занимает 1-2 минуты)...")
                status = await nlm.artifacts.generate_study_guide(
                    notebook_id=nb.id, 
                    language="ru",
                    extra_instructions="В конце документа ОБЯЗАТЕЛЬНО добавь раздел 'Ключевые слова:' и перечисли 5-7 релевантных тегов (одно или два слова каждый) через запятую."
                )
                
                # Ожидаем готовности артефакта
                await nlm.artifacts.wait_for_completion(notebook_id=nb.id, task_id=status.task_id)
                
                # 5. Скачиваем результат — имя файла из заголовка видео
                output_file = TARGET_DIR / f"{date_prefix}_{safe_name}.md"
                await nlm.artifacts.download_report(notebook_id=nb.id, output_path=str(output_file))
                
                # Форматируем и добавляем свойства YAML
                raw_content = output_file.read_text(encoding="utf-8")
                final_content = format_obsidian_note(raw_content, url)
                output_file.write_text(final_content, encoding="utf-8")

                # 5. Очистка очереди
                f.unlink()
                logger.info(f"УСПЕХ: Подробный разбор сохранен в {output_file.name}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке {f.name}: {e}")
                try:
                    os.replace(f, ERRORS_DIR / f.name)
                except: pass

if __name__ == "__main__":
    asyncio.run(process_queue())
