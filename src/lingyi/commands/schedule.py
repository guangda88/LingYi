"""日程 CLI 命令。"""

import click
from datetime import date, timedelta

from .. import schedule as sched_mod
from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("init")
    @click.argument("preset", default="clinic")
    def schedule_init(preset: str):
        """初始化排班（clinic/ask/practice/journal）"""
        if preset == "clinic":
            items = sched_mod.init_clinic()
            click.echo(f"✓ 门诊排班已初始化（{len(items)}个时段）")
        elif preset == "ask":
            items = sched_mod.init_ask()
            click.echo(f"✓ 灵通问道排班已初始化（{len(items)}个时段）")
        elif preset == "practice":
            items = sched_mod.init_practice()
            click.echo(f"✓ 练功排班已初始化（{len(items)}个时段）")
        elif preset == "journal":
            items = sched_mod.init_journal()
            click.echo(f"✓ 日记提醒已初始化（{len(items)}个时段）")
        else:
            click.echo(f"未知预设：{preset}（可用：clinic, ask, practice, journal）")

    @group.command("add")
    @click.option("--type", "schedule_type", required=True, help="类型：clinic/study/…")
    @click.option("--day", required=True, help="星期：Monday/Tuesday/…")
    @click.option("--time", "time_slot", required=True, help="时段：morning/afternoon/evening")
    @click.option("--desc", default="", help="描述")
    def schedule_add(schedule_type: str, day: str, time_slot: str, desc: str):
        """添加日程"""
        s = sched_mod.add_schedule(schedule_type, day, time_slot, desc)
        click.echo(f"✓ 日程 #{s.id} 已添加：{sched_mod.format_schedule(s)}")

    @group.command("list")
    @click.option("--type", "schedule_type", default=None, help="按类型筛选")
    def schedule_list(schedule_type: str | None):
        """查看所有日程"""
        items = sched_mod.list_schedules(schedule_type=schedule_type)
        if not items:
            click.echo("暂无日程。")
            return
        for s in items:
            click.echo(f"  {sched_mod.format_schedule(s)}")

    @group.command("show")
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

    @group.command("update")
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

    @group.command("cancel")
    @click.argument("schedule_id", type=int)
    def schedule_cancel(schedule_id: int):
        """取消日程"""
        if sched_mod.cancel_schedule(schedule_id):
            click.echo(f"✓ 日程 #{schedule_id} 已取消")
        else:
            click.echo(f"日程 #{schedule_id} 不存在。")

    @group.command("today")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def schedule_today(speak_flag: bool):
        """今日安排"""
        output = sched_mod.format_today()
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))

    @group.command("week")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def schedule_week(speak_flag: bool):
        """本周一览"""
        click.echo("📅 本周排班：")
        output = sched_mod.format_week()
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))

    @group.command("remind")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def schedule_remind(speak_flag: bool):
        """检查今日提醒（练功/日记/门诊/灵通问道）"""
        speech_parts = []
        practice = sched_mod.check_practice_remind()
        if practice:
            click.echo(" Qi 今天早上练功至少30分钟！")
            speech_parts.append("今天早上练功至少30分钟")
        else:
            click.echo("今天没有练功安排。")
        click.echo()
        journal = sched_mod.check_journal_remind()
        if journal:
            click.echo("✍ 今晚11点记得写日记！")
            speech_parts.append("今晚11点记得写日记")
        else:
            click.echo("今天没有日记提醒。")
        click.echo()
        clinics = sched_mod.check_remind()
        if clinics:
            click.echo("⚠ 今天有门诊！")
            speech_parts.append("今天有门诊")
            for s in clinics:
                slot_cn = sched_mod._SLOT_CN.get(s.time_slot, s.time_slot)
                click.echo(f"  {slot_cn}  {s.description or '门诊'}")
                speech_parts.append(f"{slot_cn}{s.description or '门诊'}")
        else:
            click.echo("今天没有门诊。")
        click.echo()
        tomorrow_ask = sched_mod.check_tomorrow_ask()
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_cn = sched_mod._DAY_CN.get(tomorrow.strftime("%A"), "")
        if tomorrow_ask:
            click.echo(f"📢 明天{tomorrow_cn}早上6点有灵通问道更新，请确认内容是否已准备好！")
            speech_parts.append(f"明天{tomorrow_cn}早上6点有灵通问道更新")
        else:
            click.echo(f"明天{tomorrow_cn}没有灵通问道更新。")
        if speak_flag and speech_parts:
            speak(clean_text_for_speech("。".join(speech_parts)))
