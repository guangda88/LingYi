"""日程管理：排班、增删查、今日/本周视图、上诊提醒。"""

from datetime import date, timedelta

from .config import load_schedule_preset
from .db import get_db
from .models import Schedule

_DAY_CN = {
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
    "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日",
}

_SLOT_CN = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}


def _init_preset(preset_name: str) -> list[Schedule]:
    data = load_schedule_preset(preset_name)
    if not data:
        return []
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM schedules WHERE type = ?", (preset_name,)
    ).fetchone()
    if existing:
        conn.close()
        return list_schedules(schedule_type=preset_name)
    for day, slot, desc in data:
        conn.execute(
            "INSERT INTO schedules (type, day, time_slot, description) VALUES (?, ?, ?, ?)",
            (preset_name, day, slot, desc),
        )
    conn.commit()
    result = list_schedules(schedule_type=preset_name)
    conn.close()
    return result


def init_clinic() -> list[Schedule]:
    return _init_preset("clinic")


def init_ask() -> list[Schedule]:
    return _init_preset("ask")


def init_practice() -> list[Schedule]:
    return _init_preset("practice")


def init_journal() -> list[Schedule]:
    return _init_preset("journal")


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
    day_order = "CASE day WHEN 'Monday' THEN 0 WHEN 'Tuesday' THEN 1 WHEN 'Wednesday' THEN 2 WHEN 'Thursday' THEN 3 WHEN 'Friday' THEN 4 WHEN 'Saturday' THEN 5 WHEN 'Sunday' THEN 6 ELSE 7 END"
    slot_order = "CASE time_slot WHEN 'morning' THEN 0 WHEN 'afternoon' THEN 1 WHEN 'evening' THEN 2 ELSE 3 END"
    sql += f" ORDER BY {day_order}, {slot_order}"
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


def format_day_cn(day: str) -> str:
    return _DAY_CN.get(day, day)


def format_slot_cn(slot: str) -> str:
    return _SLOT_CN.get(slot, slot)


def check_remind() -> list[Schedule]:
    items = today_schedules()
    return [s for s in items if s.type == "clinic"]


def smart_remind() -> str:
    """智能提醒：综合日程、偏好、会话记忆给出建议。"""
    from . import pref as pref_mod
    from . import session as session_mod

    lines = []
    today = date.today()
    today_cn = _DAY_CN.get(today.strftime("%A"), "")
    lines.append(f"🧠 智能提醒 — 今天{today_cn}（{today.strftime('%m-%d')}）")
    lines.append("")

    # 1. 今日日程
    items = today_schedules()
    if items:
        lines.append("📅 今日安排：")
        for s in items:
            slot_cn = _SLOT_CN.get(s.time_slot, s.time_slot)
            desc = f" {s.description}" if s.description else ""
            lines.append(f"  {slot_cn}  {s.type}{desc}")
    else:
        lines.append("📅 今天没有固定安排。")

    # 2. 偏好提醒
    prefs = pref_mod.list_prefs()
    pref_dict = dict(prefs) if prefs else {}
    lines.append("")
    if pref_dict:
        lines.append("⚙ 偏好提醒：")
        for k, v in prefs:
            if any(kw in k for kw in ("提醒", "习惯", "注意", "频率", "偏好")):
                lines.append(f"  · {k}: {v}")

    # 3. 上次会话待办
    last = session_mod.last_session()
    lines.append("")
    if last and last.todos:
        lines.append("📋 上次会话待办：")
        for line in last.todos.strip().split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line:
                lines.append(f"  □ {line}")
    else:
        lines.append("📋 没有待办事项。")

    # 4. 智能建议
    lines.append("")
    lines.append("💡 建议：")
    suggestions = []

    clinic_today = [s for s in items if s.type == "clinic"]
    if clinic_today:
        suggestions.append("今天有门诊，注意提前准备病例资料。")

    practice_today = [s for s in items if s.type == "practice"]
    if practice_today:
        suggestions.append("今天有练功安排。")

    if not items:
        suggestions.append("今天没有固定安排，适合集中精力推进项目。")

    commit_freq = pref_dict.get("代码提交频率", "")
    if commit_freq and ("每天" in commit_freq or "每日" in commit_freq):
        suggestions.append("今天可以提交代码。")

    if last and last.summary:
        suggestions.append("上次有未完成的会话，可以继续。")

    if not suggestions:
        suggestions.append("保持节奏，专注当前任务。")

    for s in suggestions:
        lines.append(f"  · {s}")

    return "\n".join(lines)


def check_practice_remind() -> list[Schedule]:
    items = today_schedules()
    return [s for s in items if s.type == "practice"]


def check_journal_remind() -> list[Schedule]:
    items = today_schedules()
    return [s for s in items if s.type == "journal"]


def check_tomorrow_ask() -> list[Schedule]:
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_name = tomorrow.strftime("%A")
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM schedules WHERE day = ? AND type = 'ask' AND is_active = 1",
        (tomorrow_name,),
    ).fetchall()
    conn.close()
    return [Schedule(**dict(r)) for r in rows]


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
        lines.append(f"  {slot_cn}  {s.type}  {desc.strip()}" if s.description else f"  {slot_cn}  {s.type}")
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
            parts = []
            for s in items:
                slot_cn = _SLOT_CN.get(s.time_slot, s.time_slot)
                d_str = f"{s.description}" if s.description else s.type
                parts.append(f"{slot_cn} {d_str}")
            lines.append(f"  {day_cn}（{d.strftime('%m-%d')}）{marker}: {', '.join(parts)}")
        else:
            lines.append(f"  {day_cn}（{d.strftime('%m-%d')}）{marker}: —")
    return "\n".join(lines)
