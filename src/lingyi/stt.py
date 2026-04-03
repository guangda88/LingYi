"""语音识别 — 本地 STT 支持多后端（whisper / sherpa-onnx）。"""

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def check_stt() -> dict:
    """检查可用的 STT 后端。"""
    backends = []

    try:
        import whisper
        backends.append({"name": "whisper", "version": getattr(whisper, "__version__", "unknown")})
    except ImportError:
        pass

    try:
        import sherpa_onnx
        backends.append({"name": "sherpa_onnx", "version": getattr(sherpa_onnx, "__version__", "unknown")})
    except (ImportError, AttributeError):
        try:
            import sherpa_onnx
            backends.append({"name": "sherpa_onnx", "version": "unknown"})
        except ImportError:
            pass

    return {
        "available": len(backends) > 0,
        "backends": backends,
        "default": backends[0]["name"] if backends else None,
    }


def record_audio(duration: int = 5, output_path: str | None = None) -> str | None:
    """使用 arecord 录音。

    Args:
        duration: 录音时长（秒）
        output_path: 输出文件路径，None 则使用临时文件

    Returns:
        音频文件路径，失败返回 None
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav")
        import os
        os.close(fd)

    try:
        result = subprocess.run(
            ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1",
             "-d", str(duration), output_path],
            capture_output=True, text=True, timeout=duration + 5,
        )
        if result.returncode == 0 and Path(output_path).exists():
            return output_path
        logger.debug(f"arecord failed: {result.stderr}")
        return None
    except FileNotFoundError:
        logger.debug("arecord not found")
        return None
    except subprocess.TimeoutExpired:
        logger.debug("arecord timeout")
        return None


def transcribe_file(audio_path: str, backend: str | None = None) -> dict:
    """转录音频文件。

    Args:
        audio_path: 音频文件路径
        backend: 指定后端（whisper/sherpa_onnx），None 则自动选择

    Returns:
        {"text": str, "available": bool, "backend": str}
    """
    if not Path(audio_path).exists():
        return {"text": "", "available": False, "backend": None, "error": "文件不存在"}

    if backend is None:
        stt_info = check_stt()
        if not stt_info["available"]:
            return {"text": "", "available": False, "backend": None,
                    "error": "无可用的 STT 后端（需安装 whisper 或 sherpa-onnx）"}
        backend = stt_info["default"]

    if backend == "whisper":
        return _transcribe_whisper(audio_path)
    elif backend == "sherpa_onnx":
        return _transcribe_sherpa(audio_path)

    return {"text": "", "available": False, "backend": backend, "error": f"未知后端: {backend}"}


def _transcribe_whisper(audio_path: str) -> dict:
    """使用 whisper 转录。"""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language="zh")
        text = result.get("text", "").strip()
        return {"text": text, "available": True, "backend": "whisper"}
    except ImportError:
        return {"text": "", "available": False, "backend": "whisper",
                "error": "whisper 未安装"}
    except Exception as e:
        logger.debug(f"whisper transcribe failed: {e}")
        return {"text": "", "available": False, "backend": "whisper", "error": str(e)}


def _transcribe_sherpa(audio_path: str) -> dict:
    """使用 sherpa-onnx 转录。"""
    try:
        import sherpa_onnx
        return {"text": "", "available": False, "backend": "sherpa_onnx",
                "error": "sherpa-onnx 支持待实现"}
    except ImportError:
        return {"text": "", "available": False, "backend": "sherpa_onnx",
                "error": "sherpa_onnx 未安装"}


def format_stt_status(info: dict) -> str:
    """格式化 STT 状态信息。"""
    if not info["available"]:
        return "⚠ 语音识别不可用\n  需安装: pip install openai-whisper 或 sherpa-onnx"

    lines = ["🎤 语音识别可用"]
    for b in info["backends"]:
        lines.append(f"  - {b['name']} ({b['version']})")
    if info["default"]:
        lines.append(f"  默认后端: {info['default']}")
    return "\n".join(lines)


def format_transcribe_result(data: dict) -> str:
    """格式化转录结果。"""
    if not data.get("available"):
        error = data.get("error", "未知错误")
        return f"⚠ 转录失败: {error}"

    text = data.get("text", "")
    backend = data.get("backend", "")
    if text:
        return f"🎤 [{backend}] {text}"
    return f"🎤 [{backend}] （未识别到语音）"
