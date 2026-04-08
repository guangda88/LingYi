# 智桥与LingMessage统一抽象层设计

## 背景

当前存在两套并行的通信系统：

### 系统1: LingMessage (灵信)
- **目的**: 跨项目异步讨论、审计报告、交叉审查
- **存储**: 文件系统 (`~/.lingmessage/discussions/*.json`, `~/.lingmessage/inbox/`)
- **通信方式**: HTTP POST 到各端点的 `/api/lingmessage/notify`
- **特点**:
  - 持久化存储
  - 支持话题分组
  - 支持回复、标注
  - 支持收件箱（新增）
  - 支持送达状态追踪（新增）
  - 3秒超时，无重试，静默失败

### 系统2: 智桥 WebSocket (Zhineng-Bridge)
- **目的**: 用户-AI实时聊天
- **连接**: 长连接 WebSocket (`ws://127.0.0.1:8765`)
- **消息类型**:
  - `register_backend`: AI服务注册
  - `reply`: AI回复用户消息
  - `push`: AI主动推送
  - `chat`: 用户聊天消息
  - `switch_backend`: 切换AI后端
  - `list_backends`: 列出可用的AI后端
  - `ping`: 心跳
- **特点**:
  - 实时双向通信
  - 心跳机制（保持连接）
  - 自动重连
  - 消息路由（根据用户请求路由到不同AI）
  - **没有LingMessage/discussion路由**（已验证）

## 核心问题

**两套系统不互通**：
- 灵通endpoint offline → LingMessage消息无法送达，即使智桥WebSocket连接正常
- 智桥WebSocket只处理用户聊天，不处理跨项目讨论
- 没有统一的在线感知机制
- 没有统一的消息队列和重试机制

## 统一抽象层设计

### 1. 统一成员注册 (Unified Member Registry)

```python
@dataclass
class UnifiedMember:
    member_id: str
    name: str
    lingmessage_endpoint: str | None  # HTTP端点
    bridge_backend_id: str | None    # WebSocket后端ID
    last_online: str | None
    preferred_channel: str = "auto"  # auto | lingmessage | bridge

UNIFIED_MEMBERS = {
    "lingyi": UnifiedMember(
        member_id="lingyi",
        name="灵依",
        lingmessage_endpoint="https://127.0.0.1:8900/api/lingmessage/notify",
        bridge_backend_id="lingyi",
    ),
    "lingzhi": UnifiedMember(
        member_id="lingzhi",
        name="灵知",
        lingmessage_endpoint="http://127.0.0.1:8000/api/v1/lingmessage/notify",
        bridge_backend_id="lingzhi",
    ),
    # ... 其他成员
}
```

### 2. 统一在线感知 (Unified Online Detection)

```python
class UnifiedOnlineDetector:
    def check_online(self, member_id: str) -> bool:
        """检查成员是否在线（双通道检测）"""
        member = UNIFIED_MEMBERS.get(member_id)
        if not member:
            return False

        # 优先检测HTTP端点（LingMessage）
        if member.lingmessage_endpoint:
            if self._ping_http(member.lingmessage_endpoint):
                return True

        # 备用检测WebSocket后端（智桥）
        if member.bridge_backend_id:
            if self._check_bridge_backend(member.bridge_backend_id):
                return True

        return False

    def _ping_http(self, url: str) -> bool:
        """Ping HTTP端点"""
        # 复用 endpoint_monitor.py 的逻辑
        pass

    def _check_bridge_backend(self, backend_id: str) -> bool:
        """检查智桥后端是否在线"""
        # 调用智桥API检查后端注册状态
        pass

    def check_all_online(self) -> dict[str, bool]:
        """检查所有成员在线状态"""
        return {mid: self.check_online(mid) for mid in UNIFIED_MEMBERS}
```

### 3. 统一消息路由器 (Unified Message Router)

```python
class UnifiedMessageRouter:
    def __init__(self, online_detector: UnifiedOnlineDetector):
        self.online_detector = online_detector

    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        topic: str,
        content: str,
        message_type: str = "discussion"  # discussion | chat | notification
    ) -> SendResult:
        """
        发送消息到指定成员

        Args:
            sender_id: 发送者ID
            recipient_id: 接收者ID
            topic: 消息话题
            content: 消息内容
            message_type: 消息类型（discussion/chat/notification）

        Returns:
            SendResult: 包含发送状态和详情
        """
        recipient = UNIFIED_MEMBERS.get(recipient_id)
        if not recipient:
            return SendResult(success=False, error=f"Unknown recipient: {recipient_id}")

        # 检查在线状态
        online = self.online_detector.check_online(recipient_id)

        # 路由决策
        if not online:
            # 离线：放入队列
            return self._enqueue_offline(sender_id, recipient_id, topic, content, message_type)
        elif message_type == "discussion":
            # 讨论：使用LingMessage（持久化）
            return self._send_via_lingmessage(sender_id, recipient_id, topic, content)
        else:
            # 聊天/通知：使用智桥WebSocket（实时）
            return self._send_via_bridge(sender_id, recipient_id, topic, content)

    def _send_via_lingmessage(self, sender_id: str, recipient_id: str, topic: str, content: str) -> SendResult:
        """通过LingMessage发送（讨论类型）"""
        # 复用 lingmessage.py 的逻辑
        msg = send_message(sender_id, topic, content)
        # 更新送达状态
        return SendResult(success=True, message_id=msg.id, channel="lingmessage")

    def _send_via_bridge(self, sender_id: str, recipient_id: str, topic: str, content: str) -> SendResult:
        """通过智桥WebSocket发送（聊天/通知类型）"""
        # 调用 bridge_client.py 发送消息
        return SendResult(success=True, channel="bridge")

    def _enqueue_offline(self, sender_id: str, recipient_id: str, topic: str, content: str, message_type: str) -> SendResult:
        """离线消息入队"""
        # 保存到离线队列
        # 定期重试
        return SendResult(success=False, error="Recipient offline, message queued", channel="queue")
```

### 4. 离线消息队列 (Offline Message Queue)

```python
class OfflineMessageQueue:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, message: OfflineMessage) -> None:
        """将消息加入队列"""
        queue_file = self.queue_dir / f"{message.message_id}.json"
        queue_file.write_text(json.dumps(asdict(message), ensure_ascii=False, indent=2), encoding="utf-8")

    def dequeue(self, recipient_id: str) -> list[OfflineMessage]:
        """获取指定收件人的队列消息"""
        queue_dir = self.queue_dir / recipient_id
        if not queue_dir.exists():
            return []

        messages = []
        for msg_file in sorted(queue_dir.glob("*.json")):
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                messages.append(OfflineMessage(**data))
            except Exception:
                continue

        return sorted(messages, key=lambda m: m.timestamp)

    def remove(self, message_id: str) -> bool:
        """从队列中移除消息"""
        for msg_file in self.queue_dir.glob(f"{message_id}.json"):
            msg_file.unlink()
            return True
        return False

    def retry_send(self, router: UnifiedMessageRouter, online_detector: UnifiedOnlineDetector) -> dict[str, int]:
        """重试发送队列中的离线消息"""
        stats = {"success": 0, "failed": 0}

        for recipient_dir in self.queue_dir.iterdir():
            if not recipient_dir.is_dir():
                continue

            recipient_id = recipient_dir.name

            # 检查是否在线
            if not online_detector.check_online(recipient_id):
                continue

            # 重试发送
            messages = self.dequeue(recipient_id)
            for msg in messages:
                try:
                    result = router.send_message(
                        msg.sender_id,
                        recipient_id,
                        msg.topic,
                        msg.content,
                        msg.message_type,
                    )
                    if result.success:
                        self.remove(msg.message_id)
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1
                except Exception:
                    stats["failed"] += 1

        return stats
```

### 5. 定时重试服务 (Periodic Retry Service)

```python
class RetryScheduler:
    def __init__(self, queue: OfflineMessageQueue, router: UnifiedMessageRouter, detector: UnifiedOnlineDetector):
        self.queue = queue
        self.router = router
        self.detector = detector
        self.running = False

    def start(self, interval: int = 60):
        """启动定时重试（间隔N秒）"""
        self.running = True
        while self.running:
            try:
                stats = self.queue.retry_send(self.router, self.detector)
                if stats["success"] > 0 or stats["failed"] > 0:
                    logger.info(f"Retry stats: {stats}")
            except Exception as e:
                logger.error(f"Retry error: {e}")

            time.sleep(interval)

    def stop(self):
        """停止定时重试"""
        self.running = False
```

## 实现路线图

### Phase 1: 基础设施 (Week 1)
- [x] LingMessage inbox机制
- [x] 端点健康监控
- [x] 送达状态追踪
- [ ] 统一成员注册表
- [ ] 统一在线感知

### Phase 2: 统一路由 (Week 2)
- [ ] 统一消息路由器
- [ ] 离线消息队列
- [ ] 智桥后端状态检测
- [ ] 路由决策逻辑

### Phase 3: 智能重试 (Week 3)
- [ ] 定时重试服务
- [ ] 重试策略（指数退避）
- [ ] 重试统计和监控
- [ ] 失败告警

### Phase 4: 集成测试 (Week 4)
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 故障恢复测试
- [ ] 文档更新

## 数据结构

```python
@dataclass
class OfflineMessage:
    message_id: str
    sender_id: str
    recipient_id: str
    topic: str
    content: str
    message_type: str  # discussion | chat | notification
    timestamp: str
    retry_count: int = 0
    max_retries: int = 10
    next_retry: str

@dataclass
class SendResult:
    success: bool
    message_id: str | None = None
    channel: str | None = None  # lingmessage | bridge | queue
    error: str | None = None
    response_time_ms: float = 0
```

## API设计

### 统一发送消息API

```python
POST /api/unified/send
{
    "sender_id": "lingyi",
    "recipient_id": "lingflow",
    "topic": "v0.16系统审计",
    "content": "请灵通完成v0.16审计交叉审查",
    "message_type": "discussion"
}

Response:
{
    "success": true,
    "message_id": "msg_20260408154753",
    "channel": "lingmessage",
    "response_time_ms": 34
}
```

### 统一在线状态API

```python
GET /api/unified/online

Response:
{
    "lingyi": {"online": true, "last_seen": "2026-04-08T15:47:53", "channel": "lingmessage"},
    "lingflow": {"online": false, "last_seen": "2026-04-07T10:30:00", "channel": "none"},
    "lingzhi": {"online": true, "last_seen": "2026-04-08T15:47:53", "channel": "lingmessage"},
    ...
}
```

### 离线队列API

```python
GET /api/unified/queue/{recipient_id}

Response:
{
    "recipient_id": "lingflow",
    "queued_messages": 5,
    "messages": [
        {
            "message_id": "msg_20260408154753",
            "sender_id": "lingyi",
            "topic": "v0.16系统审计",
            "content": "...",
            "message_type": "discussion",
            "timestamp": "2026-04-08T15:47:53",
            "retry_count": 3
        },
        ...
    ]
}
```

## 关键决策点

### 1. 通道选择策略
- **讨论类型** → LingMessage（需要持久化、话题分组）
- **聊天/通知** → 智桥WebSocket（需要实时性）
- **离线成员** → 离线队列（等待重试）

### 2. 重试策略
- **初始间隔**: 60秒
- **指数退避**: 每次失败后间隔翻倍，最大10分钟
- **最大重试**: 10次（约17小时）
- **超时删除**: 24小时后删除未送达的消息

### 3. 在线检测优先级
- **优先**: HTTP端点（LingMessage）
- **备用**: WebSocket后端（智桥）
- **缓存**: 在线状态缓存60秒，避免频繁检测

### 4. 一致性保证
- **最终一致性**: 消息可能延迟送达，但最终会送达（如果成员上线）
- **幂等性**: 同一消息多次重试，只保留一份
- **顺序性**: 同一发送者的消息按时间顺序送达

## 监控指标

- 在线率（各成员）
- 送达率（按通道、按成员）
- 重试次数（按消息）
- 队列长度（各成员）
- 平均送达时间

## 下一步行动

1. 实现 `UnifiedMember` 注册表
2. 实现 `UnifiedOnlineDetector`（整合 endpoint_monitor.py）
3. 实现 `OfflineMessageQueue`（复用 inbox 机制）
4. 实现 `UnifiedMessageRouter`（整合 lingmessage 和 bridge）
5. 实现 `RetryScheduler`（后台任务）
6. 添加API端点和CLI命令
7. 集成测试和文档更新
