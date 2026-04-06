#!/usr/bin/env python3
"""议事厅健康检查 — 由 cron 调用，有告警时发送桌面通知

用法:
    python scripts/council_health_check.py          # 检查并打印结果
    python scripts/council_health_check.py --notify  # 有告警时弹桌面通知
    python scripts/council_health_check.py --quiet   # 只在有告警时输出
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("council_health_check")


def send_notification(title: str, body: str) -> bool:
    try:
        subprocess.run(
            ["notify-send", title, body],
            timeout=5,
            capture_output=True,
        )
        return True
    except Exception:
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="议事厅健康检查")
    parser.add_argument("--notify", action="store_true", help="有告警时弹桌面通知")
    parser.add_argument("--quiet", action="store_true", help="只在有告警时输出")
    args = parser.parse_args()

    from lingyi.council import council_health

    health = council_health()
    summary = health["summary"]
    alerts = health["alerts"]

    if summary["status"] == "HEALTHY":
        if not args.quiet:
            print(f"✅ 议事厅健康 | {summary['open_discussions']}个讨论 | "
                  f"{summary['total_messages']}条消息 | "
                  f"自动回复率 {summary['auto_reply_ratio']}")
        return 0

    alert_text = "\n".join(alerts[:8])
    if len(alerts) > 8:
        alert_text += f"\n... 还有 {len(alerts) - 8} 条告警"

    print(f"⚠️  议事厅告警 ({len(alerts)}条)")
    print(alert_text)
    print(f"\n摘要: {summary['open_discussions']}个讨论, "
          f"{summary['total_messages']}条消息, "
          f"自动回复率 {summary['auto_reply_ratio']}")

    if args.notify:
        send_notification(
            "⚠️ 议事厅告警",
            f"{len(alerts)}条告警\n{alert_text[:200]}",
        )

    log_dir = Path.home() / ".lingyi" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "council_health.jsonl"
    with open(log_file, "a") as f:
        import datetime
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "status": summary["status"],
            "alert_count": len(alerts),
            "alerts": alerts[:10],
            "summary": summary,
        }
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return 1


if __name__ == "__main__":
    sys.exit(main())
