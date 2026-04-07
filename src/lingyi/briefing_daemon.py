"""Briefing Daemon — 定时自动生成情报汇报。

功能:
- 后台守护进程
- 每日8:00自动生成简报
- 保存到 ~/.lingyi/daily_briefings/
- 支持手动触发
- 日志记录
"""

import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DAEMON_PID_FILE = Path.home() / ".lingyi" / "briefing_daemon.pid"
_BRIEFINGS_DIR = Path.home() / ".lingyi" / "daily_briefings"


def _ensure_dirs():
    """确保目录存在。"""
    _DAEMON_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)


def _write_pid():
    """写入PID文件。"""
    _ensure_dirs()
    _DAEMON_PID_FILE.write_text(str(os.getpid()))


def _remove_pid():
    """移除PID文件。"""
    if _DAEMON_PID_FILE.exists():
        _DAEMON_PID_FILE.unlink()


def _is_running() -> bool:
    """检查daemon是否在运行。"""
    if not _DAEMON_PID_FILE.exists():
        return False

    try:
        pid = int(_DAEMON_PID_FILE.read_text())
        os.kill(pid, 0)  # 检查进程是否存在
        return True
    except (OSError, ValueError):
        return False


def _save_briefing(briefing_text: str):
    """保存简报到文件。"""
    _ensure_dirs()
    today = datetime.now().strftime("%Y-%m-%d")
    filename = _BRIEFINGS_DIR / f"briefing_{today}.txt"

    # 添加时间戳
    content = f"生成时间: {datetime.now().isoformat()}\n\n{briefing_text}\n"

    filename.write_text(content, encoding="utf-8")
    logger.info(f"简报已保存: {filename}")
    return str(filename)


def _generate_briefing():
    """生成简报。"""
    try:
        from .briefing import collect_all, format_briefing

        data = collect_all()
        briefing = format_briefing(data)
        return briefing, data
    except Exception as e:
        logger.error(f"生成简报失败: {e}")
        return None, None


def run_once():
    """立即生成一次简报。"""
    logger.info("开始生成简报...")
    briefing, data = _generate_briefing()

    if briefing:
        filename = _save_briefing(briefing)
        print(f"✅ 简报生成成功: {filename}")
        print("\n" + briefing)
        return True
    else:
        print("❌ 简报生成失败")
        return False


def _signal_handler(signum, frame):
    """信号处理函数。"""
    logger.info(f"收到信号 {signum}, 正在退出...")
    _remove_pid()
    sys.exit(0)


def start_daemon():
    """启动守护进程。"""
    if _is_running():
        print("❌ Daemon已经在运行")
        return False

    # 设置信号处理
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # 写入PID
    _write_pid()

    print("✅ Daemon已启动")
    print(f"PID: {os.getpid()}")
    print(f"PID文件: {_DAEMON_PID_FILE}")
    print("简报目录: {_BRIEFINGS_DIR}")
    print("\n使用以下命令查看日志:")
    print("  tail -f ~/.lingyi/briefing_daemon.log")

    # 启动日志
    log_file = Path.home() / ".lingyi" / "briefing_daemon.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("Briefing Daemon 启动")

    # 主循环 (简化版: 每天运行一次)
    # 实际生产环境应该用cron或systemd timer
    import time

    while True:
        now = datetime.now()

        # 每天8:00生成简报
        if now.hour == 8 and now.minute == 0:
            logger.info("开始每日简报生成...")
            briefing, data = _generate_briefing()
            if briefing:
                _save_briefing(briefing)
                logger.info("每日简报生成完成")

        # 每分钟检查一次
        time.sleep(60)


def stop_daemon():
    """停止守护进程。"""
    if not _is_running():
        print("❌ Daemon未在运行")
        return False

    try:
        pid = int(_DAEMON_PID_FILE.read_text())
        os.kill(pid, signal.SIGTERM)
        print(f"✅ Daemon已停止 (PID: {pid})")

        # 等待PID文件被删除
        import time
        for _ in range(10):
            if not _DAEMON_PID_FILE.exists():
                break
            time.sleep(0.5)

        return True
    except Exception as e:
        print(f"❌ 停止Daemon失败: {e}")
        return False


def get_status():
    """获取daemon状态。"""
    running = _is_running()

    if running:
        try:
            pid = int(_DAEMON_PID_FILE.read_text())
            print("✅ Daemon运行中")
            print(f"PID: {pid}")
        except Exception as e:
            print(f"⚠️ 状态异常: {e}")
    else:
        print("❌ Daemon未运行")

    # 显示最近的简报
    if _BRIEFINGS_DIR.exists():
        briefings = sorted(_BRIEFINGS_DIR.glob("*.txt"), reverse=True)[:5]
        if briefings:
            print(f"\n最近的简报 ({len(briefings)}):")
            for b in briefings:
                print(f"  - {b.name}")
        else:
            print("\n暂无简报")
    else:
        print("\n简报目录不存在")

    return running


def list_briefings(limit: int = 5):
    """列出最近的简报。"""
    if not _BRIEFINGS_DIR.exists():
        print("❌ 简报目录不存在")
        return []

    briefings = sorted(_BRIEFINGS_DIR.glob("*.txt"), reverse=True)[:limit]

    if not briefings:
        print("暂无简报")
        return []

    print(f"最近的简报 ({len(briefings)}):")
    for b in briefings:
        stat = b.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size = stat.st_size
        print(f"  {b.name}  ({mtime}, {size} bytes)")

    return briefings


def show_briefing(date_str: str):
    """显示指定日期的简报。"""
    filename = _BRIEFINGS_DIR / f"briefing_{date_str}.txt"

    if not filename.exists():
        # 尝试查找包含日期的文件
        matching = list(_BRIEFINGS_DIR.glob(f"*{date_str}*.txt"))
        if matching:
            filename = matching[0]
        else:
            print(f"❌ 未找到日期 {date_str} 的简报")
            return False

    content = filename.read_text(encoding="utf-8")
    print(content)
    return True
