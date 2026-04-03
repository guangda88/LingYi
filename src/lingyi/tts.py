"""语音播报引擎（edge-tts）。"""

import asyncio
import subprocess
import tempfile
from pathlib import Path

DEFAULT_VOICE = "zh-CN-YunxiNeural"


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
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name],
            check=True,
        )
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
