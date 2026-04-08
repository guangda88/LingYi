"""Web 认证：会话管理、密码哈希、Token持久化。"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import string
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS: dict[str, datetime] = {}
PERSISTENT_TOKEN_PATH = Path.home() / ".lingyi" / ".web_tokens"
MAX_SESSIONS = 200

LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
LOGIN_MAX_ATTEMPTS = 10
LOGIN_WINDOW_SEC = 300


def cleanup_sessions():
    now = datetime.now()
    expired = [t for t, exp in SESSIONS.items() if exp < now]
    for t in expired:
        del SESSIONS[t]
    if len(SESSIONS) > MAX_SESSIONS:
        by_age = sorted(SESSIONS.items(), key=lambda x: x[1])
        for t, _ in by_age[: len(SESSIONS) - MAX_SESSIONS]:
            del SESSIONS[t]


def check_login_rate(ip: str) -> bool:
    now = time.time()
    attempts = LOGIN_ATTEMPTS[ip]
    LOGIN_ATTEMPTS[ip] = [t for t in attempts if now - t < LOGIN_WINDOW_SEC]
    if len(LOGIN_ATTEMPTS[ip]) >= LOGIN_MAX_ATTEMPTS:
        return False
    return True


def record_login_attempt(ip: str):
    LOGIN_ATTEMPTS[ip].append(time.time())


def load_persistent_tokens() -> dict[str, str]:
    try:
        if PERSISTENT_TOKEN_PATH.exists():
            data = json.loads(PERSISTENT_TOKEN_PATH.read_text("utf-8"))
            now = datetime.now().isoformat()
            return {k: v for k, v in data.items() if v > now}
    except Exception:
        pass
    return {}


def save_persistent_tokens(tokens: dict[str, str]):
    try:
        PERSISTENT_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        PERSISTENT_TOKEN_PATH.write_text(json.dumps(tokens, ensure_ascii=False, indent=2), "utf-8")
    except Exception as exc:
        logger.error(f"Failed to save persistent tokens: {exc}")


def add_persistent_token(token: str, expires: datetime):
    tokens = load_persistent_tokens()
    tokens[token] = expires.isoformat()
    save_persistent_tokens(tokens)


def remove_persistent_token(token: str):
    tokens = load_persistent_tokens()
    tokens.pop(token, None)
    save_persistent_tokens(tokens)


def check_auth(token: str) -> bool:
    if not token:
        return False
    exp = SESSIONS.get(token)
    if exp:
        if datetime.now() > exp:
            del SESSIONS[token]
            return False
        return True
    persistent = load_persistent_tokens()
    exp_str = persistent.get(token)
    if exp_str:
        if datetime.now() < datetime.fromisoformat(exp_str):
            return True
        else:
            remove_persistent_token(token)
    return False


def get_web_password() -> str:
    try:
        import json as _json
        presets_path = Path.home() / ".lingyi" / "presets.json"
        if presets_path.exists():
            data = _json.loads(presets_path.read_text("utf-8"))
            if data.get("web_password"):
                return str(data["web_password"])
    except Exception:
        pass
    return ""


def generate_and_save_password() -> str:
    chars = string.ascii_lowercase + string.digits
    pwd = "".join(secrets.choice(chars) for _ in range(8))
    try:
        presets_path = Path.home() / ".lingyi" / "presets.json"
        data = {}
        if presets_path.exists():
            data = json.loads(presets_path.read_text("utf-8"))
        data["web_password"] = pwd
        presets_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as exc:
        logger.error(f"Failed to save web_password: {exc}")
    return pwd


def hash_password(pwd: str) -> str:
    try:
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(pwd.encode('utf-8'), salt).decode('utf-8')
    except ImportError:
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt, 100000)
        return f"pbkdf2:{salt.hex()}:{key.hex()}"


def check_password(pwd: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('utf-8'))
    except ImportError:
        if hashed.startswith("pbkdf2:"):
            parts = hashed.split(":")
            salt = bytes.fromhex(parts[1])
            key = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt, 100000)
            return key.hex() == parts[2]
        return hashlib.sha256(pwd.encode()).hexdigest() == hashed
