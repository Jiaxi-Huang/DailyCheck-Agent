# DailyCheck-Agent
[![CI](https://github.com/Jiaxi-Huang/DailyCheck-Agent/actions/workflows/CI.yml/badge.svg?branch=main)](https://github.com/Jiaxi-Huang/DailyCheck-Agent/actions/workflows/CI.yml)
[![CodeQL](https://github.com/Jiaxi-Huang/DailyCheck-Agent/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Jiaxi-Huang/DailyCheck-Agent/actions/workflows/codeql-analysis.yml) 
    
A GUI-based agent to help you stay consistent with daily check-ins. Perfect for tracking habits, tasks, or goals with an intuitive interface and customizable features.

**Language**: [English](README.md) | [中文](README-CN.md)

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Command Line Options](#command-line-options)
- [License](#license)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Jiaxi-Huang/DailyCheck-Agent.git
cd DailyCheck-Agent

# 2. Install dependencies
pip install .

# 3. Download ADB (scrcpy)
curl -L -o scrcpy-macos-aarch64-v3.3.4.tar.gz https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-macos-aarch64-v3.3.4.tar.gz && \
tar -xzvf scrcpy-macos-aarch64-v3.3.4.tar.gz && \
rm -r scrcpy-macos-aarch64-v3.3.4.tar.gz && \
mv scrcpy-* scrcpy

# 4. Configure API key (edit config/api.yml)

# 5. Run
dailycheck
```

---

## Installation

### Using pip

```bash
# Standard installation
pip install .

# Development mode (with dev dependencies)
pip install -e ".[dev]"
```

### Using uv (Recommended)

```bash
# Standard installation
uv pip install .

# Development mode
uv pip install -e ".[dev]"
```

### Install ADB (scrcpy)

The project requires ADB for device control. You can download it automatically or manually:

```bash
# macOS ARM64
curl -L -o scrcpy-macos-aarch64-v3.3.4.tar.gz https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-macos-aarch64-v3.3.4.tar.gz && \
tar -xzvf scrcpy-macos-aarch64-v3.3.4.tar.gz && \
rm -r scrcpy-macos-aarch64-v3.3.4.tar.gz && \
mv scrcpy-* scrcpy
```

For other platforms, download from [scrcpy releases](https://github.com/Genymobile/scrcpy/releases).

---

## Configuration

### API Configuration

Configure LLM API in `config/api.yml`:

```yaml
api:
  open-router:
    model: "z-ai/glm-4.7-flash"
    api-key: "your-api-key-here"
  siliconflow:
    model: "Pro/zai-org/GLM-4.7"
    api-key: "your-api-key-here"
```

Supported API providers:
- [OpenRouter](https://openrouter.ai/)
- [Siliconflow](https://cloud.siliconflow.cn/)

### Task Configuration

Define tasks in `config/tasks.yml`:

```yaml
tasks:
  taobao_checkin:
    name: "Taobao Check-in"
    app: "Taobao"
    steps:
      - name: "Open app"
        description: "Find and tap the Taobao app icon on home screen"
      - name: "Start check-in"
        description: "Tap the button that starts the daily check session"
      - name: "Open sub page"
        description: "Find and tap the 领淘金币 icon to enter sub page"
      - name: "Complete check-in"
        description: "Tap the 点击签到 button that completes the daily check session"
      - name: "Finish"
        description: "Returned to app home, call task_complete"
```

Task configuration fields:
- `name`: Task display name
- `app`: Target application name
- `steps`: List of task steps, each containing:
  - `name`: Step name
  - `description`: Step description to guide AI in identifying UI elements and actions

---

## Usage

### Option 1: Using `dailycheck` command (Recommended)

```bash
# Basic usage (uses default task)
dailycheck

# Specify a task
dailycheck taobao_checkin

# With custom options
dailycheck taobao_checkin --api-provider open-router --max-steps 50

# View help
dailycheck --help
```

### Option 2: Using Python module

```bash
python -m dailycheck_agent taobao_checkin
```

### Option 3: Using Shell script (Legacy)

```bash
chmod +x run.sh
./run.sh taobao_checkin open-router
```

---

## Command Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `task_name` | | `taobao_checkin` | Task name (positional argument) |
| `--api-provider` | `-a` | `open-router` | API provider name |
| `--device-serial` | `-d` | Auto-detect | Device serial number |
| `--adb-path` | | `./scrcpy/adb` | ADB executable path |
| `--max-steps` | `-m` | `50` | Maximum execution steps |
| `--config-dir` | | | Configuration directory |
| `--version` | `-v` | | Show version number |


## Project Structure

```
dailycheck-agent/
├── dailycheck_agent/      # Main module
│   ├── __init__.py
│   ├── __main__.py        # Module entry point
│   ├── cli.py             # Command-line interface
│   ├── main.py            # Agent core logic
│   └── lib/
│       ├── api_request.py # LLM API requests
│       ├── config_loader.py # Configuration loader
│       ├── prompt.py      # Prompt builder
│       └── render.py      # Screen renderer
├── config/
│   ├── api.yml            # API configuration
│   └── tasks.yml          # Task configuration
├── scrcpy/                # ADB tools
├── pyproject.toml         # Project configuration
├── requirements.txt       # Dependencies (deprecated)
└── run.sh                 # Startup script (legacy)
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Language**: [English](README.md) | [中文](readme-cn.md)
