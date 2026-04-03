"""灵依 LingYi CLI 入口。"""

import click
from datetime import date, timedelta

from . import __version__, patrol as patrol_mod
from . import memo as memo_mod
from . import schedule as sched_mod


@click.group()
@click.version_option(__version__, message="灵依 v%(version)s")
def cli():
    """灵依 — 你的私我AI助理"""
    pass


# ── memo ──────────────────────────────────────────────

@cli.group()
def memo():
    """备忘录"""
    pass


@memo.command("add")
@click.argument("content")
def memo_add(content: str):
    """添加备忘"""
    m = memo_mod.add_memo(content)
    click.echo(f"✓ 备忘 #{m.id} 已添加")


@memo.command("list")
def memo_list():
    """查看所有备忘"""
    memos = memo_mod.list_memos()
    if not memos:
        click.echo("暂无备忘。")
        return
    for m in memos:
        click.echo(f"  [{m.id}] {m.content}  ({m.created_at})")


@memo.command("show")
@click.argument("memo_id", type=int)
def memo_show(memo_id: int):
    """查看单条备忘"""
    m = memo_mod.show_memo(memo_id)
    if not m:
        click.echo(f"备忘 #{memo_id} 不存在。")
        return
    click.echo(f"  #{m.id}")
    click.echo(f"  内容：{m.content}")
    click.echo(f"  创建：{m.created_at}")
    click.echo(f"  更新：{m.updated_at}")


@memo.command("delete")
@click.argument("memo_id", type=int)
def memo_delete(memo_id: int):
    """删除备忘"""
    if memo_mod.delete_memo(memo_id):
        click.echo(f"✓ 备忘 #{memo_id} 已删除")
    else:
        click.echo(f"备忘 #{memo_id} 不存在。")


# ── schedule ──────────────────────────────────────────

@cli.group()
def schedule():
    """日程管理"""
    pass


@schedule.command("init")
@click.argument("preset", default="clinic")
def schedule_init(preset: str):
    """初始化排班（clinic/ask）"""
    if preset == "clinic":
        items = sched_mod.init_clinic()
        click.echo(f"✓ 门诊排班已初始化（{len(items)}个时段）")
    elif preset == "ask":
        items = sched_mod.init_ask()
        click.echo(f"✓ 灵通问道排班已初始化（{len(items)}个时段）")
    else:
        click.echo(f"未知预设：{preset}（可用：clinic, ask）")


@schedule.command("add")
@click.option("--type", "schedule_type", required=True, help="类型：clinic/study/…")
@click.option("--day", required=True, help="星期：Monday/Tuesday/…")
@click.option("--time", "time_slot", required=True, help="时段：morning/afternoon/evening")
@click.option("--desc", default="", help="描述")
def schedule_add(schedule_type: str, day: str, time_slot: str, desc: str):
    """添加日程"""
    s = sched_mod.add_schedule(schedule_type, day, time_slot, desc)
    click.echo(f"✓ 日程 #{s.id} 已添加：{sched_mod.format_schedule(s)}")


@schedule.command("list")
@click.option("--type", "schedule_type", default=None, help="按类型筛选")
def schedule_list(schedule_type: str | None):
    """查看所有日程"""
    items = sched_mod.list_schedules(schedule_type=schedule_type)
    if not items:
        click.echo("暂无日程。")
        return
    for s in items:
        click.echo(f"  {sched_mod.format_schedule(s)}")


@schedule.command("show")
@click.argument("schedule_id", type=int)
def schedule_show(schedule_id: int):
    """查看日程详情"""
    s = sched_mod.show_schedule(schedule_id)
    if not s:
        click.echo(f"日程 #{schedule_id} 不存在。")
        return
    click.echo(f"  #{s.id}")
    click.echo(f"  类型：{s.type}")
    click.echo(f"  时间：{s.day} {s.time_slot}")
    click.echo(f"  描述：{s.description or '—'}")
    click.echo(f"  状态：{'活跃' if s.is_active else '已取消'}")


@schedule.command("update")
@click.argument("schedule_id", type=int)
@click.option("--type", "schedule_type", default=None)
@click.option("--day", default=None)
@click.option("--time", "time_slot", default=None)
@click.option("--desc", default=None)
def schedule_update(schedule_id: int, schedule_type: str | None, day: str | None,
                    time_slot: str | None, desc: str | None):
    """修改日程"""
    kwargs = {}
    if schedule_type:
        kwargs["type"] = schedule_type
    if day:
        kwargs["day"] = day
    if time_slot:
        kwargs["time_slot"] = time_slot
    if desc is not None:
        kwargs["description"] = desc
    s = sched_mod.update_schedule(schedule_id, **kwargs)
    if not s:
        click.echo(f"日程 #{schedule_id} 不存在。")
        return
    click.echo(f"✓ 已更新：{sched_mod.format_schedule(s)}")


@schedule.command("cancel")
@click.argument("schedule_id", type=int)
def schedule_cancel(schedule_id: int):
    """取消日程"""
    if sched_mod.cancel_schedule(schedule_id):
        click.echo(f"✓ 日程 #{schedule_id} 已取消")
    else:
        click.echo(f"日程 #{schedule_id} 不存在。")


@schedule.command("today")
def schedule_today():
    """今日安排"""
    click.echo(sched_mod.format_today())


@schedule.command("week")
def schedule_week():
    """本周一览"""
    click.echo("📅 本周排班：")
    click.echo(sched_mod.format_week())


@schedule.command("remind")
def schedule_remind():
    """检查今日门诊 + 明日灵通问道"""
    clinics = sched_mod.check_remind()
    if clinics:
        click.echo("⚠ 今天有门诊！")
        for s in clinics:
            slot_cn = sched_mod._SLOT_CN.get(s.time_slot, s.time_slot)
            click.echo(f"  {slot_cn}  {s.description or '门诊'}")
    else:
        click.echo("今天没有门诊。")
    click.echo()
    tomorrow_ask = sched_mod.check_tomorrow_ask()
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_cn = sched_mod._DAY_CN.get(tomorrow.strftime("%A"), "")
    if tomorrow_ask:
        click.echo(f"📢 明天{tomorrow_cn}早上6点有灵通问道更新，请确认内容是否已准备好！")
    else:
        click.echo(f"明天{tomorrow_cn}没有灵通问道更新。")


# ── patrol ───────────────────────────────────────────

@cli.command("patrol")
def do_patrol():
    """巡检所有项目变化"""
    click.echo(patrol_mod.generate_report())


if __name__ == "__main__":
    cli()
