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

    @group.command("review")
    @click.argument("file_path")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def do_review(file_path: str, speak_flag: bool):
        """代码审查：让灵克审查指定文件"""
        data = code_mod.review_code(file_path)
        output = code_mod.format_code_result(data)
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))

    @group.command("deps")
    @click.argument("project_path")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def do_deps(project_path: str, speak_flag: bool):
        """依赖检查：分析项目依赖配置"""
        data = code_mod.check_dependencies(project_path)
        output = code_mod.format_code_result(data)
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))

    @group.command("refactor")
    @click.argument("file_path")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    def do_refactor(file_path: str, speak_flag: bool):
        """重构建议：分析代码并给出重构建议"""
        data = code_mod.suggest_refactor(file_path)
        output = code_mod.format_code_result(data)
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))
