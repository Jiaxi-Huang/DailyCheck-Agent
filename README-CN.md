# DailyCheck-Agent

一个基于 GUI 的代理助手，帮助您坚持每日打卡任务。适用于追踪习惯、任务或目标，提供直观的界面和可定制的功能。

## 目录

- [快速开始](#快速开始)
- [安装](#安装)
- [配置](#配置)
- [运行](#运行)
- [命令行选项](#命令行选项)
- [环境变量](#环境变量)
- [许可证](#许可证)

---

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Jiaxi-Huang/DailyCheck-Agent.git
cd DailyCheck-Agent

# 2. 安装依赖
uv pip install .

# 3. 下载 ADB (scrcpy)
curl -L -o scrcpy-macos-aarch64-v3.3.4.tar.gz https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-macos-aarch64-v3.3.4.tar.gz && \
tar -xzvf scrcpy-macos-aarch64-v3.3.4.tar.gz && \
rm -r scrcpy-macos-aarch64-v3.3.4.tar.gz && \
mv scrcpy-* scrcpy

# 4. 配置 API 密钥（编辑 config/api.yml）

# 5. 运行
dailycheck
```

---

## 安装

### 使用 pip

```bash
# 标准安装
pip install .

# 开发模式安装（包含开发依赖）
pip install -e ".[dev]"
```

### 使用 uv（推荐）

```bash
# 标准安装
uv pip install .

# 开发模式安装
uv pip install -e ".[dev]"
```

### 安装 ADB (scrcpy)

项目依赖 ADB 进行设备控制。您可以手动下载或自动安装：

```bash
# macOS ARM64
curl -L -o scrcpy-macos-aarch64-v3.3.4.tar.gz https://github.com/Genymobile/scrcpy/releases/download/v3.3.4/scrcpy-macos-aarch64-v3.3.4.tar.gz && \
tar -xzvf scrcpy-macos-aarch64-v3.3.4.tar.gz && \
rm -r scrcpy-macos-aarch64-v3.3.4.tar.gz && \
mv scrcpy-* scrcpy
```

其他平台请从 [scrcpy 发布页](https://github.com/Genymobile/scrcpy/releases) 下载对应版本。

---

## 配置

### API 配置

在 `config/api.yml` 中配置 LLM API：

```yaml
api:
  open-router:
    model: "z-ai/glm-4.7-flash"
    api-key: "your-api-key-here"
  siliconflow:
    model: "Pro/zai-org/GLM-4.7"
    api-key: "your-api-key-here"
```

目前支持的 API 提供商：
- [OpenRouter](https://openrouter.ai/)
- [Siliconflow](https://cloud.siliconflow.cn/)

### 任务配置

在 `config/tasks.yml` 中定义任务：

```yaml
tasks:
  taobao_checkin:
    name: "淘宝打卡"
    app: "淘宝"
    steps:
      - name: "打开应用"
        description: "在主屏幕找到并点击淘宝应用图标"
      - name: "开始签到"
        description: "点击启动每日签到会话的按钮"
      - name: "打开子页面"
        description: "找到并点击领淘金币图标进入子页面"
      - name: "完成签到"
        description: "点击签到按钮完成每日签到"
      - name: "完成"
        description: "返回应用主页，调用 task_complete 完成任务"
```

任务配置说明：
- `name`: 任务显示名称
- `app`: 目标应用名称
- `steps`: 任务步骤列表，每个步骤包含：
  - `name`: 步骤名称
  - `description`: 步骤描述，指导 AI 识别 UI 元素和操作

---

## 运行

### 方式一：使用 `dailycheck` 命令（推荐）

```bash
# 基础用法（使用默认任务）
dailycheck

# 指定任务
dailycheck taobao_checkin

# 自定义选项
dailycheck taobao_checkin --api-provider open-router --max-steps 50

# 查看帮助
dailycheck --help
```

### 方式二：使用 Python 模块

```bash
python -m dailycheck_agent taobao_checkin
```

### 方式三：使用 Shell 脚本（旧版）

```bash
chmod +x run.sh
./run.sh taobao_checkin open-router
```

---

## 命令行选项

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `task_name` | | `taobao_checkin` | 任务名称（位置参数） |
| `--api-provider` | `-a` | `open-router` | API 提供商名称 |
| `--device-serial` | `-d` | 自动检测 | 设备序列号 |
| `--adb-path` | | `./scrcpy/adb` | ADB 可执行文件路径 |
| `--max-steps` | `-m` | `50` | 最大执行步骤数 |
| `--config-dir` | | | 配置文件目录 |
| `--version` | `-v` | | 显示版本号 |

---

## 环境变量

可以通过环境变量配置代理：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DAILYCHECK_TASK` | 任务名称 | `taobao_checkin` |
| `DAILYCHECK_API_PROVIDER` | API 提供商 | `open-router` |
| `DAILYCHECK_DEVICE_SERIAL` | 设备序列号 | 自动检测 |
| `ADB_PATH` | ADB 路径 | `./scrcpy/adb` |
| `MAX_STEPS` | 最大步骤数 | `50` |
| `DAILYCHECK_CONFIG_DIR` | 配置文件目录 | 默认配置目录 |

示例：

```bash
export DAILYCHECK_TASK=taobao_checkin
export DAILYCHECK_API_PROVIDER=siliconflow
export MAX_STEPS=100

dailycheck
```

---

## 项目结构

```
dailycheck-agent/
├── dailycheck_agent/      # 主模块
│   ├── __init__.py
│   ├── __main__.py        # 模块入口
│   ├── cli.py             # 命令行接口
│   ├── main.py            # 代理核心逻辑
│   └── lib/
│       ├── api_request.py # LLM API 请求
│       ├── config_loader.py # 配置加载器
│       ├── prompt.py      # 提示词构建
│       └── render.py      # 屏幕渲染
├── config/
│   ├── api.yml            # API 配置
│   └── tasks.yml          # 任务配置
├── scrcpy/                # ADB 工具
├── pyproject.toml         # 项目配置
├── requirements.txt       # 依赖（已弃用）
└── run.sh                 # 启动脚本（旧版）
```

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

**语言选择**: [English](README.md) | [中文](readme-cn.md)
