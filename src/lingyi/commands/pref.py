"""偏好管理 CLI 命令。"""

import click

from .. import pref as pref_mod


def register(group: click.Group):
    @group.command("set")
    @click.argument("key")
    @click.argument("value")
    def pref_set(key: str, value: str):
        """设置偏好"""
        pref_mod.set_pref(key, value)
        click.echo(f"✓ {key} = {value}")

    @group.command("get")
    @click.argument("key")
    def pref_get(key: str):
        """查看偏好"""
        val = pref_mod.get_pref(key)
        if val is None:
            click.echo(f"偏好 '{key}' 不存在。")
        else:
            click.echo(f"  {key} = {val}")

    @group.command("list")
    def pref_list():
        """查看所有偏好"""
        prefs = pref_mod.list_prefs()
        click.echo(pref_mod.format_pref_list(prefs))

    @group.command("delete")
    @click.argument("key")
    def pref_delete(key: str):
        """删除偏好"""
        if pref_mod.delete_pref(key):
            click.echo(f"✓ 偏好 '{key}' 已删除")
        else:
            click.echo(f"偏好 '{key}' 不存在。")
