"""移动端适配 — ZeroTermux / Termux 环境支持。"""

import os
import shutil
import subprocess


def detect_environment() -> dict:
    """检测当前运行环境。"""
    env_type = "desktop"
    if os.path.exists("/data/data/com.termux"):
        env_type = "termux"
    elif "TERMUX_VERSION" in os.environ:
        env_type = "termux"
    elif "ANDROID_ROOT" in os.environ:
        env_type = "android"

    term_width = 80
    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        pass

    is_compact = term_width < 60

    audio_player = _detect_audio_player()

    return {
        "type": env_type,
        "is_termux": env_type == "termux",
        "is_compact": is_compact,
        "term_width": term_width,
        "audio_player": audio_player,
    }


def _detect_audio_player() -> str | None:
    """检测可用的音频播放器。"""
    players = ["ffplay", "termux-media-player", "play-audio", "mpv", "aplay", "paplay"]
    for player in players:
        if shutil.which(player):
            return player
    return None


def play_audio(file_path: str, player: str | None = None) -> bool:
    """使用检测到的播放器播放音频文件。"""
    if player is None:
        env = detect_environment()
        player = env["audio_player"]
        if player is None:
            return False

    try:
        if player == "termux-media-player":
            subprocess.run(["termux-media-player", "play", file_path],
                           check=True, capture_output=True, timeout=30)
            return True
        elif player == "ffplay":
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path],
                           check=True, capture_output=True, timeout=30)
            return True
        elif player == "mpv":
            subprocess.run(["mpv", "--no-video", "--really-quiet", file_path],
                           check=True, capture_output=True, timeout=30)
            return True
        elif player == "play-audio":
            subprocess.run(["play-audio", file_path],
                           check=True, capture_output=True, timeout=30)
            return True
        elif player in ("aplay", "paplay"):
            subprocess.run([player, file_path],
                           check=True, capture_output=True, timeout=30)
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False
    return False


def compact_output(text: str, width: int = 50) -> str:
    """紧凑输出：截断过长的行，适配小屏幕。"""
    if width <= 0:
        return text
    lines = []
    for line in text.splitlines():
        if len(line) <= width:
            lines.append(line)
        else:
            lines.append(line[:width - 1] + "…")
    return "\n".join(lines)


def format_env_info(env: dict) -> str:
    """格式化环境信息。"""
    lines = ["📱 环境信息"]
    lines.append(f"  类型: {env['type']}")
    lines.append(f"  终端宽度: {env['term_width']}{' (紧凑)' if env['is_compact'] else ''}")
    lines.append(f"  音频播放: {env['audio_player'] or '未检测到'}")
    if env["is_termux"]:
        lines.append("  Termux 优化: 已启用")
    return "\n".join(lines)
