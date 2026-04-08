"""Web UI 音频处理 — TTS/STT 函数。"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")


async def _do_tts(text: str) -> str | None:
    from .tts import clean_text_for_speech
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        return None

    result = await _tts_edge(cleaned)
    if result:
        return result
    return await _tts_dashscope(cleaned)


async def _tts_edge(text: str) -> str | None:
    try:
        import tempfile as _tf
        import os as _os
        import edge_tts
        fd, tmp_path = _tf.mkstemp(suffix=".mp3")
        _os.close(fd)
        comm = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
        await comm.save(tmp_path)
        with open(tmp_path, "rb") as f:
            audio = f.read()
        _os.unlink(tmp_path)
        if audio and len(audio) > 100:
            return base64.b64encode(audio).decode("ascii")
        return None
    except Exception as exc:
        logger.error(f"edge-tts failed: {exc}")
        return None


async def _tts_dashscope(text: str) -> str | None:
    try:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        dashscope.api_key = _DASHSCOPE_API_KEY

        synth = SpeechSynthesizer(model="cosyvoice-v2", voice="longxiaocheng_v2")
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, lambda: synth.call(text))

        if audio and len(audio) > 100:
            return base64.b64encode(audio).decode("ascii")
        return None
    except Exception as exc:
        logger.error(f"DashScope TTS failed: {exc}")
        return None


async def _do_stt(audio_b64: str) -> str | None:
    result = await _stt_whisper(audio_b64)
    if result:
        return result
    logger.warning("Whisper STT failed, falling back to DashScope")
    return await _stt_dashscope(audio_b64)


async def _stt_dashscope(audio_b64: str) -> str | None:
    try:
        import dashscope
        from dashscope.audio.asr import Recognition, RecognitionCallback
        dashscope.api_key = _DASHSCOPE_API_KEY

        audio_bytes = base64.b64decode(audio_b64)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(audio_bytes)
        tmp.close()

        texts: list[str] = []
        done_event = asyncio.Event()

        class CB(RecognitionCallback):
            def on_complete(self):
                done_event.set()

            def on_error(self, result):
                logger.error(f"Recognition error: {result}")
                done_event.set()

            def on_event(self, result):
                try:
                    d = json.loads(str(result))
                    t = d.get("output", {}).get("sentence", {}).get("text", "")
                    if t:
                        texts.append(t)
                except Exception:
                    pass

        recognition = Recognition(
            model="paraformer-realtime-v2",
            format="wav",
            sample_rate=16000,
            callback=CB(),
        )

        def _run():
            recognition.start()
            with open(tmp.name, "rb") as f:
                recognition.send_audio_frame(f.read())
            recognition.stop()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run)
        Path(tmp.name).unlink(missing_ok=True)

        return "".join(texts).strip() or None
    except Exception as exc:
        logger.error(f"DashScope STT failed: {exc}")
        return None


async def _stt_whisper(audio_b64: str) -> str | None:
    try:
        import whisper
        if not hasattr(_stt_whisper, '_model'):
            _stt_whisper._model = whisper.load_model("base")
        model = _stt_whisper._model

        audio_bytes = base64.b64decode(audio_b64)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(audio_bytes)
        tmp.close()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: model.transcribe(tmp.name, language="zh")
        )
        Path(tmp.name).unlink(missing_ok=True)
        return result.get("text", "").strip() or None
    except Exception as exc:
        logger.error(f"Whisper STT failed: {exc}")
        return None
