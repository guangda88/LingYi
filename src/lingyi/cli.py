"""灵依 LingYi CLI 入口。"""

import click

from . import __version__, patrol as patrol_mod, report as report_mod
from .commands import memo as memo_cmds
from .commands import schedule as sched_cmds
from .commands import project as proj_cmds
from .commands import plan as plan_cmds
from .commands import session as session_cmds
from .commands import pref as pref_cmds
from .commands import chat as chat_cmds
from .commands import connect as connect_cmds


@click.group()
@click.version_option(__version__, message="灵依 v%(version)s")
def cli():
    """灵依 — 你的私我AI助理"""
    pass


@cli.group()
def memo():
    """备忘录"""
    pass


@cli.group()
def schedule():
    """日程管理"""
    pass


@cli.group("project")
def project():
    """项目管理"""
    pass


@cli.group("plan")
def plan():
    """工作计划"""
    pass


@cli.group("session")
def session():
    """会话记忆"""
    pass


@cli.group("pref")
def pref():
    """偏好设置"""
    pass


memo_cmds.register(memo)
sched_cmds.register(schedule)
proj_cmds.register(project)
plan_cmds.register(plan)
session_cmds.register(session)
pref_cmds.register(pref)
chat_cmds.register(cli)
connect_cmds.register(cli)


@cli.command("patrol")
def do_patrol():
    """巡检所有项目变化"""
    click.echo(patrol_mod.generate_report())


@cli.command("report")
@click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
def do_report(speak_flag: bool):
    """生成本周周报"""
    output = report_mod.generate_weekly_report()
    click.echo(output)
    if speak_flag:
        from .tts import speak, clean_text_for_speech
        speak(clean_text_for_speech(output))


if __name__ == "__main__":
    cli()
