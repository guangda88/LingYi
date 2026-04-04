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
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_STORE_DIR = Path(os.environ.get("LINGMESSAGE_DIR", "/home/ai/.lingmessage"))

PROJECTS = {
    "lingflow": {"name": "灵通", "role": "工作流引擎"},
    "lingclaude": {"name": "灵克", "role": "编程助手"},
    "lingzhi": {"name": "灵知", "role": "知识库"},
    "lingyi": {"name": "灵依", "role": "情报中枢"},
    "lingtongask": {"name": "灵通问道", "role": "内容平台"},
    "lingterm": {"name": "灵犀", "role": "终端感知"},
    "lingminopt": {"name": "灵极优", "role": "自优化框架"},
    "lingresearch": {"name": "灵研", "role": "科研优化"},
    "zhibridge": {"name": "智桥", "role": "HTTP中继"},
}


@dataclass
class Message:
    id: str
    from_id: str
    from_name: str
    topic: str
    content: str
    timestamp: str
    reply_to: Optional[str] = None
    tags: list = field(default_factory=list)


@dataclass
class Discussion:
    id: str
    topic: str
    initiator: str
    initiator_name: str
    created_at: str
    updated_at: str
    participants: list = field(default_factory=list)
    status: str = "open"
    summary: str = ""
    messages: list = field(default_factory=list)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def _msg_id() -> str:
    ms = _now().replace("-", "").replace("T", "").replace(":", "")
    return f"msg_{ms}"


def _disc_id() -> str:
    ms = _now().replace("-", "").replace("T", "").replace(":", "")
    return f"disc_{ms}"


def _get_store() -> Path:
    return _STORE_DIR


def _ensure_store() -> Path:
    store = _get_store()
    store.mkdir(parents=True, exist_ok=True)
    (store / "discussions").mkdir(exist_ok=True)
    return store


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
    store = _ensure_store()
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

    targets = [
        ("灵知", "http://127.0.0.1:8000/api/v1/lingmessage/notify"),
        ("灵依", "https://127.0.0.1:8900/api/lingmessage/notify"),
        ("灵克", "http://127.0.0.1:8700/api/lingmessage/notify"),
    ]
    for name, url in targets:
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


def send_message(from_id: str, topic: str, content: str,
                 reply_to: Optional[str] = None,
                 tags: Optional[list] = None) -> Message:
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
                        tags: Optional[list] = None) -> Optional[Message]:
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
        lines.append(f"\n💬 {msg.get('from_name', msg.get('from_id', '?'))} "
                     f"[{msg.get('timestamp', '')[:16].replace('T', ' ')}]{reply_marker}")
        lines.append(f"   {msg.get('content', '')}")
        if msg.get("tags"):
            lines.append(f"   标签: {', '.join(msg['tags'])}")

    return "\n".join(lines)


def format_message(msg: Message) -> str:
    """格式化单条消息。"""
    lines = [
        f"💬 {msg.from_name} [{msg.timestamp[:16].replace('T', ' ')}]",
        f"   {msg.content}",
    ]
    if msg.tags:
        lines.append(f"   标签: {', '.join(msg.tags)}")
    return "\n".join(lines)
