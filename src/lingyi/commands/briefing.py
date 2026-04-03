"""情报汇报 CLI 命令。"""

import click

from .. import briefing as briefing_mod
from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("briefing")
    @click.option("--short", "short_mode", is_flag=True, help="简短模式（一行摘要）")
    @click.option("--source", "source", default=None,
              help="指定来源（lingzhi/lingflow/lingclaude）")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def do_briefing(short_mode: bool, source: str | None, speak_flag: bool):
        """汇总灵通/灵知/灵克情报，汇报"""
        if source == "lingzhi":
            data = {"timestamp": "", "lingzhi": briefing_mod.collect_lingzhi(),
                    "lingflow": {"available": False}, "lingclaude": {"available": False}}
        elif source == "lingflow":
            data = {"timestamp": "", "lingflow": briefing_mod.collect_lingflow(),
                    "lingzhi": {"available": False}, "lingclaude": {"available": False}}
        elif source == "lingclaude":
            data = {"timestamp": "", "lingclaude": briefing_mod.collect_lingclaude(),
                    "lingzhi": {"available": False}, "lingflow": {"available": False}}
        else:
            data = briefing_mod.collect_all()

        if short_mode:
            output = briefing_mod.format_briefing_short(data)
        else:
            output = briefing_mod.format_briefing(data)

        click.echo(output)

        if speak_flag:
            speak(clean_text_for_speech(output))
