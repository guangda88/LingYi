"""统一通信层CLI命令。"""

import click

from ..unified_comm import (
    UnifiedOnlineDetector,
    UnifiedMessageRouter,
    OfflineMessageQueue,
    UNIFIED_MEMBERS,
)


@click.group()
def unified():
    """统一通信层 — 整合LingMessage和智桥"""
    pass


@unified.command("online")
def unified_online():
    """显示所有成员在线状态"""
    detector = UnifiedOnlineDetector()
    online_status = detector.check_all_online()

    click.echo("📡 统一在线状态")
    click.echo("=" * 50)

    online_count = sum(1 for online in online_status.values() if online)
    total_count = len(online_status)

    click.echo(f"在线: {online_count}/{total_count}")
    click.echo()

    for member_id, online in sorted(online_status.items()):
        member = UNIFIED_MEMBERS.get(member_id)
        if member:
            icon = "🟢" if online else "🔴"
            click.echo(f"{icon} {member.name} ({member_id}) - {'在线' if online else '离线'}")


@unified.command("send")
@click.option("--sender", "-s", default="lingyi", help="发送者ID")
@click.option("--recipient", "-r", required=True, help="接收者ID")
@click.option("--topic", "-t", required=True, help="消息话题")
@click.option("--type", "msg_type", default="discussion", type=click.Choice(["discussion", "chat", "notification"]), help="消息类型")
@click.argument("content")
def unified_send(sender, recipient, topic, msg_type, content):
    """发送消息（统一路由）"""
    # 验证发送者
    if sender not in UNIFIED_MEMBERS:
        click.echo(f"❌ 未知发送者: {sender}", err=True)
        return

    # 验证接收者
    if recipient not in UNIFIED_MEMBERS:
        click.echo(f"❌ 未知接收者: {recipient}", err=True)
        return

    # 初始化路由器
    detector = UnifiedOnlineDetector()
    router = UnifiedMessageRouter(detector)

    # 发送消息
    result = router.send_message(sender, recipient, topic, content, msg_type)

    if result.success:
        click.echo("✅ 消息发送成功")
        click.echo(f"   消息ID: {result.message_id}")
        click.echo(f"   通道: {result.channel}")
        if result.response_time_ms > 0:
            click.echo(f"   响应时间: {result.response_time_ms:.2f}ms")
    else:
        click.echo(f"⚠️  消息发送失败: {result.error}")
        if result.message_id:
            click.echo(f"   消息ID: {result.message_id}")
        click.echo(f"   通道: {result.channel}")


@unified.command("queue")
@click.option("--recipient", "-r", help="查看指定收件人的队列")
def unified_queue(recipient):
    """显示离线消息队列状态"""
    queue = OfflineMessageQueue()

    if recipient:
        # 查看指定收件人的队列
        messages = queue.dequeue(recipient)
        if not messages:
            click.echo(f"📭 {recipient} 的队列为空")
        else:
            member = UNIFIED_MEMBERS.get(recipient)
            member_name = member.name if member else recipient
            click.echo(f"📬 {member_name} ({recipient}) 的离线队列")
            click.echo("=" * 50)
            click.echo(f"共 {len(messages)} 条消息")
            click.echo()

            for msg in messages:
                click.echo(f"📨 {msg.message_id}")
                click.echo(f"   发送者: {msg.sender_id}")
                click.echo(f"   话题: {msg.topic}")
                click.echo(f"   时间: {msg.timestamp}")
                click.echo(f"   类型: {msg.message_type}")
                click.echo(f"   重试: {msg.retry_count}/{msg.max_retries}")
                if msg.next_retry:
                    click.echo(f"   下次重试: {msg.next_retry}")
                click.echo(f"   内容: {msg.content[:100]}...")
                click.echo()
    else:
        # 查看所有队列统计
        stats = queue.get_queue_stats()
        if not stats:
            click.echo("📭 离线队列为空")
        else:
            click.echo("📬 离线队列统计")
            click.echo("=" * 50)
            for recipient_id, count in sorted(stats.items()):
                member = UNIFIED_MEMBERS.get(recipient_id)
                member_name = member.name if member else recipient_id
                click.echo(f"{member_name} ({recipient_id}): {count} 条消息")


@unified.command("retry")
@click.option("--once", is_flag=True, help="只重试一次")
def unified_retry(once):
    """手动触发队列重试"""
    detector = UnifiedOnlineDetector()
    router = UnifiedMessageRouter(detector)
    queue = OfflineMessageQueue()

    if once:
        # 只重试一次
        click.echo("🔄 触发队列重试...")
        stats = queue.retry_send(router, detector)
        click.echo(f"重试统计: {stats}")
    else:
        # 启动后台重试调度器
        from .unified_comm import RetryScheduler

        scheduler = RetryScheduler(queue, router, detector)
        click.echo("🔄 启动后台重试调度器（Ctrl+C停止）")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            scheduler.stop()
            click.echo("\n⏹️ 重试调度器已停止")


def register(group: click.Group):
    """注册统一通信层命令到主CLI组"""
    unified_cmd = unified
    group.add_command(unified_cmd)
