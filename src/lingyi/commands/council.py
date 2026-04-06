"""议事厅守护进程 CLI 命令。"""

import click


def register(group: click.Group):
    @group.command("council")
    @click.option("--interval", default=300, help="扫描间隔（秒）")
    @click.option("--once", is_flag=True, help="只扫描一次后退出")
    @click.option("--status", "show_status", is_flag=True, help="查看议事厅状态")
    @click.option("--health", "show_health", is_flag=True, help="全面健康检查")
    @click.option("--wake", nargs=2, type=str, help="手动唤醒成员: --wake <member_id> <disc_id>")
    def do_council(interval: int, once: bool, show_status: bool, show_health: bool, wake: tuple | None):
        """灵家议事厅守护进程 — 客厅的灯"""
        if show_health:
            from ..council import council_health
            report = council_health()
            summary = report["summary"]

            status_icon = "✅" if summary["status"] == "HEALTHY" else "⚠️"
            lines = [
                f"{status_icon} 灵家议事厅健康检查",
                "=" * 50,
                f"  讨论总数:   {summary['total_discussions']}",
                f"  进行中:     {summary['open_discussions']}",
                f"  消息总数:   {summary['total_messages']}",
                f"  人工消息:   {summary['total_human_messages']}",
                f"  自动回复:   {summary['total_auto_replies']}",
                f"  自动比例:   {summary['auto_reply_ratio']}",
                f"  告警数:     {summary['alert_count']}",
            ]

            if report.get("alerts"):
                lines.append("")
                lines.append("⚠️  告警详情:")
                for alert in report["alerts"]:
                    lines.append(f"  • {alert}")

            if report.get("per_discussion"):
                lines.append("")
                lines.append("📋  议题列表:")
                lines.append(f"  {'ID':<25s} {'议题':<30s} {'总消息':>6s} {'自动':>4s} {'人工':>4s} {'告警':>4s}")
                lines.append("  " + "-" * 80)
                for d in report["per_discussion"]:
                    lines.append(
                        f"  {d['id'][:22]:<25s} {d['topic']:<30s} "
                        f"{d['messages']:>6d} {d['auto_replies']:>4d} "
                        f"{d['human_messages']:>4d} {d['alerts']:>4d}"
                    )

            click.echo("\n".join(lines))
            return

        if show_status:
            from ..council import council_status
            info = council_status()
            lines = [
                "🏛️  灵家议事厅状态",
                "=" * 30,
                f"  启动时间: {info.get('started_at', '未启动')}",
                f"  最后扫描: {info.get('last_scan', '从未')}",
                f"  累计唤醒: {info.get('total_wakes', 0)} 次",
                f"  讨论总数: {info.get('total_discussions', 0)}",
                f"  进行中:   {info.get('open_discussions', 0)}",
                f"  注册成员: {info.get('members_registered', 0)}",
            ]
            click.echo("\n".join(lines))
            return

        if wake:
            from ..council import wake_member
            member_id, disc_id = wake
            click.echo(f"唤醒 {member_id} 参与讨论 {disc_id}...")
            reply = wake_member(member_id, disc_id)
            if reply:
                click.echo(f"回复: {reply[:200]}...")
            else:
                click.echo("唤醒失败（已发言/讨论已关闭/API不可用）")
            return

        from ..council import start_council_daemon
        click.echo(f"🏛️  启动灵家议事厅守护进程 (间隔 {interval}s)")
        start_council_daemon(interval=interval, once=once)
