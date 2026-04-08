"""灵信 LingMessage — 灵字辈跨项目讨论框架。

从单向情报汇总进化为双向讨论系统：
┌─────────────┐     .lingmessage/      ┌─────────────┐
│  LingFlow   │ ←───────────────────→ │   LingYi    │
│  (灵通)     │   discussions/*.json  │   (灵依)    │
├─────────────┤                        ├─────────────┤
│  LingZhi    │ ←───────────────────→ │   LingYi    │
│  (灵知)     │                        │   (灵依)    │
├─────────────┤                        ├─────────────┤
│  LingClaude │ ←───────────────────→ │   LingYi    │
│  (灵克)     │                        │   (灵依)    │
└─────────────┘                        └─────────────┘

灵信不是中心控制器，而是一面墙——每个项目都可以在墙上留言、回复、讨论。
"""

import json
import logging
from dataclasses import asdict
from typing import Optional

from ._lingmessage_models import (
    Message, Discussion,
    SOURCE_TYPE_LABELS, PROJECTS,
    _now, _msg_id, _disc_id, _get_store, _ensure_store,
    _STORE_DIR,
)
from ._lingmessage_store import (
    _load_index, _load_discussion, _save_discussion,
    _update_index_entry, _project_name, init_store,
    _ping_notify,
    detect_temporal_anomalies, _is_auto_reply,
)
from ._lingmessage_inbox import (
    _save_to_inboxes,
    get_inbox, get_delivery_status, mark_inbox_read, clean_read_inbox,
)

logger = logging.getLogger(__name__)

__all__ = [
    "send_message", "list_discussions", "read_discussion",
    "reply_to_discussion", "close_discussion", "search_messages",
    "format_discussion_list", "format_discussion_thread", "format_message",
    "annotate_discussion", "init_store",
    "get_inbox", "get_delivery_status", "mark_inbox_read", "clean_read_inbox",
    "detect_temporal_anomalies",
    "Message", "Discussion", "PROJECTS", "SOURCE_TYPE_LABELS",
    "_STORE_DIR", "_ensure_store", "_load_index", "_load_discussion",
    "_project_name", "_now", "_get_store", "_msg_id", "_disc_id",
]


def send_message(from_id: str, topic: str, content: str,
                 reply_to: Optional[str] = None,
                 tags: Optional[list] = None,
                 source_type: str = "real") -> Message:
    """发送消息。如果话题已有讨论，追加到该讨论；否则创建新讨论。"""
    store = _ensure_store()
    from_name = _project_name(from_id)
    msg = Message(
        id=_msg_id(),
        from_id=from_id,
        from_name=from_name,
        topic=topic,
        content=content,
        timestamp=_now(),
        reply_to=reply_to,
        tags=tags or [],
        source_type=source_type,
    )

    index = _load_index(store)
    disc_id = None
    for item in index:
        if item.get("topic") == topic and item.get("status") == "open":
            disc_id = item.get("id") or item.get("thread_id", "")
            break

    if disc_id:
        disc_data = _load_discussion(store, disc_id)
        if disc_data:
            disc_data["messages"].append(asdict(msg))
            disc_data["updated_at"] = _now()
            if from_name not in disc_data.get("participants", []):
                disc_data.setdefault("participants", []).append(from_name)
            _save_discussion(store, disc_data)
            _update_index_entry(store, disc_data)
    else:
        disc = Discussion(
            id=_disc_id(),
            topic=topic,
            initiator=from_id,
            initiator_name=from_name,
            created_at=_now(),
            updated_at=_now(),
            participants=[from_name],
            status="open",
            messages=[asdict(msg)],
        )
        disc_data = asdict(disc)
        _save_discussion(store, disc_data)
        _update_index_entry(store, disc_data)
        disc_id = disc_data["id"]

    _save_to_inboxes(store, disc_id, msg, from_id)

    _ping_notify(from_id, disc_id, topic)
    return msg


def list_discussions(status: Optional[str] = None) -> list:
    """列出所有讨论。"""
    store = _get_store()
    if not store.exists():
        return []
    index = _load_index(store)
    if status:
        index = [d for d in index if d.get("status") == status]
    return sorted(index, key=lambda d: d.get("updated_at", ""), reverse=True)


def read_discussion(discussion_id: str) -> Optional[dict]:
    """读取完整讨论线程。"""
    store = _get_store()
    if not store.exists():
        return None
    return _load_discussion(store, discussion_id)


def reply_to_discussion(discussion_id: str, from_id: str, content: str,
                        reply_to: Optional[str] = None,
                        tags: Optional[list] = None,
                        source_type: str = "real") -> Optional[Message]:
    """回复讨论。"""
    store = _get_store()
    disc_data = _load_discussion(store, discussion_id)
    if not disc_data:
        return None
    if disc_data.get("status") == "closed":
        return None

    from_name = _project_name(from_id)
    msg = Message(
        id=_msg_id(),
        from_id=from_id,
        from_name=from_name,
        topic=disc_data["topic"],
        content=content,
        timestamp=_now(),
        reply_to=reply_to,
        tags=tags or [],
        source_type=source_type,
    )
    disc_data["messages"].append(asdict(msg))
    disc_data["updated_at"] = _now()
    if from_name not in disc_data.get("participants", []):
        disc_data.setdefault("participants", []).append(from_name)
    _save_discussion(store, disc_data)
    _update_index_entry(store, disc_data)
    return msg


def close_discussion(discussion_id: str) -> bool:
    """关闭讨论。"""
    store = _get_store()
    disc_data = _load_discussion(store, discussion_id)
    if not disc_data:
        return False
    disc_data["status"] = "closed"
    disc_data["updated_at"] = _now()
    _save_discussion(store, disc_data)
    _update_index_entry(store, disc_data)
    return True


def search_messages(keyword: str) -> list:
    """搜索包含关键词的消息。"""
    store = _get_store()
    if not store.exists():
        return []
    results = []
    disc_dir = store / "discussions"
    if not disc_dir.exists():
        return []
    for f in disc_dir.glob("disc_*.json"):
        try:
            disc = json.loads(f.read_text(encoding="utf-8"))
            for msg in disc.get("messages", []):
                if keyword.lower() in msg.get("content", "").lower():
                    results.append(msg)
        except Exception:
            continue
    return sorted(results, key=lambda m: m.get("timestamp", ""), reverse=True)


def format_discussion_list(discussions: list) -> str:
    """格式化讨论列表。"""
    if not discussions:
        return "📭 暂无讨论"

    lines = ["📬 灵信讨论列表", "=" * 40]
    for d in discussions:
        status_icon = "🟢" if d.get("status") == "open" else "🔴"
        count = d.get("message_count", 0)
        parts = ", ".join(d.get("participants", []))
        updated = d.get("updated_at", "")[:16].replace("T", " ")
        disc_id_str = str(d.get('id') or d.get('thread_id', ''))
        lines.append(f"\n{status_icon} [{disc_id_str[:20]}...] {d.get('topic', '?')}")
        lines.append(f"   参与者: {parts}  消息: {count}条  更新: {updated}")
    return "\n".join(lines)


def format_discussion_thread(disc: dict) -> str:
    """格式化讨论线程（完整显示）。"""
    if not disc:
        return "讨论不存在"

    status_icon = "🟢" if disc.get("status") == "open" else "🔴"
    lines = [
        f"{status_icon} 讨论: {disc['topic']}",
        f"   发起: {disc.get('initiator_name', disc.get('initiator', '?'))} "
        f"  时间: {disc['created_at'][:16].replace('T', ' ')}",
        f"   参与者: {', '.join(disc.get('participants', []))}",
        "=" * 50,
    ]

    for i, msg in enumerate(disc.get("messages", [])):
        reply_marker = ""
        if msg.get("reply_to"):
            reply_marker = f"  ↳ 回复 {msg['reply_to'][:20]}..."
        source = msg.get("source_type", "unverifiable")
        source_label = SOURCE_TYPE_LABELS.get(source, source)
        lines.append(f"\n💬 {msg.get('from_name', msg.get('from_id', '?'))} "
                     f"[{msg.get('timestamp', '')[:16].replace('T', ' ')}]{reply_marker}")
        lines.append(f"   [{source_label}]")
        lines.append(f"   {msg.get('content', '')}")
        if msg.get("tags"):
            lines.append(f"   标签: {', '.join(msg['tags'])}")

    return "\n".join(lines)


def format_message(msg: Message) -> str:
    """格式化单条消息。"""
    source_label = SOURCE_TYPE_LABELS.get(msg.source_type, msg.source_type)
    lines = [
        f"💬 {msg.from_name} [{msg.timestamp[:16].replace('T', ' ')}]",
        f"   [{source_label}]",
        f"   {msg.content}",
    ]
    if msg.tags:
        lines.append(f"   标签: {', '.join(msg.tags)}")
    return "\n".join(lines)


def annotate_discussion(disc_id: str) -> dict:
    """对已有讨论执行自动标注，返回标注结果。"""
    store = _get_store()
    if not store.exists():
        return {"error": "存储不存在"}

    disc = _load_discussion(store, disc_id)
    if not disc:
        return {"error": f"讨论 {disc_id} 不存在"}

    anomalies = detect_temporal_anomalies(disc)
    anomaly_indices = {idx for idx, _ in anomalies}

    changed = 0
    for i, msg in enumerate(disc.get("messages", [])):
        if msg.get("source_type") in ("real",):
            continue

        if i in anomaly_indices or _is_auto_reply(msg):
            new_type = "inferred"
        else:
            new_type = "unverifiable"

        if msg.get("source_type") != new_type:
            msg["source_type"] = new_type
            changed += 1

    if changed > 0:
        _save_discussion(store, disc)

    return {
        "discussion_id": disc_id,
        "total_messages": len(disc.get("messages", [])),
        "anomalies": len(anomalies),
        "updated": changed,
        "anomaly_details": [desc for _, desc in anomalies],
    }
