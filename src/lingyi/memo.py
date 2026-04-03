"""备忘录增删查。"""

from .db import get_db
from .models import Memo


def add_memo(content: str) -> Memo:
    conn = get_db()
    cur = conn.execute("INSERT INTO memos (content) VALUES (?)", (content,))
    row = conn.execute("SELECT * FROM memos WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return Memo(**dict(row))


def list_memos() -> list[Memo]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM memos ORDER BY id DESC").fetchall()
    conn.close()
    return [Memo(**dict(r)) for r in rows]


def show_memo(memo_id: int) -> Memo | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    conn.close()
    return Memo(**dict(row)) if row else None


def delete_memo(memo_id: int) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0
