# DailyCheck-Agent Memory

## Project Overview

DailyCheck-Agent is an Android automation agent for daily check-in tasks. It uses LLM to analyze screen information and control Android devices via ADB commands.

## Key Decisions & Learnings

### 1. Configuration File Path Resolution (2026-03-05)

**Problem:** When the package is installed via pip, `ConfigLoader` couldn't find the config files because it used `Path(__file__).parent.parent.parent` which pointed to site-packages instead of the project directory.

**Solution:** Modified `config_loader.py` to use a priority-based strategy:
1. First try current working directory's `config` folder
2. Then try the package directory's parent `config` folder (dev mode)
3. Finally fallback to `~/.dailycheck/config`

**File:** `dailycheck_agent/lib/config_loader.py`

### 2. Ad Handling via Prompt Engineering (2026-03-05)

**Problem:** Hard-coded ad detection and handling logic was too rigid and interfered with the main task flow.

**Solution:** 
- Removed hard-coded ad handling logic from `main.py` and `prompt.py`
- Ad handling is now implemented via prompt engineering in SKILLS.md
- The LLM decides when and how to handle ads based on screen information
- This provides flexibility for different ad formats and layouts

**Files Modified:**
- `dailycheck_agent/main.py` - Removed `_handle_ad` method and ad-related logic
- `dailycheck_agent/lib/prompt.py` - Removed `AD_KEYWORDS`, `detect_ad_elements`, `is_ad_screen` methods
- `.claude/SKILLS.md` - Added "Ad Handling Guide" section (Section 8)

### 3. Task Completion Flow (2026-03-05)

**Problem:** After completing the core task operation (e.g., clicking "签到" button), the app might navigate to a different page (reward page, activity detail, etc.). The agent needed to handle this gracefully.

**Solution:**
- Added "Task Completion Criteria" to the system prompt
- When `task_complete` is called, the agent automatically presses HOME key to return to the home screen
- This ensures the device is left in a clean state after task execution

**Implementation:**
- System prompt now includes: "任务完成后，先按 HOME 键回到手机主页，然后调用 task_complete 工具"
- `main.py` automatically presses HOME key (code 3) when `task_complete` tool is called

**Files Modified:**
- `dailycheck_agent/lib/prompt.py` - Added "任务完成判定" section to system prompt
- `dailycheck_agent/main.py` - Added HOME key press before breaking the loop

### 4. Unified Configuration System (2026-03-05)

**Problem:** Configuration was scattered across multiple environment variables (`DAILYCHECK_TASK`, `DAILYCHECK_API_PROVIDER`, etc.), making it cumbersome to manage and share configurations.

**Solution:**
- Added support for YAML configuration files (`config.yml`, `.dailycheck.yml`)
- Implemented unified priority: **CLI Args > Environment Variables > Config File > Defaults**
- Added `--config` / `-c` flag to specify custom config file path
- Default config file search paths: `./config.yml`, `./.dailycheck.yml`, `~/.dailycheck/config.yml`
- **Run all tasks by default** when no task name is specified
- Added `--list-tasks` flag to list all available tasks

**Config File Format:**
```yaml
# Optional: specify tasks to run (run all if not specified)
# tasks:
#   - aliyunpan_checkin

api_provider: open-router
device_serial: "emulator-5554"
adb_path: "scrcpy/adb"
max_steps: 50
config_dir: "config"
```

**Usage:**
```bash
# Run all tasks
dailycheck

# Run specific task
dailycheck aliyunpan_checkin

# List tasks
dailycheck --list-tasks
```

**Files Modified:**
- `dailycheck_agent/cli.py` - Complete rewrite with task list support, `load_yaml()`, `load_tasks_config()` functions
- `.claude/SKILLS.md` - Updated Configuration section (Section 6) with new usage patterns

## Best Practices

### For Task Configuration
- Define clear, step-by-step instructions in `tasks.yml`
- Each step should have a name and description
- The LLM uses this information to understand the task flow

### For LLM Interaction
- Always include screen context in user messages
- Provide tool execution results with new screen information
- Handle cases where LLM doesn't call any tool

### For Device Control
- Wait 1.5-2.0 seconds after tap operations for UI to update
- Wait 3.0-5.0 seconds after app launch
- Always validate coordinates are within screen bounds

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Config file not found | Use priority-based path resolution |
| Ad interference | Handle via LLM prompt, not hard-coded logic |
| Task stuck on reward page | Auto-press HOME when task_complete is called |
| API 500 errors | Check API key configuration in `config/api.yml` |

## Configuration Example

```yaml
# config/api.yml
api:
  open-router:
    base-url: https://openrouter.ai/api/v1
    model: z-ai/glm-4.7-flash
    api-key: "{{ api_key }}"  # Set DAILYCHECK_API_KEY env var

# config/tasks.yml
tasks:
  taobao_checkin:
    app: 淘宝
    steps:
      - name: Open app
        description: Find and tap the 淘宝 app icon on home screen
      - name: Start check-in
        description: Tap the button that starts the check-in flow
```
