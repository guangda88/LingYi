"""备忘录 CLI 命令。"""

import click

from .. import memo as memo_mod
from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("add")
    @click.argument("content")
    def memo_add(content: str):
        """添加备忘"""
        m = memo_mod.add_memo(content)
        click.echo(f"✓ 备忘 #{m.id} 已添加")

    @group.command("list")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音朗读")
    def memo_list(speak_flag: bool):
        """查看所有备忘"""
        memos = memo_mod.list_memos()
        if not memos:
            click.echo("暂无备忘。")
            return
        lines = []
        for m in memos:
            line = f"  [{m.id}] {m.content}  ({m.created_at})"
            click.echo(line)
            lines.append(f"备忘{m.id}，{m.content}")
        if speak_flag:
            speak(clean_text_for_speech("。".join(lines)))

    @group.command("show")
    @click.argument("memo_id", type=int)
    @click.option("--speak", "speak_flag", is_flag=True, help="语音朗读")
    def memo_show(memo_id: int, speak_flag: bool):
        """查看单条备忘"""
        m = memo_mod.show_memo(memo_id)
        if not m:
            click.echo(f"备忘 #{memo_id} 不存在。")
            return
        click.echo(f"  #{m.id}")
        click.echo(f"  内容：{m.content}")
        click.echo(f"  创建：{m.created_at}")
        click.echo(f"  更新：{m.updated_at}")
        if speak_flag:
            speak(clean_text_for_speech(f"备忘{m.id}，{m.content}"))

    @group.command("delete")
    @click.argument("memo_id", type=int)
    def memo_delete(memo_id: int):
        """删除备忘"""
        if memo_mod.delete_memo(memo_id):
            click.echo(f"✓ 备忘 #{memo_id} 已删除")
        else:
            click.echo(f"备忘 #{memo_id} 不存在。")
