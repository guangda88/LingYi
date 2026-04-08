"""统一通信层 — 整合LingMessage和智桥WebSocket。

提供统一的消息发送、在线感知、离线队列和重试机制。
解决两套并行系统不互通的问题。
"""

from __future__ import annotations

import json
import logging
import time

from .endpoint_monitor import ping_endpoint
from .lingmessage import send_message, get_delivery_status
from ._unified_comm_models import (
    UnifiedMember, UNIFIED_MEMBERS,
    OfflineMessage, SendResult,
    _now, _msg_id, _calculate_next_retry,
)
from ._unified_comm_queue import OfflineMessageQueue

__all__ = [
    "UnifiedMember", "UNIFIED_MEMBERS",
    "OfflineMessage", "SendResult",
    "OfflineMessageQueue",
    "UnifiedOnlineDetector", "UnifiedMessageRouter", "RetryScheduler",
]

logger = logging.getLogger(__name__)


class UnifiedOnlineDetector:
    """统一在线检测器（双通道检测）"""

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[bool, str]] = {}

    def check_online(self, member_id: str) -> bool:
        """检查成员是否在线（双通道检测）"""
        if member_id in self._cache:
            cached_online, cached_at = self._cache[member_id]
            from datetime import datetime
            cached_time = datetime.fromisoformat(cached_at)
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_online

        member = UNIFIED_MEMBERS.get(member_id)
        if not member:
            return False

        online = False

        if member.lingmessage_endpoint:
            if member_id in [
                "lingyi", "lingzhi", "lingminopt", "lingresearch",
                "lingclaude", "lingflow", "lingyang",
            ]:
                endpoint_id = member_id
            else:
                endpoint_id = member_id

            status = ping_endpoint(endpoint_id)
            online = status.online

        if not online and member.bridge_backend_id:
            online = self._check_bridge_backend(member.bridge_backend_id)

        self._cache[member_id] = (online, _now())
        return online

    def _check_bridge_backend(self, backend_id: str) -> bool:
        """检查智桥后端是否在线"""
        try:
            import urllib.request

            url = f"http://127.0.0.1:8765/api/backends/{backend_id}/status"
            req = urllib.request.Request(url, method="GET")

            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("online", False)
        except Exception as e:
            logger.debug(f"Bridge backend check failed: {e}")
            return False

    def check_all_online(self) -> dict[str, bool]:
        """检查所有成员在线状态"""
        return {mid: self.check_online(mid) for mid in UNIFIED_MEMBERS}

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()


class UnifiedMessageRouter:
    """统一消息路由器"""

    def __init__(self, online_detector: UnifiedOnlineDetector):
        self.online_detector = online_detector

    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        topic: str,
        content: str,
        message_type: str = "discussion",
        _skip_queue: bool = False,
    ) -> SendResult:
        recipient = UNIFIED_MEMBERS.get(recipient_id)
        if not recipient:
            return SendResult(
                success=False,
                error=f"Unknown recipient: {recipient_id}"
            )

        online = self.online_detector.check_online(recipient_id)

        if not online:
            if not _skip_queue:
                return self._enqueue_offline(
                    sender_id, recipient_id, topic, content, message_type
                )
            else:
                return SendResult(
                    success=False,
                    error="Recipient offline and queue skipped",
                    channel="none"
                )
        elif message_type == "discussion":
            return self._send_via_lingmessage(
                sender_id, recipient_id, topic, content
            )
        else:
            return self._send_via_bridge(
                sender_id, recipient_id, topic, content
            )

    def _send_via_lingmessage(
        self,
        sender_id: str,
        recipient_id: str,
        topic: str,
        content: str,
    ) -> SendResult:
        try:
            import time as _time
            start = _time.time()

            msg = send_message(sender_id, topic, content)

            response_time_ms = (_time.time() - start) * 1000

            status = get_delivery_status(msg.id)
            delivered = any(
                s.get("status") == "delivered"
                for s in status.get("recipients", {}).values()
            )

            return SendResult(
                success=delivered,
                message_id=msg.id,
                channel="lingmessage",
                response_time_ms=round(response_time_ms, 2),
                error=None if delivered else "Message sent but not delivered"
            )
        except Exception as e:
            return SendResult(
                success=False,
                channel="lingmessage",
                error=str(e)[:100]
            )

    def _send_via_bridge(
        self,
        sender_id: str,
        recipient_id: str,
        topic: str,
        content: str,
    ) -> SendResult:
        try:
            import time as _time
            start = _time.time()

            import urllib.request
            import json as _json

            url = "http://127.0.0.1:8765/api/send"
            data = {
                "backend_id": recipient_id,
                "sender_id": sender_id,
                "topic": topic,
                "content": content,
            }

            req = urllib.request.Request(
                url,
                data=_json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    response_time_ms = (_time.time() - start) * 1000
                    return SendResult(
                        success=True,
                        channel="bridge",
                        response_time_ms=round(response_time_ms, 2),
                    )
                else:
                    return SendResult(
                        success=False,
                        channel="bridge",
                        error=f"HTTP {resp.status}"
                    )
        except Exception as e:
            return SendResult(
                success=False,
                channel="bridge",
                error=str(e)[:100]
            )

    def _enqueue_offline(
        self,
        sender_id: str,
        recipient_id: str,
        topic: str,
        content: str,
        message_type: str,
    ) -> SendResult:
        msg = OfflineMessage(
            message_id=_msg_id(),
            sender_id=sender_id,
            recipient_id=recipient_id,
            topic=topic,
            content=content,
            message_type=message_type,
            timestamp=_now(),
            next_retry=_calculate_next_retry(0),
        )

        queue = OfflineMessageQueue()
        queue.enqueue(msg)

        return SendResult(
            success=False,
            message_id=msg.message_id,
            channel="queue",
            error="Recipient offline, message queued"
        )


class RetryScheduler:
    """定时重试服务"""

    def __init__(
        self,
        queue: OfflineMessageQueue,
        router: UnifiedMessageRouter,
        detector: UnifiedOnlineDetector,
        interval: int = 60,
    ):
        self.queue = queue
        self.router = router
        self.detector = detector
        self.interval = interval
        self.running = False

    def start(self):
        """启动定时重试（阻塞）"""
        logger.info(f"启动重试调度器，间隔: {self.interval}秒")
        self.running = True

        while self.running:
            try:
                stats = self.queue.retry_send(self.router, self.detector)
                if stats["success"] > 0 or stats["failed"] > 0:
                    logger.info(f"重试统计: {stats}")
            except Exception as e:
                logger.error(f"重试调度器错误: {e}")

            time.sleep(self.interval)

    def stop(self):
        """停止定时重试"""
        logger.info("停止重试调度器")
        self.running = False
