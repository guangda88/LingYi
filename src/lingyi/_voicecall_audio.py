"""语音通话音频层 — VAD录音、STT转写、TTS合成播放。"""

import importlib.util
import logging
import subprocess
import tempfile
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

_SILENCE_LIMIT = 1.2
_MAX_RECORD_SEC = 30
_SAMPLE_RATE = 16000
_CHANNELS = 1
_FRAME_DURATION = 30
_VAD_AGGRESSIVENESS = 3


def _check_dependencies() -> dict:
    deps = {"vad": False, "stt": False, "tts": False, "record": False}

    if importlib.util.find_spec("webrtcvad") is not None:
        deps["vad"] = True
    if importlib.util.find_spec("whisper") is not None:
        deps["stt"] = True
    if importlib.util.find_spec("edge_tts") is not None:
        deps["tts"] = True

    try:
        subprocess.run(["arecord", "--version"], capture_output=True, timeout=3)
        deps["record"] = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return deps


def _record_with_vad(silence_limit: float = _SILENCE_LIMIT,
                     max_duration: float = _MAX_RECORD_SEC) -> str | None:
    """使用 VAD 录音：检测到说话开始，说完自动停止。

    Returns:
        WAV 文件路径，失败返回 None
    """
    import webrtcvad

    vad = webrtcvad.Vad(_VAD_AGGRESSIVENESS)
    frame_size = int(_SAMPLE_RATE * _FRAME_DURATION / 1000)

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    import os
    os.close(fd)

    try:
        proc = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", str(_SAMPLE_RATE),
             "-c", str(_CHANNELS), "-t", "raw", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return None

    frames: list[bytes] = []
    has_speech = False
    silence_start = None
    total_frames = 0
    max_frames = int(_SAMPLE_RATE / frame_size * max_duration)

    try:
        while total_frames < max_frames:
            raw = proc.stdout.read(frame_size * 2)
            if not raw or len(raw) < frame_size * 2:
                break

            total_frames += 1
            is_speech = vad.is_speech(raw, _SAMPLE_RATE)

            if is_speech:
                frames.append(raw)
                has_speech = True
                silence_start = None
            elif has_speech:
                frames.append(raw)
                if silence_start is None:
                    silence_start = total_frames
                elif (total_frames - silence_start) * _FRAME_DURATION / 1000 >= silence_limit:
                    break
            if not has_speech and total_frames * _FRAME_DURATION / 1000 > 5:
                break
    except Exception as e:
        logger.debug(f"VAD录音异常: {e}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not has_speech or not frames:
        Path(wav_path).unlink(missing_ok=True)
        return None

    try:
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return wav_path
    except Exception as e:
        logger.debug(f"写WAV失败: {e}")
        Path(wav_path).unlink(missing_ok=True)
        return None


def _transcribe(audio_path: str) -> str:
    """使用 whisper 转录。"""
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="zh")
    return result.get("text", "").strip()


def _synthesize_and_play(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bool:
    """TTS 合成并播放。"""
    from .tts import speak, clean_text_for_speech
    return speak(clean_text_for_speech(text), voice=voice)
