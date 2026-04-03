"""会话摘要管理。"""

from .db import get_db
from .models import Session


def save_session(summary: str = "", files: str = "", decisions: str = "",
                 todos: str = "", prefs_noted: str = "") -> Session:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sessions (summary, files, decisions, todos, prefs_noted) VALUES (?, ?, ?, ?, ?)",
        (summary, files, decisions, todos, prefs_noted),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row_to_session(row)


def last_session() -> Session | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return _row_to_session(row) if row else None


def get_session(session_id: int) -> Session | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return _row_to_session(row) if row else None


def list_sessions(limit: int = 10) -> list[Session]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [_row_to_session(r) for r in rows]


def delete_session(session_id: int) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def format_session_short(s: Session) -> str:
    return f"  [{s.id}] {s.created_at}  {s.summary[:60]}"


def format_session_detail(s: Session) -> str:
    lines = [f"## 会话 #{s.id}  {s.created_at}"]
    if s.summary:
        lines.append(f"- 摘要：{s.summary}")
    if s.files:
        lines.append(f"- 修改文件：{s.files}")
    if s.decisions:
        lines.append(f"- 关键决策：{s.decisions}")
    if s.todos:
        lines.append(f"- 待办：{s.todos}")
    if s.prefs_noted:
        lines.append(f"- 用户偏好：{s.prefs_noted}")
    return "\n".join(lines)


def format_session_resume(s: Session) -> str:
    lines = ["# 上次会话摘要", ""]
    if s.summary:
        lines.append(f"## 完成了\n{s.summary}")
    if s.files:
        lines.append(f"\n## 修改文件\n{s.files}")
    if s.decisions:
        lines.append(f"\n## 关键决策\n{s.decisions}")
    if s.todos:
        lines.append(f"\n## 待办\n{s.todos}")
    if s.prefs_noted:
        lines.append(f"\n## 用户偏好\n{s.prefs_noted}")
    return "\n".join(lines)


def _row_to_session(row) -> Session:
    return Session(**dict(row))
