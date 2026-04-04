"""语音通话 CLI 命令。"""

import click

from .. import voicecall as vc_mod


def register(group: click.Group):
    @group.command("call")
    @click.option("--voice", default="zh-CN-XiaoxiaoNeural", help="TTS语音角色")
    @click.option("--silence", default=1.2, help="静音检测阈值（秒），说完多久后自动识别")
    def do_call(voice: str, silence: float):
        """语音通话：像打电话一样和灵依实时对话"""
        vc_mod.voice_call(voice=voice, silence_limit=silence)

    @group.command("call-status")
    def do_call_status():
        """查看语音通话功能状态"""
        deps = vc_mod.check_voice_call()
        click.echo(vc_mod.format_voice_call_status(deps))
