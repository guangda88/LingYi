#!/bin/bash
# 设置情报系统定时任务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INTELLIGENCE_SCRIPT="$PROJECT_DIR/scripts/intelligence_report.py"

echo "========================================="
echo "  灵依情报系统 - 定时任务设置"
echo "========================================="
echo ""

# 检查脚本是否存在
if [ ! -f "$INTELLIGENCE_SCRIPT" ]; then
    echo "❌ 错误: 找不到情报收集脚本"
    echo "   路径: $INTELLIGENCE_SCRIPT"
    exit 1
fi

# 确保脚本可执行
chmod +x "$INTELLIGENCE_SCRIPT"

# 获取 Python 路径
PYTHON_CMD=$(which python3)
if [ -z "$PYTHON_CMD" ]; then
    PYTHON_CMD=$(which python)
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ 错误: 找不到 Python"
    exit 1
fi

echo "📋 当前配置:"
echo "   Python: $PYTHON_CMD"
echo "   脚本: $INTELLIGENCE_SCRIPT"
echo "   数据目录: ~/.lingyi/intelligence"
echo ""

# 询问收集频率
echo "🕐 选择情报收集频率:"
echo "   1) 每小时 (适合开发测试)"
echo "   2) 每 6 小时"
echo "   3) 每天早上 9 点 (推荐)"
echo "   4) 每天早上 9 点 和 晚上 9 点"
echo "   5) 自定义"
echo ""
read -p "请选择 [1-5]: " choice

case $choice in
    1)
        cron_schedule="0 * * * *"
        schedule_desc="每小时"
        ;;
    2)
        cron_schedule="0 */6 * * *"
        schedule_desc="每6小时"
        ;;
    3)
        cron_schedule="0 9 * * *"
        schedule_desc="每天早上9点"
        ;;
    4)
        cron_schedule="0 9,21 * * *"
        schedule_desc="每天9点和21点"
        ;;
    5)
        echo ""
        read -p "请输入 cron 表达式 (分 时 日 月 周): " cron_schedule
        schedule_desc="自定义"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 构建命令
cron_cmd="$PYTHON_CMD $INTELLIGENCE_SCRIPT --save --quiet"

# 检查是否已存在
existing_cron=$(crontab -l 2>/dev/null | grep -i "intelligence_report" || true)

if [ -n "$existing_cron" ]; then
    echo ""
    echo "⚠️  发现已存在的定时任务:"
    echo "$existing_cron"
    echo ""
    read -p "是否替换? [y/N]: " replace
    if [[ ! $replace =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi
    # 删除旧任务
    crontab -l 2>/dev/null | grep -v "intelligence_report" | crontab -
fi

# 添加新任务
(crontab -l 2>/dev/null; echo "$cron_schedule $cron_cmd") | crontab -

echo ""
echo "✅ 定时任务已设置:"
echo "   频率: $schedule_desc"
echo "   Cron: $cron_schedule"
echo ""

# 显示当前 crontab
echo "📅 当前定时任务列表:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "  (无)"
echo ""

# 测试运行
read -p "是否立即测试运行? [Y/n]: " test_run
if [[ ! $test_run =~ ^[Nn]$ ]]; then
    echo ""
    echo "🧪 测试运行..."
    $PYTHON_CMD $INTELLIGENCE_SCRIPT --short
    echo ""
fi

echo "========================================="
echo "✅ 设置完成！"
echo ""
echo "查看数据文件:"
echo "   ls ~/.lingyi/intelligence/"
echo ""
echo "查看历史记录:"
echo "   cat ~/.lingyi/intelligence/history.jsonl"
echo ""
echo "编辑定时任务:"
echo "   crontab -e"
echo ""
echo "删除定时任务:"
echo "   crontab -l | grep -v intelligence_report | crontab -"
echo "========================================="
