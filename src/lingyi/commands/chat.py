"""交互式对话模式。"""

import sys

import click

from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("chat")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音朗读回复")
    @click.option("--voice", default="zh-CN-YunxiNeural", help="TTS语音")
    def lingyi_chat(speak_flag: bool, voice: str):
        """交互式对话模式"""
        click.echo("灵依对话模式（输入 q 退出）")
        click.echo("─" * 30)
        while True:
            try:
                user_input = input("你：").strip()
            except (EOFError, KeyboardInterrupt):
                click.echo("\n再见！")
                break
            if user_input.lower() in ("q", "quit", "exit", "退出"):
                click.echo("再见！")
                break
            if not user_input:
                continue
            reply = _process_input(user_input)
            click.echo(f"灵依：{reply}")
            if speak_flag:
                speak(clean_text_for_speech(reply), voice=voice)


def _process_input(text: str) -> str:
    text_lower = text.lower()
    if any(kw in text_lower for kw in ("今天", "日程", "安排")):
        from ..schedule import format_today
        return format_today()
    if any(kw in text_lower for kw in ("备忘", "记一下", "提醒我")):
        content = text
        for kw in ("备忘", "记一下", "提醒我", "帮我"):
            content = content.replace(kw, "")
        content = content.strip()
        if content:
            from ..memo import add_memo
            m = add_memo(content)
            return f"已记录：{content}（备忘 #{m.id}）"
        return "请告诉我你要记什么。"
    if any(kw in text_lower for kw in ("帮助", "help", "你能")):
        return "我可以帮你查看日程、记录备忘、管理项目和计划。试试说'今天有什么安排'或'备忘买牛奶'。"
    return f"收到：{text}。（更多智能回复将在v0.7实现）"
