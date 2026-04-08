"""灵信存储层 — 磁盘I/O、索引管理、收件箱、通知。"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ._lingmessage_models import (
    PROJECTS, _now,
)

logger = logging.getLogger(__name__)


def _load_index(store: Path) -> list:
    idx_path = store / "index.json"
    if not idx_path.exists():
        return []
    try:
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("threads", data.get("discussions", []))
        return []
    except Exception:
        return []


def _save_index(store: Path, index: list) -> None:
    idx_path = store / "index.json"
    data = {"threads": index, "last_updated": _now()}
    idx_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_discussion(store: Path, disc_id: str) -> Optional[dict]:
    path = store / "discussions" / f"{disc_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_discussion(store: Path, disc: dict) -> None:
    path = store / "discussions" / f"{disc['id']}.json"
    path.write_text(json.dumps(disc, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_index_entry(store: Path, disc: dict) -> None:
    index = _load_index(store)
    disc_id = disc.get("id") or disc.get("thread_id", "")
    entry = {
        "id": disc_id,
        "topic": disc.get("topic", ""),
        "initiator": disc.get("initiator", ""),
        "participants": disc.get("participants", []),
        "message_count": len(disc.get("messages", [])),
        "status": disc.get("status", "open"),
        "created_at": disc.get("created_at", ""),
        "updated_at": disc.get("updated_at", ""),
        "summary": disc.get("summary", ""),
    }
    found = False
    for i, item in enumerate(index):
        item_id = item.get("id") or item.get("thread_id", "")
        if item_id == disc_id:
            if "thread_id" in item:
                entry["thread_id"] = item["thread_id"]
            if item.get("channel"):
                entry["channel"] = item["channel"]
            index[i] = entry
            found = True
            break
    if not found:
        index.append(entry)
    _save_index(store, index)


def _project_name(project_id: str) -> str:
    return PROJECTS.get(project_id, {}).get("name", project_id)


def init_store() -> dict:
    """初始化灵信存储。"""
    from ._lingmessage_models import _ensure_store as _do_ensure
    store = _do_ensure()
    config_path = store / "config.json"
    if not config_path.exists():
        config = {
            "version": "0.1.0",
            "created_at": _now(),
            "projects": PROJECTS,
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    if not (store / "index.json").exists():
        _save_index(store, [])
    return {"initialized": True, "store": str(store)}


def _ping_notify(from_id: str, disc_id: str, topic: str) -> None:
    """通知在线服务有新灵信消息。"""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "event": "new_message",
        "from": from_id,
        "discussion_id": disc_id,
        "topic": topic,
        "timestamp": _now(),
    }, ensure_ascii=False).encode("utf-8")

    _FROM_TO_TARGET = {
        "lingzhi": "灵知",
        "lingclaude": "灵克",
        "lingyi": "灵依",
    }
    skip_target = _FROM_TO_TARGET.get(from_id)

    targets = [
        ("灵知", "http://127.0.0.1:8000/api/v1/lingmessage/notify"),
        ("灵依", "https://127.0.0.1:8900/api/lingmessage/notify"),
        ("灵克", "http://127.0.0.1:8700/api/lingmessage/notify"),
        ("灵知(auto)", "http://127.0.0.1:8011/api/lingmessage/notify"),
        ("灵极优", "http://127.0.0.1:8002/api/lingmessage/notify"),
        ("灵妍", "http://127.0.0.1:8003/api/lingmessage/notify"),
    ]
    for name, url in targets:
        if name == skip_target:
            continue
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
            urllib.request.urlopen(req, context=ctx, timeout=3)
            logger.debug(f"通知 {name} 成功")
        except urllib.error.HTTPError as e:
            logger.debug(f"通知 {name} 返回 {e.code}")
        except Exception as e:
            logger.debug(f"通知 {name} 失败: {e}")


def _is_auto_reply(msg: dict) -> bool:
    return "auto_reply" in msg.get("tags", [])


def detect_temporal_anomalies(disc: dict, threshold_seconds: float = 2.0) -> list:
    """检测时间间隔异常——同秒或极短时间内多个'不同成员'发言。"""
    messages = disc.get("messages", [])
    if len(messages) < 2:
        return []

    anomalies = []
    prev_time = None
    prev_from = None
    streak = 0

    for i, msg in enumerate(messages):
        ts_str = msg.get("timestamp", "")
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue

        cur_from = msg.get("from_id", "")

        if prev_time is not None:
            delta = (ts - prev_time).total_seconds()
            if delta <= threshold_seconds and cur_from != prev_from:
                streak += 1
                if streak >= 2:
                    anomalies.append((
                        i,
                        f"连续{streak + 1}个不同成员在{delta:.0f}秒内发言: "
                        f"{msg.get('from_name', cur_from)} @ {ts_str}"
                    ))
            else:
                streak = 0

        prev_time = ts
        prev_from = cur_from

    return anomalies



