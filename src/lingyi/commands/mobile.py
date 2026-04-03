"""移动端适配 CLI 命令。"""

import click

from .. import mobile as mobile_mod


def register(group: click.Group):
    @group.command("env")
    def do_env():
        """查看当前运行环境信息"""
        env = mobile_mod.detect_environment()
        click.echo(mobile_mod.format_env_info(env))
