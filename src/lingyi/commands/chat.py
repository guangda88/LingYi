"""交互式对话模式。"""

import click

from ..tts import speak, clean_text_for_speech


def register(group: click.Group):
    @group.command("chat")
    @click.option("--speak", "speak_flag", is_flag=True, help="语音朗读回复")
    @click.option("--voice", "voice_mode", is_flag=True, help="语音对话模式（STT输入+TTS输出）")
    @click.option("--voice-sec", default=5, help="语音录音时长（秒，默认5）")
    @click.option("--tts-voice", default="zh-CN-XiaoxiaoNeural", help="TTS语音角色")
    def lingyi_chat(speak_flag: bool, voice_mode: bool, voice_sec: int, tts_voice: str):
        """交互式对话模式"""
        stt_info = None
        if voice_mode:
            from ..stt import check_stt
            stt_info = check_stt()
            if not stt_info["available"]:
                click.echo("⚠ 语音输入不可用，需安装 whisper 或 sherpa-onnx")
                click.echo("  回退到文字输入模式")
                voice_mode = False
            else:
                click.echo(f"🎤 语音对话模式（后端: {stt_info['default']}，录音{voice_sec}秒）")

        mode_label = "语音" if voice_mode else "文字"
        click.echo(f"灵依对话模式 [{mode_label}]（输入 q 退出）")
        click.echo("─" * 30)

        while True:
            try:
                if voice_mode:
                    click.echo("🎤 录音中...")
                    user_input = _voice_input(voice_sec, stt_info)
                    if user_input is None:
                        click.echo("⚠ 录音失败，请重试或输入 q 退出")
                        continue
                    click.echo(f"你：{user_input}")
                else:
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

            if speak_flag or voice_mode:
                speak(clean_text_for_speech(reply), voice=tts_voice)


def _voice_input(duration: int, stt_info: dict) -> str | None:
    """录音并转录。返回识别文本，失败返回 None。"""
    from ..stt import record_audio, transcribe_file
    audio_path = record_audio(duration=duration)
    if audio_path is None:
        return None
    try:
        result = transcribe_file(audio_path, backend=stt_info["default"])
        return result.get("text", "").strip() or None
    finally:
        from pathlib import Path
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass


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
