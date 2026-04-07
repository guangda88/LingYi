#!/bin/bash
# LingYi Briefing Daemon 安装脚本

set -e

SERVICE_NAME="lingyi-briefing-daemon"
SERVICE_FILE="/home/ai/LingYi/docs/lingyi-briefing-daemon.service"
SYSTEMD_DIR="/home/ai/.config/systemd/user"

echo "📦 安装 LingYi Briefing Daemon..."

# 检查是否以正确用户运行
if [ "$USER" != "ai" ]; then
    echo "⚠️  请以 ai 用户运行此脚本"
    exit 1
fi

# 创建systemd用户服务目录
mkdir -p "$SYSTEMD_DIR"

# 复制服务文件
echo "📋 复制服务文件..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"

# 重新加载systemd配置
echo "🔄 重新加载 systemd 配置..."
systemctl --user daemon-reload

# 启用服务（开机自启）
echo "✅ 启用服务（开机自启）..."
systemctl --user enable "$SERVICE_NAME"

# 启动服务
echo "🚀 启动服务..."
systemctl --user start "$SERVICE_NAME"

# 等待服务启动
sleep 2

# 检查服务状态
echo ""
echo "📊 服务状态:"
systemctl --user status "$SERVICE_NAME" --no-pager || true

echo ""
echo "✅ 安装完成！"
echo ""
echo "📝 常用命令:"
echo "  lingyi daemon status    # 查看daemon状态"
echo "  lingyi daemon run       # 立即生成简报"
echo "  lingyi daemon list      # 列出最近简报"
echo "  lingyi daemon show      # 显示今天简报"
echo ""
echo "🛠️  systemd 命令:"
echo "  systemctl --user start $SERVICE_NAME    # 启动服务"
echo "  systemctl --user stop $SERVICE_NAME     # 停止服务"
echo "  systemctl --user restart $SERVICE_NAME  # 重启服务"
echo "  systemctl --user status $SERVICE_NAME   # 查看状态"
echo ""
echo "📋 查看日志:"
echo "  tail -f ~/.lingyi/briefing_daemon.log"
echo "  journalctl --user -u $SERVICE_NAME -f"
