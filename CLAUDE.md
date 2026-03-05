# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

DailyCheck-Agent is a GUI agent that implements a daily-check workflow based on scrcpy(tool).

**Configuration**: All configuration is done through YAML files in the `config/` directory. Environment variables are **deprecated** and no longer supported.

## Architecture

```
.claude/SKILL.md            → Context provided when tool calling and plugin are invoked
.claude/MEMORY.md           → Memory for successful experiences
config/api.yml              → API credentials (api-key must be filled in this file)
config/tasks.yml            → Tasks to be done
dailycheck_agent/           → Main code
run.sh                      → Legacy script for directly running code (deprecated)
tests/                      → Test suite
scrcpy/                     → Scrcpy for mobile control
```

### Data Flow

1. `tasks.yml` & `api.yml` → `main.py`
2. When need to call a tool, refer to `.claude/SKILL.md`
3. If task successfully completed, add knowledge to memory at `.claude/MEMORY.md`

### Key Code (./dailycheck_agent/)

1. `cli.py`: Command-line interface entry point
2. `main.py`: Agent core logic
3. `lib/`: Library code (construct prompts, API requests, and screen rendering)

## Configuration

All configuration is done through YAML files:

- **API Configuration** (`config/api.yml`): Fill in `api-key` directly in the file
- **Task Configuration** (`config/tasks.yml`): Define tasks and their steps
- **User Configuration** (optional): `config.yml` or `.dailycheck.yml` in project root

Environment variables such as `DAILYCHECK_API_KEY`, `ADB_PATH`, `MAX_STEPS`, etc. are **deprecated** and no longer work.

## Running

```bash
# Recommended: Use dailycheck command
dailycheck [task_name] --api-provider open-router

# Legacy: Use run.sh (not recommended)
./run.sh [task_name] [api_provider]
```

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