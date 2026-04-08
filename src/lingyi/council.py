"""灵家议事厅守护进程 — 客厅的灯。

让灵信讨论在用户终端关闭后仍能继续。灵依作为客厅灯守：
- 监听灵信新消息
- 按需唤醒成员参与讨论
- 追踪议题生命周期
- 用户回来后汇报离线期间的讨论
"""

import logging
import time

from .lingmessage import (
    PROJECTS, _ensure_store, _load_index, _load_discussion,
    _now,
)
from ._council_config import MEMBER_ENDPOINTS, _load_state, _save_state
from ._council_scan import council_scan, _check_discussion_health
from ._council_member import wake_member

logger = logging.getLogger(__name__)

__all__ = [
    "council_scan", "council_status", "council_health",
    "start_council_daemon", "wake_member",
]


def council_status() -> dict:
    """返回议事厅守护进程状态。"""
    state = _load_state()
    store = _ensure_store()
    index = _load_index(store)
    open_count = len([d for d in index if d.get("status") == "open"])
    total_count = len(index)

    return {
        "started_at": state.started_at,
        "last_scan": state.last_scan_time,
        "total_wakes": state.wake_count,
        "open_discussions": open_count,
        "total_discussions": total_count,
        "members_registered": len(PROJECTS),
        "real_endpoints": list(MEMBER_ENDPOINTS.keys()),
    }


def council_health() -> dict:
    """全面健康检查。返回 {alerts: [...], summary: {...}, per_discussion: [...]}。"""
    store = _ensure_store()
    index = _load_index(store)

    all_alerts = []
    per_discussion = []
    total_messages = 0
    total_auto = 0
    total_human = 0

    for entry in index:
        disc_id = entry.get("id") or entry.get("thread_id", "")
        if not disc_id:
            continue
        disc = _load_discussion(store, disc_id)
        if not disc:
            continue

        alerts = _check_discussion_health(disc_id, disc)
        all_alerts.extend(alerts)

        messages = disc.get("messages", [])
        auto_count = sum(1 for m in messages if "auto_reply" in m.get("tags", []))
        human_count = len(messages) - auto_count
        total_messages += len(messages)
        total_auto += auto_count
        total_human += human_count

        if disc.get("status") == "open":
            per_discussion.append({
                "id": disc_id,
                "topic": disc.get("topic", "?")[:40],
                "status": disc.get("status", "?"),
                "messages": len(messages),
                "auto_replies": auto_count,
                "human_messages": human_count,
                "alerts": len(alerts),
                "last_speaker": messages[-1].get("from_name", "?") if messages else "",
                "last_time": messages[-1].get("timestamp", "") if messages else "",
            })

    open_count = len([d for d in index if d.get("status") == "open"])
    auto_ratio = total_auto / total_messages if total_messages > 0 else 0

    summary = {
        "total_discussions": len(index),
        "open_discussions": open_count,
        "total_messages": total_messages,
        "total_auto_replies": total_auto,
        "total_human_messages": total_human,
        "auto_reply_ratio": f"{auto_ratio:.1%}",
        "alert_count": len(all_alerts),
        "status": "HEALTHY" if not all_alerts else "ALERT",
    }

    return {
        "alerts": all_alerts,
        "summary": summary,
        "per_discussion": per_discussion,
    }


def start_council_daemon(interval: int = 300, once: bool = False) -> None:
    """启动议事厅守护进程。

    Args:
        interval: 扫描间隔（秒），默认300秒（5分钟）
        once: 只运行一次就退出（用于测试或手动触发）
    """
    state = _load_state()
    state.started_at = _now()
    _save_state(state)

    logger.info(f"🏛️  灵家议事厅守护进程启动 (间隔 {interval}s)")

    if once:
        results = council_scan()
        logger.info(f"扫描完成: {results['open_discussions']} 个open讨论, "
                     f"唤醒了 {results['woken_members']}")
        return

    while True:
        try:
            results = council_scan()
            if results["woken_members"]:
                logger.info(f"唤醒成员: {', '.join(results['woken_members'])}")
            else:
                logger.debug(f"扫描完成: {results['open_discussions']} 个open讨论")
        except Exception as e:
            logger.error(f"议事厅扫描异常: {e}")

        time.sleep(interval)
