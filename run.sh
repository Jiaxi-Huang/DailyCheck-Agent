#!/bin/bash

# DailyCheck-Agent 启动脚本
# 用法：./run.sh [任务名称] [API 提供商] [设备序列号]

set -e

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
DEFAULT_TASK="taobao_checkin"
DEFAULT_API_PROVIDER="open-router"
DEFAULT_ADB_PATH="$SCRIPT_DIR/scrcpy/adb"

# 从环境变量或参数获取配置
TASK_NAME="${1:-$DEFAULT_TASK}"
API_PROVIDER="${2:-$DEFAULT_API_PROVIDER}"
DEVICE_SERIAL="${3:-}"
ADB_PATH="${ADB_PATH:-$DEFAULT_ADB_PATH}"
MAX_STEPS="${MAX_STEPS:-50}"

# 颜色输出 (opencode 风格)
BOLD='\033[1m'
DIM='\033[2m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${WHITE}${BOLD} ██████╗  █████╗ ██╗██╗  ██╗   ██╗ ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗${NC}"
echo -e "${WHITE}${BOLD} ██╔══██╗██╔══██╗██║██║  ╚██╗ ██╔╝██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝${NC}"
echo -e "${WHITE}${BOLD} ██║  ██║███████║██║██║   ╚████╔╝ ██║     ███████║█████╗  ██║     █████╔╝     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ${NC}"
echo -e "${WHITE}${BOLD} ██║  ██║██╔══██║██║██║    ╚██╔╝  ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ${NC}"
echo -e "${WHITE}${BOLD} ██████╔╝██║  ██║██║███████╗██║   ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ${NC}"
echo -e "${WHITE}${BOLD} ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ${NC}"
# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ 错误${NC}: 未找到 python3，请确保已安装 Python 3.9+"
    exit 1
fi

# 检查 ADB 路径
if [ ! -f "$ADB_PATH" ]; then
    echo -e "${YELLOW}⚠ 警告${NC}: ADB 文件不存在：$ADB_PATH"
    echo -e "${DIM}  将尝试使用系统 PATH 中的 adb${NC}"
    ADB_PATH="adb"
fi

# 检查 API 密钥
if [ -z "$DAILYCHECK_API_KEY" ]; then
    echo -e "${YELLOW}⚠ 警告${NC}: 未设置 DAILYCHECK_API_KEY 环境变量"
    echo -e "${DIM}  请确保在 config/api.yml 中配置了有效的 API 密钥${NC}"
fi

# 打印配置
echo -e "${BOLD}配置信息:${NC}"
echo -e "  ${BLUE}●${NC} 任务名称：${BOLD}$TASK_NAME${NC}"
echo -e "  ${BLUE}●${NC} API 提供商：${API_PROVIDER}"
echo -e "  ${BLUE}●${NC} 设备序列号：${DIM}${DEVICE_SERIAL:-自动检测}${NC}"
echo -e "  ${BLUE}●${NC} ADB 路径：${DIM}$ADB_PATH${NC}"
echo -e "  ${BLUE}●${NC} 最大步骤数：${MAX_STEPS}"
echo ""

# 运行代理
python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')

from dailycheck_agent.main import DailyCheckAgent

try:
    agent = DailyCheckAgent(
        task_name='$TASK_NAME',
        adb_path='$ADB_PATH',
        device_serial='$DEVICE_SERIAL' if '$DEVICE_SERIAL' else None,
        api_provider='$API_PROVIDER',
        max_steps=$MAX_STEPS,
    )
    success = agent.run()
    sys.exit(0 if success else 1)
except Exception as e:
    print(f'运行失败：{e}')
    sys.exit(1)
"

# 捕获退出码
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ 任务执行成功${NC}"
else
    echo -e "${RED}✗ 任务执行失败或未完成${NC}"
fi

exit $EXIT_CODE
