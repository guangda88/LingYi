"""灵信收件箱 — 收件箱读写、送达状态、通知推送。"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from ._lingmessage_models import PROJECTS, _now, _get_store

logger = logging.getLogger(__name__)


def _save_to_inboxes(store: Path, disc_id: str, msg, sender_id: str) -> list:
    """保存消息到所有收件人的收件箱（除发送者外），返回通知成功列表。"""
    inbox_entry = {
        "discussion_id": disc_id,
        "message_id": msg.id,
        "topic": msg.topic,
        "from_id": msg.from_id,
        "from_name": msg.from_name,
        "content": msg.content,
        "timestamp": msg.timestamp,
        "status": "sent",
        "read": False,
    }

    recipient_ids = [mid for mid in PROJECTS.keys() if mid != sender_id]

    notified: list[str] = []
    for recipient_id in recipient_ids:
        inbox_dir = store / "inbox" / recipient_id
        inbox_file = inbox_dir / f"{msg.id}.json"
        try:
            inbox_file.write_text(json.dumps(inbox_entry, ensure_ascii=False, indent=2), encoding="utf-8")

            try:
                success = _notify_single(recipient_id, msg.from_id, disc_id, msg.topic)
                if success:
                    inbox_entry["status"] = "delivered"
                    inbox_file.write_text(json.dumps(inbox_entry, ensure_ascii=False, indent=2), encoding="utf-8")
                    notified.append(recipient_id)
                else:
                    inbox_entry["status"] = "notified"
                    inbox_file.write_text(json.dumps(inbox_entry, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Failed to save to {recipient_id}'s inbox: {e}")

    return notified


def _notify_single(recipient_id: str, from_id: str, disc_id: str, topic: str) -> bool:
    """尝试通知单个成员，返回是否成功。"""
    import urllib.request
    import urllib.error

    _ENDPOINT_MAP = {
        "lingflow": "http://127.0.0.1:8600/api/lingmessage/notify",
        "lingzhi": "http://127.0.0.1:8000/api/v1/lingmessage/notify",
        "lingyi": "https://127.0.0.1:8900/api/lingmessage/notify",
        "lingclaude": "http://127.0.0.1:8700/api/lingmessage/notify",
        "lingresearch": "http://127.0.0.1:8003/api/lingmessage/notify",
        "lingminopt": "http://127.0.0.1:8002/api/lingmessage/notify",
    }

    if recipient_id not in _ENDPOINT_MAP:
        return False

    url = _ENDPOINT_MAP[recipient_id]
    payload = json.dumps({
        "event": "new_message",
        "from": from_id,
        "discussion_id": disc_id,
        "topic": topic,
        "timestamp": _now(),
    }, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ctx = None
        if url.startswith("https"):
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = 0
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_inbox(member_id: str) -> list:
    """获取成员的未读消息列表。"""
    store = _get_store()
    if not store.exists():
        return []

    inbox_dir = store / "inbox" / member_id
    if not inbox_dir.exists():
        return []

    messages: list[dict] = []
    for msg_file in sorted(inbox_dir.glob("*.json")):
        try:
            data = json.loads(msg_file.read_text(encoding="utf-8"))
            if not data.get("read", False):
                messages.append(data)
        except Exception:
            continue

    return sorted(messages, key=lambda m: m.get("timestamp", ""), reverse=True)


def get_delivery_status(message_id: str) -> dict:
    """获取消息的送达状态详情。"""
    store = _get_store()
    if not store.exists():
        return {"error": "Store not found"}

    inbox_dir = store / "inbox"
    if not inbox_dir.exists():
        return {"error": "Inbox directory not found"}

    status: dict = {"message_id": message_id, "recipients": {}}

    for member_inbox in inbox_dir.iterdir():
        if not member_inbox.is_dir():
            continue

        msg_file = member_inbox / f"{message_id}.json"
        if msg_file.exists():
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                member_id = member_inbox.name
                status["recipients"][member_id] = {
                    "name": data.get("from_name", member_id),
                    "status": data.get("status", "unknown"),
                    "read": data.get("read", False),
                    "timestamp": data.get("timestamp", ""),
                }
            except Exception:
                continue

    return status


def mark_inbox_read(member_id: str, message_id: str) -> bool:
    """标记消息为已读，并返回是否成功。"""
    store = _get_store()
    inbox_dir = store / "inbox" / member_id
    msg_file = inbox_dir / f"{message_id}.json"

    if not msg_file.exists():
        return False

    try:
        data = json.loads(msg_file.read_text(encoding="utf-8"))
        data["read"] = True
        data["status"] = "read"
        msg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.warning(f"Failed to mark {message_id} as read: {e}")
        return False


def clean_read_inbox(member_id: str, days: int = 7) -> int:
    """清理N天前的已读消息，返回删除的数量。"""
    store = _get_store()
    inbox_dir = store / "inbox" / member_id

    if not inbox_dir.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0

    for msg_file in inbox_dir.glob("*.json"):
        try:
            data = json.loads(msg_file.read_text(encoding="utf-8"))
            if data.get("read", False):
                ts_str = data.get("timestamp", "")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if ts < cutoff:
                            msg_file.unlink()
                            deleted += 1
                    except ValueError:
                        pass
        except Exception:
            continue

    return deleted
