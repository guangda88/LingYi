"""用户偏好持久化。"""

from .db import get_db


def set_pref(key: str, value: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?, updated_at=CURRENT_TIMESTAMP",
        (key, value, value),
    )
    conn.commit()
    conn.close()


def get_pref(key: str) -> str | None:
    conn = get_db()
    row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def list_prefs() -> list[tuple[str, str]]:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM preferences ORDER BY key").fetchall()
    conn.close()
    return [(r["key"], r["value"]) for r in rows]


def delete_pref(key: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM preferences WHERE key = ?", (key,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def format_pref_list(prefs: list[tuple[str, str]]) -> str:
    if not prefs:
        return "暂无偏好设置。"
    return "\n".join(f"  {k} = {v}" for k, v in prefs)
