"""灵信 LingMessage CLI 命令。"""

import click

from .. import lingmessage as lm


_VALID_PROJECTS = list(lm.PROJECTS.keys())


def register(group: click.Group):
    @group.command("msg-send")
    @click.option("--from", "from_id", required=True, help="发送者项目ID（如 lingyi/lingflow/lingclaude）")
    @click.option("--topic", required=True, help="讨论话题")
    @click.argument("content")
    def msg_send(from_id: str, topic: str, content: str):
        """发送消息到灵信讨论"""
        if from_id not in _VALID_PROJECTS:
            click.echo(f"未知项目: {from_id}。有效项目: {', '.join(_VALID_PROJECTS)}")
            return
        lm.init_store()
        msg = lm.send_message(from_id, topic, content)
        click.echo(f"✓ 消息已发送")
        click.echo(lm.format_message(msg))

    @group.command("msg-list")
    @click.option("--status", default=None, help="过滤状态（open/closed）")
    def msg_list(status: str | None):
        """列出灵信讨论"""
        lm.init_store()
        discussions = lm.list_discussions(status)
        click.echo(lm.format_discussion_list(discussions))

    @group.command("msg-read")
    @click.argument("discussion_id")
    def msg_read(discussion_id: str):
        """阅读讨论线程"""
        disc = lm.read_discussion(discussion_id)
        if not disc:
            click.echo(f"讨论不存在: {discussion_id}")
            return
        click.echo(lm.format_discussion_thread(disc))

    @group.command("msg-reply")
    @click.argument("discussion_id")
    @click.option("--from", "from_id", required=True, help="回复者项目ID")
    @click.argument("content")
    def msg_reply(discussion_id: str, from_id: str, content: str):
        """回复讨论"""
        if from_id not in _VALID_PROJECTS:
            click.echo(f"未知项目: {from_id}。有效项目: {', '.join(_VALID_PROJECTS)}")
            return
        msg = lm.reply_to_discussion(discussion_id, from_id, content)
        if not msg:
            click.echo("回复失败：讨论不存在或已关闭")
            return
        click.echo("✓ 回复已发送")
        click.echo(lm.format_message(msg))

    @group.command("msg-discuss")
    @click.option("--from", "from_id", required=True, help="发起者项目ID")
    @click.argument("topic")
    @click.argument("content")
    def msg_discuss(from_id: str, topic: str, content: str):
        """发起或加入讨论"""
        if from_id not in _VALID_PROJECTS:
            click.echo(f"未知项目: {from_id}。有效项目: {', '.join(_VALID_PROJECTS)}")
            return
        lm.init_store()
        msg = lm.send_message(from_id, topic, content)
        click.echo("✓ 已发起/加入讨论")
        click.echo(lm.format_message(msg))

    @group.command("msg-search")
    @click.argument("keyword")
    def msg_search(keyword: str):
        """搜索灵信消息"""
        results = lm.search_messages(keyword)
        if not results:
            click.echo(f"未找到包含「{keyword}」的消息")
            return
        click.echo(f"找到 {len(results)} 条消息:")
        for m in results:
            click.echo(f"\n  💬 {m.get('from_name', '?')} "
                       f"[{m.get('timestamp', '')[:16].replace('T', ' ')}]")
            content = m.get("content", "")
            click.echo(f"     {content[:100]}{'...' if len(content) > 100 else ''}")

    @group.command("msg-close")
    @click.argument("discussion_id")
    def msg_close(discussion_id: str):
        """关闭讨论"""
        if lm.close_discussion(discussion_id):
            click.echo(f"✓ 讨论已关闭: {discussion_id}")
        else:
            click.echo(f"关闭失败：讨论不存在: {discussion_id}")

    @group.command("msg-annotate")
    @click.argument("discussion_id")
    def msg_annotate(discussion_id: str):
        """自动标注讨论中的消息来源"""
        result = lm.annotate_discussion(discussion_id)
        if "error" in result:
            click.echo(f"错误: {result['error']}")
            return
        click.echo(f"讨论: {discussion_id}")
        click.echo(f"  总消息: {result['total_messages']}")
        click.echo(f"  时间异常: {result['anomalies']}")
        click.echo(f"  已更新标注: {result['updated']}")
        if result["anomaly_details"]:
            click.echo("\n异常详情:")
            for detail in result["anomaly_details"]:
                click.echo(f"  ⚠️  {detail}")
