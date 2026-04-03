"""会话管理 CLI 命令。"""

import click

from .. import session as session_mod


def register(group: click.Group):
    @group.command("save")
    @click.option("--summary", default="", help="会话摘要")
    @click.option("--files", default="", help="修改的文件")
    @click.option("--decisions", default="", help="关键决策")
    @click.option("--todos", default="", help="待办事项")
    @click.option("--prefs-noted", default="", help="发现的用户偏好")
    def session_save(summary: str, files: str, decisions: str, todos: str, prefs_noted: str):
        """保存当前会话摘要"""
        if not any([summary, files, decisions, todos, prefs_noted]):
            click.echo("请至少提供一项内容 (--summary/--files/--decisions/--todos/--prefs-noted)。")
            return
        s = session_mod.save_session(summary, files, decisions, todos, prefs_noted)
        click.echo(f"✓ 会话 #{s.id} 已保存 ({s.created_at})")

    @group.command("last")
    def session_last():
        """查看上次会话摘要"""
        s = session_mod.last_session()
        if not s:
            click.echo("暂无会话记录。")
            return
        click.echo(session_mod.format_session_detail(s))

    @group.command("resume")
    def session_resume():
        """输出上次会话摘要（供AI读入）"""
        s = session_mod.last_session()
        if not s:
            click.echo("暂无会话记录。")
            return
        click.echo(session_mod.format_session_resume(s))

    @group.command("list")
    @click.option("--limit", default=10, help="显示条数")
    def session_list(limit: int):
        """查看会话列表"""
        sessions = session_mod.list_sessions(limit)
        if not sessions:
            click.echo("暂无会话记录。")
            return
        for s in sessions:
            click.echo(session_mod.format_session_short(s))

    @group.command("show")
    @click.argument("session_id", type=int)
    def session_show(session_id: int):
        """查看指定会话详情"""
        s = session_mod.get_session(session_id)
        if not s:
            click.echo(f"会话 #{session_id} 不存在。")
            return
        click.echo(session_mod.format_session_detail(s))

    @group.command("delete")
    @click.argument("session_id", type=int)
    def session_delete(session_id: int):
        """删除会话记录"""
        if session_mod.delete_session(session_id):
            click.echo(f"✓ 会话 #{session_id} 已删除")
        else:
            click.echo(f"会话 #{session_id} 不存在。")
