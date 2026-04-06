#!/bin/bash
# 设置议事厅健康检查定时任务
# 用法: bash scripts/setup_council_health_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HEALTH_SCRIPT="$PROJECT_DIR/scripts/council_health_check.py"

echo "========================================="
echo "  灵依议事厅 - 健康检查定时任务"
echo "========================================="
echo ""

if [ ! -f "$HEALTH_SCRIPT" ]; then
    echo "错误: 找不到健康检查脚本"
    echo "   路径: $HEALTH_SCRIPT"
    exit 1
fi

chmod +x "$HEALTH_SCRIPT"

PYTHON_CMD=$(which python3)
if [ -z "$PYTHON_CMD" ]; then
    echo "错误: 找不到 python3"
    exit 1
fi

echo "配置:"
echo "  Python: $PYTHON_CMD"
echo "  脚本:   $HEALTH_SCRIPT"
echo "  频率:   每10分钟"
echo ""

cron_schedule="*/10 * * * *"
cron_cmd="$PYTHON_CMD $HEALTH_SCRIPT --notify --quiet"

existing_cron=$(crontab -l 2>/dev/null | grep "council_health_check" || true)

if [ -n "$existing_cron" ]; then
    echo "发现已有议事厅健康检查任务，替换..."
    crontab -l 2>/dev/null | grep -v "council_health_check" | crontab -
fi

(crontab -l 2>/dev/null; echo "$cron_schedule $cron_cmd") | crontab -

echo "已安装。告警日志在: ~/.lingyi/logs/council_health.jsonl"
echo ""
echo "手动测试:"
echo "  python3 scripts/council_health_check.py"
echo "  python3 scripts/council_health_check.py --notify"
echo ""
echo "查看告警历史:"
echo "  cat ~/.lingyi/logs/council_health.jsonl"
echo ""
echo "卸载:"
echo "  crontab -l | grep -v council_health_check | crontab -"
echo "========================================="
