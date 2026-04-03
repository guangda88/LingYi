"""周报生成：汇总本周日程、计划、备忘、项目状态。"""

from datetime import date, timedelta

from . import __version__
from . import schedule as sched_mod
from . import plan as plan_mod
from . import memo as memo_mod
from . import project as proj_mod
from . import session as session_mod


def _report_schedule(monday: date) -> list[str]:
    lines = ["📅 本周日程："]
    week_data = sched_mod.week_schedules()
    has_schedule = False
    for i in range(7):
        d = monday + timedelta(days=i)
        day_name = d.strftime("%A")
        day_cn = sched_mod.format_day_cn(day_name)
        items = week_data.get(day_name, [])
        if items:
            has_schedule = True
            parts = []
            for s in items:
                slot_cn = sched_mod.format_slot_cn(s.time_slot)
                desc = f"{s.description}" if s.description else s.type
                parts.append(f"{slot_cn}{desc}")
            lines.append(f"  {day_cn}: {', '.join(parts)}")
    if not has_schedule:
        lines.append("  本周无固定日程。")
    return lines


def _report_plans() -> list[str]:
    lines = ["📋 计划进度："]
    stats = plan_mod.plan_stats()
    if stats:
        total_all = sum(sum(c.values()) for c in stats.values())
        done_all = sum(c.get("done", 0) for c in stats.values())
        todo_all = sum(c.get("todo", 0) for c in stats.values())
        pct = int(done_all / total_all * 100) if total_all else 0
        lines.append(f"  总完成率：{pct}%（{done_all}/{total_all}）")
        lines.append(f"  待办：{todo_all}项")
        for area, counts in sorted(stats.items()):
            area_total = sum(counts.values())
            area_done = counts.get("done", 0)
            lines.append(f"  {area}: {area_done}/{area_total}")
    else:
        lines.append("  暂无计划数据。")
    return lines


def _report_memos() -> list[str]:
    lines = ["📝 近期备忘："]
    memos = memo_mod.list_memos()
    recent = memos[:5]
    if recent:
        for m in recent:
            lines.append(f"  · {m.content[:60]}")
    else:
        lines.append("  暂无备忘。")
    return lines


def _report_projects() -> list[str]:
    lines = ["📂 活跃项目："]
    active_projects = proj_mod.list_projects(status="active")
    if active_projects:
        for p in active_projects:
            ver = f" v{p.version}" if p.version else ""
            priority_cn = proj_mod.format_priority_cn(p.priority)
            lines.append(f"  · {p.name}（{priority_cn}）{ver}")
    else:
        lines.append("  暂无活跃项目。")
    return lines


def _report_sessions() -> list[str]:
    lines = ["💬 最近会话："]
    sessions = session_mod.list_sessions(limit=3)
    if sessions:
        for s in sessions:
            summary = s.summary[:50] if s.summary else "（无摘要）"
            lines.append(f"  · [{s.id}] {s.created_at} {summary}")
    else:
        lines.append("  暂无会话记录。")
    return lines


def generate_weekly_report() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_range = f"{monday.strftime('%m-%d')} ~ {sunday.strftime('%m-%d')}"

    lines = [
        f"📊 灵依周报 — {week_range}",
        "=" * 40,
        "",
    ]
    lines.extend(_report_schedule(monday))
    lines.append("")
    lines.extend(_report_plans())
    lines.append("")
    lines.extend(_report_memos())
    lines.append("")
    lines.extend(_report_projects())
    lines.append("")
    lines.extend(_report_sessions())

    lines.append("")
    lines.append(f"— 灵依 v{__version__} · 生成于 {today.strftime('%Y-%m-%d')} —")

    return "\n".join(lines)
