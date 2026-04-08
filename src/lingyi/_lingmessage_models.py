"""灵信数据模型 — 常量、数据类、ID生成、存储路径。"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_STORE_DIR = Path(os.environ.get("LINGMESSAGE_DIR", "/home/ai/.lingmessage"))

SOURCE_TYPE_LABELS = {
    "real": "✅ 真实通信",
    "inferred": "🔮 AI推演",
    "unverifiable": "⚠️ 无法验证",
}

PROJECTS = {
    "lingflow": {"name": "灵通", "role": "工作流引擎"},
    "lingclaude": {"name": "灵克", "role": "编程助手"},
    "lingzhi": {"name": "灵知", "role": "知识库"},
    "lingyi": {"name": "灵依", "role": "情报中枢"},
    "lingtongask": {"name": "灵通问道", "role": "内容平台"},
    "lingterm": {"name": "灵犀", "role": "终端感知"},
    "lingminopt": {"name": "灵极优", "role": "自优化框架"},
    "lingresearch": {"name": "灵妍", "role": "科研优化"},
    "zhibridge": {"name": "智桥", "role": "HTTP中继"},
    "lingyang": {"name": "灵扬", "role": "对外窗口"},
    "guangda": {"name": "广大老师", "role": "人类用户"},
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
    source_type: str = "unverifiable"


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
    (store / "inbox").mkdir(exist_ok=True)
    for member_id in PROJECTS.keys():
        member_inbox = store / "inbox" / member_id
        member_inbox.mkdir(parents=True, exist_ok=True)
    return store
