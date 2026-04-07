"""情报汇报 CLI 命令。"""

import click

from .. import briefing as briefing_mod
from .. import briefing_daemon as daemon_mod
from ..tts import speak, clean_text_for_speech
from ..trends import TrendAnalyzer


def register(group: click.Group):
    @group.command("briefing")
    @click.option("--short", "short_mode", is_flag=True, help="简短模式（一行摘要）")
    @click.option("--source", "source", default=None,
              help="指定来源（lingzhi/lingflow/lingclaude/lingtongask）")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    @click.option("--trend", "trend_period", default=None,
              type=click.Choice(["week", "month", "w", "m"]),
              help="显示趋势分析（周/月对比）")
    @click.option("--anomaly", "check_anomaly", is_flag=True, help="检测异常数据")
    def do_briefing(short_mode: bool, source: str | None, speak_flag: bool,
                   trend_period: str | None, check_anomaly: bool):
        """汇总灵通/灵知/灵克/灵通问道情报，汇报"""
        # 收集情报
        if source == "lingzhi":
            data = {"timestamp": "", "lingzhi": briefing_mod.collect_lingzhi(),
                    "lingflow": {"available": False}, "lingclaude": {"available": False},
                    "lingtongask": {"available": False}}
        elif source == "lingflow":
            data = {"timestamp": "", "lingflow": briefing_mod.collect_lingflow(),
                    "lingzhi": {"available": False}, "lingclaude": {"available": False},
                    "lingtongask": {"available": False}}
        elif source == "lingclaude":
            data = {"timestamp": "", "lingclaude": briefing_mod.collect_lingclaude(),
                    "lingzhi": {"available": False}, "lingflow": {"available": False},
                    "lingtongask": {"available": False}}
        elif source == "lingtongask":
            data = {"timestamp": "", "lingtongask": briefing_mod.collect_lingtongask(),
                    "lingzhi": {"available": False}, "lingflow": {"available": False},
                    "lingclaude": {"available": False}}
        else:
            data = briefing_mod.collect_all()

        # 输出情报
        if short_mode:
            output = briefing_mod.format_briefing_short(data)
        else:
            output = briefing_mod.format_briefing(data)

        click.echo(output)

        # 趋势分析
        if trend_period:
            analyzer = TrendAnalyzer()
            click.echo()  # 空行

            if trend_period in ("week", "w"):
                report = analyzer.analyze_weekly()
            else:
                report = analyzer.analyze_monthly()

            click.echo(report.format_terminal())

        # 异常检测
        if check_anomaly:
            analyzer = TrendAnalyzer()
            anomalies = analyzer.detect_anomalies()

            if anomalies:
                click.echo("\n⚠️  检测到异常数据:")
                for a in anomalies:
                    click.echo(f"  • {a['metric']}: {a['value']:.0f} "
                             f"(预期: {a['expected']}, 偏差: {a['deviation']:.1f}σ)")
            else:
                click.echo("\n✅ 未检测到异常数据")

        if speak_flag:
            speak(clean_text_for_speech(output))


def register_daemon(group: click.Group):
    """注册daemon子命令。"""
    @group.group()
    def daemon():
        """定时情报汇报守护进程"""
        pass

    @daemon.command("start")
    def daemon_start():
        """启动守护进程"""
        success = daemon_mod.start_daemon()
        if not success:
            click.echo("启动失败，请检查日志")
            raise click.ClickException("启动失败")

    @daemon.command("stop")
    def daemon_stop():
        """停止守护进程"""
        daemon_mod.stop_daemon()

    @daemon.command("status")
    def daemon_status():
        """查看守护进程状态"""
        daemon_mod.get_status()

    @daemon.command("list")
    @click.option("--limit", "limit", default=5, help="显示数量")
    def daemon_list(limit: int):
        """列出最近的简报"""
        daemon_mod.list_briefings(limit)

    @daemon.command("show")
    @click.argument("date", default=None, required=False)
    def daemon_show(date: str | None):
        """显示指定日期的简报（默认今天）"""
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
        daemon_mod.show_briefing(date)

    @daemon.command("run")
    def daemon_run():
        """立即生成一次简报"""
        daemon_mod.run_once()

