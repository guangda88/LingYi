"""聊天会话管理：建表、读写消息。"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path.home() / ".lingyi" / "lingyi.db"


def ensure_chat_table(db_path: Path | None = None):
    p = db_path or _DB_PATH
    conn = sqlite3.connect(str(p))
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL DEFAULT 'default',
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, id)")

    conn.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT '新对话',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        message_count INTEGER DEFAULT 0
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)")
    conn.commit()
    conn.close()


def load_recent_chat(session_id: str, limit: int = 40, db_path: Path | None = None) -> list[dict]:
    p = db_path or _DB_PATH
    try:
        conn = sqlite3.connect(str(p))
        rows = conn.execute(
            "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        conn.close()
        return [{"role": r, "content": c, "created_at": t} for r, c, t in reversed(rows)]
    except Exception:
        return []


def save_chat_message(session_id: str | None = None, role: str = "", content: str = "", db_path: Path | None = None):
    if session_id is None:
        session_id = "default"
    p = db_path or _DB_PATH
    try:
        conn = sqlite3.connect(str(p))
        conn.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
        conn.execute(
            "INSERT INTO chat_sessions (session_id, title, message_count, updated_at) "
            "VALUES (?, '新对话', 1, CURRENT_TIMESTAMP) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP",
            (session_id,)
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error(f"Failed to save chat message: {exc}")
