"""计划 CLI 命令。"""

import click

from .. import plan as plan_mod


def register(group: click.Group):
    @group.command("add")
    @click.argument("content")
    @click.option("--area", default="编程", help="领域：医疗/编程/研究/论文/学术")
    @click.option("--project", "proj", default="", help="关联项目")
    @click.option("--due", default="", help="截止日期 YYYY-MM-DD")
    @click.option("--notes", default="", help="备注")
    def plan_add(content: str, area: str, proj: str, due: str, notes: str):
        """添加计划"""
        p = plan_mod.add_plan(content, area=area, project=proj, due_date=due, notes=notes)
        click.echo(f"✓ 计划 #{p.id} 已添加")

    @group.command("list")
    @click.option("--area", default=None, help="按领域筛选")
    @click.option("--status", default=None, help="按状态筛选：todo/done/cancel")
    @click.option("--project", default=None, help="按项目筛选")
    def plan_list(area: str | None, status: str | None, project: str | None):
        """查看计划列表"""
        items = plan_mod.list_plans(area=area, status=status, project=project)
        if not items:
            click.echo("暂无计划。")
            return
        for p in items:
            click.echo(plan_mod.format_plan_short(p))

    @group.command("show")
    @click.argument("plan_id", type=int)
    def plan_show(plan_id: int):
        """查看计划详情"""
        p = plan_mod.show_plan(plan_id)
        if not p:
            click.echo(f"计划 #{plan_id} 不存在。")
            return
        click.echo(plan_mod.format_plan_detail(p))

    @group.command("done")
    @click.argument("plan_id", type=int)
    def plan_done(plan_id: int):
        """完成任务"""
        p = plan_mod.done_plan(plan_id)
        if not p:
            click.echo(f"计划 #{plan_id} 不存在。")
            return
        click.echo(f"✓ 计划 #{plan_id}「{p.content}」已完成")

    @group.command("cancel")
    @click.argument("plan_id", type=int)
    def plan_cancel(plan_id: int):
        """取消任务"""
        if plan_mod.cancel_plan(plan_id):
            click.echo(f"✓ 计划 #{plan_id} 已取消")
        else:
            click.echo(f"计划 #{plan_id} 不存在。")

    @group.command("week")
    def plan_week():
        """本周计划"""
        click.echo("📋 本周计划：")
        click.echo(plan_mod.format_plan_week())

    @group.command("stats")
    def plan_stats():
        """完成率统计"""
        click.echo("📊 各领域完成率：")
        click.echo(plan_mod.format_plan_stats())
