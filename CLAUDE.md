# Second Brain Project Guidelines

## Protocol: Skills Usage
- **MANDATORY**: Before performing any development, planning, or PKM tasks, the agent MUST check:
  1. Project Skills: `antigravity-awesome-skills/skills/*`
  2. Global Skills: `C:\Users\slin4.VOSTRO\.antigravity\skills/*`
- Select the most relevant skill (e.g., `youtube-summarizer`, `obsidian-markdown`) and strictly follow its instructions.

## PKM Standards (Obsidian)
- **Formatting**: Use Obsidian Flavored Markdown (Callouts, Highlights ==term==, Wikilinks [[note]]).
- **Analysis**: Use STAR (Situation, Task, Action, Result) and R-I-S-E framework for all summaries.
- **YAML**: Always encapsulate string values in double quotes. Tags must be in a list format.
- **Filenames**: English snake_case only.

## CURRENT STATUS & PROGRESS (As of 2026-04-05)
- **VPS Restoration**: Complete. Pipeline is autonomous.
- **YouTube Support**: Integrated `YouTubeTranscriptApi` in `process_inbox.py`. Direct transcript extraction is prioritized over Firecrawl.
- **Telegram Formatting**: Switched to HTML parse mode in `summarizer.py` for premium looks.
- **Sync**: S3 sync via `rclone` is active.
- **Last Test Case**: `final_pro_test.md` (Video: Why Best AI Coding Tools Abandoned RAG).

## Commands
- Dev Server: `python process_inbox.py`
- VPS Execution: `cd /root/agent-second-brain && /root/.local/bin/uv run python process_inbox.py`
