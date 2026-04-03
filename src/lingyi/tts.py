"""语音播报引擎（edge-tts）。"""

import asyncio
import subprocess
import tempfile
from pathlib import Path

DEFAULT_VOICE = "zh-CN-YunxiNeural"


def _get_audio_player() -> list[str] | None:
    """获取可用的音频播放命令。"""
    from .mobile import detect_environment
    env = detect_environment()
    player = env["audio_player"]
    if player is None:
        return None
    if player == "ffplay":
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    if player == "mpv":
        return ["mpv", "--no-video", "--really-quiet"]
    if player == "termux-media-player":
        return ["termux-media-player", "play"]
    if player == "play-audio":
        return ["play-audio"]
    if player in ("aplay", "paplay"):
        return [player]
    return [player]


async def _synthesize(text: str, voice: str = DEFAULT_VOICE, output_path: str = "") -> str:
    if not text.strip():
        return ""
    out = output_path or str(Path(tempfile.mkdtemp()) / "tts.mp3")
    communicate = __import__("edge_tts").Communicate(text, voice)
    await communicate.save(out)
    return out


def speak(text: str, voice: str = DEFAULT_VOICE) -> bool:
    if not text.strip():
        return False
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        asyncio.run(_synthesize(text, voice, tmp.name))
        cmd = _get_audio_player()
        if cmd is None:
            return False
        subprocess.run(cmd + [tmp.name], check=True, capture_output=True, timeout=30)
        return True
    except Exception:
        return False
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def synthesize_to_file(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> str:
    asyncio.run(_synthesize(text, voice, output_path))
    return output_path


def clean_text_for_speech(raw: str) -> str:
    import re
    text = raw
    text = re.sub(r"✓", "完成", text)
    text = re.sub(r"[#*\-]{2,}", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
