#!/usr/bin/env python3
"""情报系统定时任务 - 每日收集并生成简报

使用方法:
    python scripts/intelligence_report.py          # 生成完整简报
    python scripts/intelligence_report.py --save   # 保存到文件
    python scripts/intelligence_report.py --notify  # 发送通知
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lingyi.briefing import collect_all, format_briefing, format_briefing_short

# 配置
DATA_DIR = Path.home() / ".lingyi" / "intelligence"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(DATA_DIR / "intelligence.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def save_report(data: dict, format: str = "json") -> Path:
    """保存情报报告到文件

    Args:
        data: 情报数据
        format: 文件格式 (json/txt)

    Returns:
        保存的文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "json":
        filepath = DATA_DIR / f"intelligence_report_{timestamp}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:  # txt
        filepath = DATA_DIR / f"intelligence_report_{timestamp}.txt"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(format_briefing(data))

    logger.info(f"报告已保存: {filepath}")
    return filepath


def append_to_history(data: dict) -> None:
    """追加到历史记录

    Args:
        data: 情报数据
    """
    history_file = DATA_DIR / "history.jsonl"

    # 提取关键指标
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "lingzhi": {
            "available": data["lingzhi"]["available"],
            "total_queries": data["lingzhi"].get("total_queries", 0),
            "errors": data["lingzhi"].get("errors", 0),
        },
        "lingflow": {
            "available": data["lingflow"]["available"],
            "feedback_count": data["lingflow"].get("feedback_count", 0),
            "github_trends": data["lingflow"].get("github_trends", 0),
            "daily_reports": data["lingflow"].get("daily_reports", 0),
        },
        "lingclaude": {
            "available": data["lingclaude"]["available"],
            "sessions": data["lingclaude"].get("sessions", 0),
        },
        "lingtongask": {
            "available": data["lingtongask"]["available"],
            "total_comments": data["lingtongask"].get("total_comments", 0),
            "unique_users": data["lingtongask"].get("unique_users", 0),
        },
    }

    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    # 保留最近 90 天的记录
    cleanup_history(history_file, days=90)


def cleanup_history(history_file: Path, days: int = 90) -> None:
    """清理旧的历史记录

    Args:
        history_file: 历史记录文件
        days: 保留天数
    """
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=days)
    temp_file = history_file.with_suffix(".tmp")

    kept = 0
    with open(history_file, 'r', encoding='utf-8') as infile, \
         open(temp_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            try:
                record = json.loads(line)
                ts = datetime.fromisoformat(record["timestamp"])
                if ts > cutoff:
                    outfile.write(line)
                    kept += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    temp_file.replace(history_file)
    logger.info(f"历史记录清理完成，保留 {kept} 条记录（最近 {days} 天）")


def send_notification(message: str) -> bool:
    """发送桌面通知

    Args:
        message: 通知内容

    Returns:
        是否发送成功
    """
    try:
        import subprocess

        # 尝试使用 notify-send (Linux)
        result = subprocess.run(
            ["notify-send", "灵依情报汇报", message],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("桌面通知不可用")
        return False


def main():
    parser = argparse.ArgumentParser(description="情报系统定时任务")
    parser.add_argument("--save", action="store_true", help="保存报告到文件")
    parser.add_argument("--format", choices=["json", "txt"], default="json", help="保存格式")
    parser.add_argument("--notify", action="store_true", help="发送桌面通知")
    parser.add_argument("--short", action="store_true", help="简短输出")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")

    args = parser.parse_args()

    # 收集情报
    logger.info("开始收集情报...")
    data = collect_all()

    # 追加历史记录
    append_to_history(data)

    # 输出
    if args.short:
        output = format_briefing_short(data)
    else:
        output = format_briefing(data)

    if not args.quiet:
        print(output)

    # 保存
    if args.save:
        save_report(data, args.format)

    # 通知
    if args.notify:
        short_msg = format_briefing_short(data)
        send_notification(short_msg)

    logger.info("情报收集完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
