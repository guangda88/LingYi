"""计划管理：五大领域任务、周计划、完成率统计。"""

from datetime import date, timedelta

from .db import get_db
from .models import Plan

_AREAS = ["医疗", "编程", "研究", "论文", "学术"]
_STATUS_CN = {"todo": "待办", "done": "完成", "cancel": "取消"}


def add_plan(content: str, area: str = "编程", project: str = "",
             due_date: str = "", notes: str = "") -> Plan:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO plans (content, area, project, due_date, notes) VALUES (?, ?, ?, ?, ?)",
        (content, area, project, due_date, notes),
    )
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return Plan(**dict(row))


def list_plans(area: str | None = None, status: str | None = None,
               project: str | None = None) -> list[Plan]:
    conn = get_db()
    sql = "SELECT * FROM plans"
    conditions: list[str] = []
    params: list = []
    if area:
        conditions.append("area = ?")
        params.append(area)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if project:
        conditions.append("project = ?")
        params.append(project)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY CASE status WHEN 'todo' THEN 0 WHEN 'done' THEN 1 ELSE 2 END, created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [Plan(**dict(r)) for r in rows]


def show_plan(plan_id: int) -> Plan | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return Plan(**dict(row)) if row else None


def done_plan(plan_id: int) -> Plan | None:
    conn = get_db()
    conn.execute("UPDATE plans SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return Plan(**dict(row)) if row else None


def cancel_plan(plan_id: int) -> bool:
    conn = get_db()
    cur = conn.execute("UPDATE plans SET status = 'cancel', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def week_plans() -> list[Plan]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM plans WHERE due_date >= ? AND due_date <= ? AND status = 'todo' ORDER BY due_date, area",
        (monday.isoformat(), sunday.isoformat()),
    ).fetchall()
    conn.close()
    return [Plan(**dict(r)) for r in rows]


def plan_stats() -> dict[str, dict[str, int]]:
    conn = get_db()
    rows = conn.execute("SELECT area, status, COUNT(*) as cnt FROM plans GROUP BY area, status").fetchall()
    conn.close()
    result: dict[str, dict[str, int]] = {}
    for r in rows:
        area = r["area"]
        result.setdefault(area, {"todo": 0, "done": 0, "cancel": 0})
        result[area][r["status"]] = r["cnt"]
    return result


def format_plan_short(p: Plan) -> str:
    status_cn = _STATUS_CN.get(p.status, p.status)
    area_tag = f"[{p.area}]" if p.area else ""
    proj_tag = f" @{p.project}" if p.project else ""
    return f"  [{p.id}] {area_tag} {p.content}{proj_tag}  {status_cn}"


def format_plan_detail(p: Plan) -> str:
    lines = [
        f"  #{p.id}",
        f"  内容：{p.content}",
        f"  领域：{p.area}",
        f"  项目：{p.project or '—'}",
        f"  状态：{_STATUS_CN.get(p.status, p.status)}",
        f"  截止：{p.due_date or '—'}",
        f"  备注：{p.notes or '—'}",
        f"  创建：{p.created_at}",
    ]
    return "\n".join(lines)


def format_plan_week() -> str:
    plans = week_plans()
    if not plans:
        return "本周没有计划。"
    lines = []
    by_date: dict[str, list[Plan]] = {}
    for p in plans:
        key = p.due_date or "未定"
        by_date.setdefault(key, []).append(p)
    for d, items in sorted(by_date.items()):
        lines.append(f"{'─' * 3} {d}（{len(items)}）{'─' * 20}")
        for p in items:
            lines.append(format_plan_short(p))
    return "\n".join(lines)


def format_plan_stats() -> str:
    stats = plan_stats()
    if not stats:
        return "暂无计划数据。"
    lines = []
    for area, counts in sorted(stats.items()):
        total = counts["todo"] + counts["done"] + counts["cancel"]
        done = counts["done"]
        pct = int(done / total * 100) if total else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"  {area}  {bar} {pct}%  ({done}/{total})")
    return "\n".join(lines)
