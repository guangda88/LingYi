"""统一通信数据模型与成员注册表。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_QUEUE_DIR = Path.home() / ".lingmessage" / "queue"

_INITIAL_RETRY_INTERVAL = 60
_MAX_RETRY_INTERVAL = 600
_MAX_RETRIES = 10
_MESSAGE_TIMEOUT = 86400


@dataclass
class UnifiedMember:
    """统一成员配置"""
    member_id: str
    name: str
    lingmessage_endpoint: str | None
    bridge_backend_id: str | None
    last_online: str | None = None
    preferred_channel: str = "auto"


UNIFIED_MEMBERS: dict[str, UnifiedMember] = {
    "lingyi": UnifiedMember(
        member_id="lingyi", name="灵依",
        lingmessage_endpoint="https://127.0.0.1:8900/api/lingmessage/notify",
        bridge_backend_id="lingyi",
    ),
    "lingzhi": UnifiedMember(
        member_id="lingzhi", name="灵知",
        lingmessage_endpoint="http://127.0.0.1:8000/api/v1/lingmessage/notify",
        bridge_backend_id="lingzhi",
    ),
    "lingzhi_auto": UnifiedMember(
        member_id="lingzhi_auto", name="灵知(auto)",
        lingmessage_endpoint=None, bridge_backend_id="lingzhi_auto",
    ),
    "lingminopt": UnifiedMember(
        member_id="lingminopt", name="灵极优",
        lingmessage_endpoint="http://127.0.0.1:8002/api/lingmessage/notify",
        bridge_backend_id="lingminopt",
    ),
    "lingresearch": UnifiedMember(
        member_id="lingresearch", name="灵妍",
        lingmessage_endpoint="http://127.0.0.1:8003/api/lingmessage/notify",
        bridge_backend_id="lingresearch",
    ),
    "lingclaude": UnifiedMember(
        member_id="lingclaude", name="灵克",
        lingmessage_endpoint="http://127.0.0.1:8700/api/lingmessage/notify",
        bridge_backend_id="lingclaude",
    ),
    "lingflow": UnifiedMember(
        member_id="lingflow", name="灵通",
        lingmessage_endpoint="http://127.0.0.1:8600/api/lingmessage/notify",
        bridge_backend_id="lingflow",
    ),
    "zhibridge": UnifiedMember(
        member_id="zhibridge", name="智桥",
        lingmessage_endpoint=None, bridge_backend_id="zhibridge",
    ),
    "lingyang": UnifiedMember(
        member_id="lingyang", name="灵扬",
        lingmessage_endpoint="http://127.0.0.1:8021/api/lingmessage/notify",
        bridge_backend_id="lingyang",
    ),
}


@dataclass
class OfflineMessage:
    """离线队列消息"""
    message_id: str
    sender_id: str
    recipient_id: str
    topic: str
    content: str
    message_type: str
    timestamp: str
    retry_count: int = 0
    max_retries: int = _MAX_RETRIES
    next_retry: str | None = None


@dataclass
class SendResult:
    """发送结果"""
    success: bool
    message_id: str | None = None
    channel: str | None = None
    error: str | None = None
    response_time_ms: float = 0


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _msg_id() -> str:
    ms = _now().replace("-", "").replace("T", "").replace(":", "")
    return f"msg_{ms}"


def _calculate_next_retry(retry_count: int) -> str:
    """计算下次重试时间（指数退避）"""
    interval = min(
        _INITIAL_RETRY_INTERVAL * (2 ** retry_count),
        _MAX_RETRY_INTERVAL
    )
    next_time = datetime.now() + timedelta(seconds=interval)
    return next_time.strftime("%Y-%m-%dT%H:%M:%S")
