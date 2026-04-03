"""语音识别 CLI 命令。"""

import click

from .. import stt as stt_mod
from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("stt")
    @click.option("--duration", default=5, help="录音时长（秒）")
    @click.option("--file", "audio_file", default=None, help="转录指定音频文件")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音播报识别结果")
    def do_stt(duration: int, audio_file: str | None, speak_flag: bool):
        """语音识别：录音并转文字"""
        if audio_file:
            data = stt_mod.transcribe_file(audio_file)
        else:
            info = stt_mod.check_stt()
            if not info["available"]:
                click.echo(stt_mod.format_stt_status(info))
                return
            click.echo(f"🎤 录音中（{duration}秒）...")
            audio_path = stt_mod.record_audio(duration=duration)
            if audio_path is None:
                click.echo("⚠ 录音失败，请检查麦克风")
                return
            try:
                data = stt_mod.transcribe_file(audio_path)
            finally:
                from pathlib import Path
                try:
                    Path(audio_path).unlink(missing_ok=True)
                except Exception:
                    pass

        output = stt_mod.format_transcribe_result(data)
        click.echo(output)
        if speak_flag:
            speak(clean_text_for_speech(output))

    @group.command("stt-status")
    def do_stt_status():
        """查看语音识别后端状态"""
        info = stt_mod.check_stt()
        click.echo(stt_mod.format_stt_status(info))
