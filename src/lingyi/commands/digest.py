"""信息整理 CLI 命令。"""

import sys

import click

from .. import digest as digest_mod
from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("digest")
    @click.option("--file", "file_path", default=None, help="从文件读取文本")
    @click.option("--save", "save_flag", is_flag=True, help="自动保存到备忘录/偏好")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报")
    @click.argument("text", nargs=-1)
    def do_digest(file_path: str | None, save_flag: bool, speak_flag: bool, text: tuple):
        """整理文本，提取待办/决策/偏好/要点"""
        if file_path:
            try:
                content = open(file_path, encoding="utf-8").read()
            except FileNotFoundError:
                click.echo(f"文件不存在: {file_path}")
                return
        elif text:
            content = " ".join(text)
        elif not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            click.echo("请提供文本：lingyi digest 文本内容，或 --file 文件路径，或管道输入")
            return

        data = digest_mod.digest_text(content)
        output = digest_mod.format_digest(data)
        click.echo(output)

        if save_flag:
            result = digest_mod.save_digest(data)
            if result["memos_saved"] or result["prefs_saved"]:
                click.echo(f"\n💾 已保存 {result['memos_saved']} 条备忘、{result['prefs_saved']} 条偏好")

        if speak_flag:
            speak(clean_text_for_speech(output))
