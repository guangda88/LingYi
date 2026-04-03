"""日程管理：排班、增删查、今日/本周视图、上诊提醒。"""

from datetime import date, timedelta

from .db import get_db
from .models import Schedule

_DAY_CN = {
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
    "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日",
}

_SLOT_CN = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}

_DEFAULT_CLINIC = [
    ("Monday", "afternoon"),
    ("Tuesday", "morning"),
    ("Wednesday", "afternoon"),
    ("Thursday", "morning"),
    ("Friday", "afternoon"),
    ("Saturday", "morning"),
]


def init_clinic() -> list[Schedule]:
    conn = get_db()
    existing = conn.execute("SELECT id FROM schedules WHERE type = 'clinic'").fetchone()
    if existing:
        conn.close()
        return list_schedules(schedule_type="clinic")
    for day, slot in _DEFAULT_CLINIC:
        conn.execute(
            "INSERT INTO schedules (type, day, time_slot, description) VALUES (?, ?, ?, ?)",
            ("clinic", day, slot, "门诊"),
        )
    conn.commit()
    result = list_schedules(schedule_type="clinic")
    conn.close()
    return result


def add_schedule(schedule_type: str, day: str, time_slot: str, description: str = "") -> Schedule:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO schedules (type, day, time_slot, description) VALUES (?, ?, ?, ?)",
        (schedule_type, day, time_slot, description),
    )
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return Schedule(**dict(row))


def list_schedules(schedule_type: str | None = None, active_only: bool = True) -> list[Schedule]:
    conn = get_db()
    sql = "SELECT * FROM schedules"
    conditions: list[str] = []
    params: list = []
    if schedule_type:
        conditions.append("type = ?")
        params.append(schedule_type)
    if active_only:
        conditions.append("is_active = 1")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY CASE day"
    for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
        sql += f" WHEN '{d}' THEN {i}"
    sql += " ELSE 7 END, CASE time_slot"
    for i, s in enumerate(["morning", "afternoon", "evening"]):
        sql += f" WHEN '{s}' THEN {i}"
    sql += " ELSE 3 END"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [Schedule(**dict(r)) for r in rows]


def show_schedule(schedule_id: int) -> Schedule | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    conn.close()
    return Schedule(**dict(row)) if row else None


def update_schedule(schedule_id: int, **kwargs) -> Schedule | None:
    if not kwargs:
        return show_schedule(schedule_id)
    conn = get_db()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [schedule_id]
    conn.execute(f"UPDATE schedules SET {sets} WHERE id = ?", vals)
    conn.commit()
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    conn.close()
    return Schedule(**dict(row)) if row else None


def cancel_schedule(schedule_id: int) -> bool:
    conn = get_db()
    cur = conn.execute("UPDATE schedules SET is_active = 0 WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def today_schedules() -> list[Schedule]:
    day_name = date.today().strftime("%A")
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM schedules WHERE day = ? AND is_active = 1 ORDER BY CASE time_slot"
        " WHEN 'morning' THEN 0 WHEN 'afternoon' THEN 1 WHEN 'evening' THEN 2 ELSE 3 END",
        (day_name,),
    ).fetchall()
    conn.close()
    return [Schedule(**dict(r)) for r in rows]


def week_schedules() -> dict[str, list[Schedule]]:
    result: dict[str, list[Schedule]] = {}
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    for i in range(7):
        d = monday + timedelta(days=i)
        day_name = d.strftime("%A")
        result[day_name] = today_schedules_for(day_name)
    return result


def today_schedules_for(day_name: str) -> list[Schedule]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM schedules WHERE day = ? AND is_active = 1 ORDER BY CASE time_slot"
        " WHEN 'morning' THEN 0 WHEN 'afternoon' THEN 1 WHEN 'evening' THEN 2 ELSE 3 END",
        (day_name,),
    ).fetchall()
    conn.close()
    return [Schedule(**dict(r)) for r in rows]


def check_remind() -> list[Schedule]:
    items = today_schedules()
    return [s for s in items if s.type == "clinic"]


def format_schedule(s: Schedule) -> str:
    day_cn = _DAY_CN.get(s.day, s.day)
    slot_cn = _SLOT_CN.get(s.time_slot, s.time_slot)
    desc = f" {s.description}" if s.description else ""
    return f"[{s.id}] {day_cn} {slot_cn} · {s.type}{desc}"


def format_today() -> str:
    items = today_schedules()
    if not items:
        today_cn = _DAY_CN.get(date.today().strftime("%A"), "")
        return f"今天{today_cn}没有安排。"
    today_cn = _DAY_CN.get(date.today().strftime("%A"), "")
    lines = [f"📋 今天{today_cn}（{date.today().strftime('%m-%d')}）："]
    for s in items:
        slot_cn = _SLOT_CN.get(s.time_slot, s.time_slot)
        desc = f" {s.description}" if s.description else ""
        lines.append(f"  {slot_cn}  {s.type}{desc}")
    return "\n".join(lines)


def format_week() -> str:
    data = week_schedules()
    lines = []
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    for i in range(7):
        d = monday + timedelta(days=i)
        day_name = d.strftime("%A")
        day_cn = _DAY_CN.get(day_name, day_name)
        marker = " ←今天" if d == today else ""
        items = data.get(day_name, [])
        if items:
            slots = ", ".join(
                f"{_SLOT_CN.get(s.time_slot, s.time_slot)} {s.type}"
                for s in items
            )
            lines.append(f"  {day_cn}（{d.strftime('%m-%d')}）{marker}: {slots}")
        else:
            lines.append(f"  {day_cn}（{d.strftime('%m-%d')}）{marker}: —")
    return "\n".join(lines)
