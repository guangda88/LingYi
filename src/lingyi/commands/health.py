"""端点健康监控 CLI 命令。"""

import click

from .. import endpoint_monitor as em


def register(group: click.Group):
    @group.command("health-check")
    def health_check():
        """检查所有端点健康状态"""
        em.check_all_endpoints()
        summary = em.get_health_summary()
        click.echo(em.format_health_summary(summary))

    @group.command("health-summary")
    def health_summary():
        """显示健康状态摘要"""
        summary = em.get_health_summary()
        click.echo(em.format_health_summary(summary))

    @group.command("health-online")
    def health_online():
        """仅显示在线端点"""
        results = em.check_all_endpoints()
        online = [r for r in results.values() if r.online]
        if not online:
            click.echo("🔴 无在线端点")
            return
        click.echo(f"🟢 在线端点 ({len(online)}):")
        for r in online:
            click.echo(f"  - {r.name} ({r.member_id}) - {r.response_time_ms:.0f}ms")

    @group.command("health-offline")
    def health_offline():
        """仅显示离线端点"""
        results = em.check_all_endpoints()
        offline = [r for r in results.values() if not r.online]
        if not offline:
            click.echo("🟢 所有端点在线")
            return
        click.echo(f"🔴 离线端点 ({len(offline)}):")
        for r in offline:
            if r.last_online:
                last_online_str = r.last_online[:16].replace("T", " ")
                click.echo(f"  - {r.name} ({r.member_id}) - 上次在线: {last_online_str}")
                if r.error:
                    click.echo(f"    错误: {r.error}")
            else:
                click.echo(f"  - {r.name} ({r.member_id}) - 从未在线")
                if r.error:
                    click.echo(f"    错误: {r.error}")
