"""统一通信离线消息队列。"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ._unified_comm_models import (
    OfflineMessage, _QUEUE_DIR, _MESSAGE_TIMEOUT,
    _calculate_next_retry,
)

logger = logging.getLogger(__name__)


class OfflineMessageQueue:
    """离线消息队列"""

    def __init__(self, queue_dir: Path | None = None):
        self.queue_dir = queue_dir or _QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, message: OfflineMessage) -> None:
        """将消息加入队列"""
        recipient_dir = self.queue_dir / message.recipient_id
        recipient_dir.mkdir(parents=True, exist_ok=True)

        queue_file = recipient_dir / f"{message.message_id}.json"
        queue_file.write_text(
            json.dumps(asdict(message), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"Message queued: {message.message_id} -> {message.recipient_id}")

    def dequeue(self, recipient_id: str) -> list[OfflineMessage]:
        """获取指定收件人的队列消息"""
        recipient_dir = self.queue_dir / recipient_id
        if not recipient_dir.exists():
            return []

        messages: list[OfflineMessage] = []
        now = datetime.now()

        for msg_file in recipient_dir.glob("*.json"):
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                msg = OfflineMessage(**data)

                msg_time = datetime.fromisoformat(msg.timestamp)
                if (now - msg_time).total_seconds() > _MESSAGE_TIMEOUT:
                    msg_file.unlink()
                    logger.warning(f"Expired message removed: {msg.message_id}")
                    continue

                messages.append(msg)
            except Exception as e:
                logger.warning(f"Failed to load queue message: {e}")
                continue

        return sorted(messages, key=lambda m: m.timestamp)

    def remove(self, message_id: str) -> bool:
        """从队列中移除消息"""
        for recipient_dir in self.queue_dir.iterdir():
            if not recipient_dir.is_dir():
                continue

            msg_file = recipient_dir / f"{message_id}.json"
            if msg_file.exists():
                msg_file.unlink()
                logger.info(f"Message removed from queue: {message_id}")
                return True
        return False

    def get_queue_stats(self) -> dict[str, int]:
        """获取队列统计信息"""
        stats: dict[str, int] = {}
        for recipient_dir in self.queue_dir.iterdir():
            if not recipient_dir.is_dir():
                continue
            count = len(list(recipient_dir.glob("*.json")))
            stats[recipient_dir.name] = count
        return stats

    def retry_send(
        self,
        router: "UnifiedMessageRouter",  # noqa: F821
        online_detector: "UnifiedOnlineDetector",  # noqa: F821
    ) -> dict[str, int]:
        """重试发送队列中的离线消息"""
        stats = {"success": 0, "failed": 0, "skipped": 0}
        now = datetime.now()

        for recipient_dir in self.queue_dir.iterdir():
            if not recipient_dir.is_dir():
                continue

            recipient_id = recipient_dir.name

            if not online_detector.check_online(recipient_id):
                stats["skipped"] += 1
                continue

            messages = self.dequeue(recipient_id)
            for msg in messages:
                if msg.next_retry:
                    next_time = datetime.fromisoformat(msg.next_retry)
                    if now < next_time:
                        continue

                if msg.retry_count >= msg.max_retries:
                    self.remove(msg.message_id)
                    logger.warning(f"Max retries exceeded: {msg.message_id}")
                    stats["failed"] += 1
                    continue

                try:
                    result = router.send_message(
                        msg.sender_id,
                        recipient_id,
                        msg.topic,
                        msg.content,
                        msg.message_type,
                        _skip_queue=True
                    )
                    if result.success:
                        self.remove(msg.message_id)
                        stats["success"] += 1
                        logger.info(f"Retry success: {msg.message_id}")
                    else:
                        msg.retry_count += 1
                        msg.next_retry = _calculate_next_retry(msg.retry_count)
                        self._update_message(msg)
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Retry error: {e}")
                    stats["failed"] += 1

        return stats

    def _update_message(self, message: OfflineMessage) -> None:
        """更新队列中的消息"""
        recipient_dir = self.queue_dir / message.recipient_id
        queue_file = recipient_dir / f"{message.message_id}.json"
        queue_file.write_text(
            json.dumps(asdict(message), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
