# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

DailyCheck-Agent is a GUI agent that implements a daily-check workflow based on scrcpy(tool)

## Architecture

```
.claude/SKILL.md            → Context provided when tool calling and plugin are invoked
.claude/MEMORY.md           → Memory for successful experiences
config/api.yml              → API info
config/tasks.yml            → Tasks to be done
dailycheck_agent/           → Main code
run.sh                      → Scripts for directly running code
tests/                      → Test suit
scrcpy/                     → Scrcpy for mobile control
```

### Data Flow

1. `task.yml`&`api.yml` → `main.py`
2. When need to call a tool, refer to `.claude/SKILL.md`
3. If task successfully complted, add knowledge to memory at `.claude/MEMORY.md`

### Key Code(./dailycheck_agent/)
1. `main.py`: Main entry point for the agent
2. `lib/`: Library code(Construct prompt, requests and render status)

## Session File Format

Session files are JSONL at `~/.claude/projects/[PROJECT_FOLDER]/`:
- User messages: `{"type": "user", "message": {"content": [{"type": "text", "text": "..."}]}, "isMeta": false}`
- Tool rejections: `{"type": "user", "message": {"content": [{"type": "tool_result", "is_error": true, "content": "...the user said:\n[feedback]"}]}}`
- Filter `isMeta: true` to exclude command expansions

## Platform Support

- **macOS**: Fully supported
- **Linux**: Fully supported
- **Windows**: Fully supported (native Python, no WSL required)
Requires Python 3.9+.