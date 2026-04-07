# Long-term Memory

Curated knowledge that persists across sessions.

## User Profile

| Field | Value |
|-------|-------|
| Язык общения | Русский |
| Профессия | Разработка документов (ГОСТ, методики испытаний), проект ВСМ-1 |
| Хобби | Изучение ИИ-инструментов для личной и рабочей эффективности |
| Личные проекты | SEO, продвижение финсоветника, аудит бизнес-процессов (для друзей/родственников) |
| Главный use case | Разобраться в своих мыслях и идеях |

## Preferences

### Tech Stack
- ИИ: Claude (основной), OpenRouter API, NotebookLM
- Инфраструктура: VPS (Ubuntu), S3, Obsidian, Telegram боты
- Инструменты: Claude Code (cm команда на VPS), claude-claw бот

### Communication Style
- Preferred response language: Русский
- Detail level: Краткий, по делу

## Key Decisions

| Дата | Решение | Контекст |
|------|---------|---------|
| 2026-04-07 | Переход на Writer Wiki модель | thoughts/ → wiki/ для накопления знаний |
| 2026-04-07 | Query через claude-claw | Не разрабатывать /wiki в capture боте |
| 2026-04-07 | Оставить S3 (не переходить на GitHub) | Вложения, двусторонняя sync |

## Active Context

### Wiki Domains
- `wiki/ai/` — ИИ инструменты и воркфлоу
- `wiki/projects/seo.md` — SEO знания
- `wiki/projects/finance.md` — Финсоветник
- `wiki/projects/bizaudit.md` — Аудит бизнеса
- `wiki/people/` — Профили людей с их ЦА и тон оф войс

### Инфраструктура
- capture bot: agent-second-brain (Telegram → daily/ и wiki/)
- query bot: claude-claw (требует донастройки под second-brain vault)
- sync: rclone bisync VPS↔S3, rclone sync S3→PC (каждые 15 мин)

## Key People

| Имя | Роль | Проект |
|-----|------|--------|
| (добавляется по мере появления) | | |

## Learnings

### Что работает
- Writer модель (нарративные wiki статьи) лучше Filing Clerk для накопления знаний

### Rules to Remember
- Wiki статьи пополняются, не перезаписываются
- Тон: Wikipedia, не дневник
- Директория по теме, не по дате

## Quick Links

- [[goals/3-weekly]] — Недельный фокус
- [[goals/2-monthly]] — Месячные приоритеты
- [[wiki/projects/seo]] — SEO знания
- [[wiki/projects/finance]] — Финсоветник знания
- [[wiki/projects/bizaudit]] — Аудит знания

---

*Last updated: 2026-04-07*
