"""灵知/灵克 CLI 命令。"""

import click

from .. import ask as ask_mod
from .. import code as code_mod
from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("ask")
    @click.argument("question", nargs=-1, required=True)
    @click.option("--category", default=None, help="分类筛选（气功/中医/儒家/佛家/道家/武术/哲学/科学/心理学）")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def do_ask(question: tuple, category: str | None, speak_flag: bool):
        """向灵知知识库提问"""
        q = " ".join(question)
        data = ask_mod.ask_knowledge(q, category=category)
        output = ask_mod.format_ask_result(data)
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))

    @group.command("code")
    @click.argument("question", nargs=-1, required=True)
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def do_code(question: tuple, speak_flag: bool):
        """向灵克提问编程问题"""
        q = " ".join(question)
        data = code_mod.ask_code(q)
        output = code_mod.format_code_result(data)
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))
