"""Web 数据路由：仪表盘、备忘、日程、项目、计划、偏好、日志。"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path

from ._web_app_helpers import git_info

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _serialize(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def _briefing_detail(key, info):
    if not info.get("available"):
        return "离线"
    if key == "lingzhi":
        return f"查询 {info.get('total_queries', 0)}"
    if key == "lingflow":
        return f"反馈 {info.get('feedback_count', 0)}"
    if key == "lingclaude":
        return f"会话 {info.get('sessions', 0)}"
    if key == "lingtongask":
        return f"评论 {info.get('total_comments', 0)}"
    return ""


def register_data_routes(app, JSONResponse, Request):
    @app.get("/api/dashboard")
    async def dashboard():
        from ..schedule import today_schedules, format_day_cn, format_slot_cn
        from ..memo import list_memos
        from ..project import list_projects
        from ..briefing import collect_all

        today_items = today_schedules()
        memos = list_memos()
        projects = list_projects(status="active")

        try:
            briefing = collect_all()
        except Exception:
            briefing = {}

        ling_status = []
        for key, label in [("lingzhi", "灵知"), ("lingflow", "灵通"), ("lingclaude", "灵克"), ("lingtongask", "灵通问道")]:
            info = briefing.get(key, {})
            ling_status.append({
                "name": label,
                "online": info.get("available", False),
                "detail": _briefing_detail(key, info),
            })

        return JSONResponse({
            "date": date.today().isoformat(),
            "weekday": format_day_cn(date.today().strftime("%A")),
            "today_schedules": [
                {
                    "id": s.id, "type": s.type,
                    "slot": format_slot_cn(s.time_slot),
                    "description": s.description or s.type,
                }
                for s in today_items
            ],
            "recent_memos": [{"id": m.id, "content": m.content, "time": m.created_at} for m in memos[:5]],
            "active_projects": [
                {
                    "id": p.id, "name": p.name, "alias": p.alias,
                    "priority": p.priority, "category": p.category,
                    "description": p.description, "status": p.status,
                }
                for p in projects[:8]
            ],
            "ling_family": ling_status,
        })

    @app.get("/api/memos")
    async def api_memos():
        from ..memo import list_memos
        return JSONResponse([_serialize(m) for m in list_memos()])

    @app.post("/api/memos")
    async def api_add_memo(request: dict):
        from ..memo import add_memo
        content = request.get("content", "").strip()
        if not content:
            return JSONResponse({"error": "内容不能为空"}, status_code=400)
        m = add_memo(content)
        return JSONResponse(_serialize(m))

    @app.delete("/api/memos/{memo_id}")
    async def api_delete_memo(memo_id: int):
        from ..memo import delete_memo
        ok = delete_memo(memo_id)
        return JSONResponse({"ok": ok})

    @app.get("/api/schedules")
    async def api_schedules(schedule_type: str | None = None):
        from ..schedule import list_schedules, format_day_cn, format_slot_cn
        items = list_schedules(schedule_type=schedule_type, active_only=True)
        return JSONResponse([
            {
                "id": s.id, "type": s.type, "day": s.day,
                "day_cn": format_day_cn(s.day), "slot_cn": format_slot_cn(s.time_slot),
                "description": s.description, "active": s.is_active,
            }
            for s in items
        ])

    @app.get("/api/schedules/today")
    async def api_schedules_today():
        from ..schedule import today_schedules, format_slot_cn
        items = today_schedules()
        return JSONResponse([
            {"id": s.id, "type": s.type, "slot": format_slot_cn(s.time_slot), "desc": s.description or s.type}
            for s in items
        ])

    @app.get("/api/schedules/week")
    async def api_schedules_week():
        from ..schedule import week_schedules, format_day_cn, format_slot_cn
        data = week_schedules()
        result = {}
        for day, items in data.items():
            result[day] = {
                "cn": format_day_cn(day),
                "items": [
                    {"type": s.type, "slot": format_slot_cn(s.time_slot), "desc": s.description or s.type}
                    for s in items
                ],
            }
        return JSONResponse(result)

    @app.get("/api/projects")
    async def api_projects(status: str | None = None):
        from ..project import list_projects
        items = list_projects(status=status)
        return JSONResponse([_serialize(p) for p in items])

    @app.get("/api/projects/live")
    async def api_projects_live():
        from ..project import list_projects
        items = list_projects()

        try:
            from ..lingmessage import list_discussions as _list_disc
            threads = _list_disc()
        except Exception:
            threads = []

        _PROJECT_ALIASES = {
            "LingFlow": ["lingflow", "灵通"], "LingClaude": ["lingclaude", "灵克"],
            "灵知系统": ["lingzhi", "灵知"], "LingYi": ["lingyi", "灵依"],
            "lingtongask": ["lingtongask", "灵通问道"], "Ling-term-mcp": ["lingterm", "灵犀"],
            "LingMinOpt": ["lingminopt", "灵极优"], "zhineng-bridge": ["zhibridge", "智桥"],
            "lingresearch": ["lingresearch", "灵研"],
            "zhineng-knowledge-system": ["lingzhi", "灵知"],
        }

        results = []
        for p in items:
            d = _serialize(p)
            d["git"] = git_info(p.repo)
            if d["git"].get("tag"):
                d["version"] = d["git"]["tag"]

            aliases = _PROJECT_ALIASES.get(p.name, [p.name.lower(), p.alias])
            related = []
            for t in threads:
                topic = t.get("topic", "")
                tags = t.get("tags", [])
                text = (topic + " " + " ".join(tags)).lower()
                if any(a.lower() in text for a in aliases):
                    related.append({
                        "id": t.get("id") or t.get("thread_id", ""),
                        "topic": topic[:60],
                        "messages": t.get("message_count", 0),
                        "updated": t.get("updated_at", ""),
                    })
            related.sort(key=lambda x: x.get("updated", ""), reverse=True)
            d["discussions"] = related[:3]
            results.append(d)

        return JSONResponse(results)

    @app.get("/api/projects/{name}")
    async def api_project_detail(name: str):
        from ..project import show_project
        p = show_project(name)
        if not p:
            return JSONResponse({"error": "项目不存在"}, status_code=404)
        return JSONResponse(_serialize(p))

    @app.get("/api/plans")
    async def api_plans():
        from ..plan import list_plans
        return JSONResponse([_serialize(p) for p in list_plans()])

    @app.post("/api/plans")
    async def api_add_plan(request: dict):
        from ..plan import add_plan
        content = request.get("content", "").strip()
        if not content:
            return JSONResponse({"error": "内容不能为空"}, status_code=400)
        area = request.get("area", "编程")
        project = request.get("project", "")
        p = add_plan(content=content, area=area, project=project)
        return JSONResponse(_serialize(p))

    @app.get("/api/preferences")
    async def api_preferences():
        from ..pref import list_prefs
        return JSONResponse([{"key": k, "value": v} for k, v in list_prefs()])

    @app.post("/api/preferences")
    async def api_set_pref(request: dict):
        from ..pref import set_pref
        key = request.get("key", "").strip()
        value = request.get("value", "").strip()
        if not key:
            return JSONResponse({"error": "key不能为空"}, status_code=400)
        set_pref(key, value)
        return JSONResponse({"ok": True})

    _LOG_SOURCES: dict[str, list[str]] = {
        "灵依": ["/tmp/lingyi.log", "/tmp/lingyi_web.log"],
        "灵克": ["/tmp/lingclaude.log", "/tmp/lingclaude-api.log"],
        "灵知": ["/tmp/lingzhi.log", "/tmp/lingzhi-auto.log"],
        "灵研究": ["/tmp/lingresearch.log"],
        "灵民调": ["/tmp/lingminopt.log"],
        "灵养": ["/tmp/lingyang_responder.log"],
        "智桥": ["/home/ai/zhineng-bridge/logs/lingflow_*.log"],
        "灵通": ["/home/ai/LingFlow/logs/lingflow_*.log"],
        "系统监控": ["/home/ai/zhineng-knowledge-system/logs/monitor.log",
                     "/home/ai/zhineng-knowledge-system/logs/docker_monitor.log"],
        "议事厅告警": [str(Path.home() / ".lingyi" / "logs" / "council_health.jsonl")],
        "VNC": ["/tmp/x11vnc.log"],
    }

    _ERROR_KEYWORDS = ("ERROR", "error", "Exception", "Traceback", "CRITICAL",
                       "WARN", "WARNING", "告警", "失败", "异常", "超时")

    @app.get("/api/logs")
    async def api_logs(source: str = "灵依", lines: int = 30, errors_only: bool = False):
        import glob
        paths = _LOG_SOURCES.get(source, [])
        if not paths:
            return JSONResponse({"error": f"未知日志源: {source}", "sources": list(_LOG_SOURCES.keys())}, status_code=400)
        all_paths: list[str] = []
        for p in paths:
            all_paths.extend(sorted(glob.glob(p)))
        if not all_paths:
            return JSONResponse({"source": source, "lines": []})
        result_lines: list[str] = []
        for fp in reversed(all_paths):
            try:
                with open(fp, "r", errors="replace") as f:
                    file_lines = f.readlines()
                    result_lines.extend(file_lines[-lines:])
            except Exception:
                result_lines.append(f"[无法读取: {fp}]")
        if errors_only:
            result_lines = [ln for ln in result_lines
                           if any(kw in ln for kw in _ERROR_KEYWORDS)]
            result_lines = result_lines[-lines:]
        return JSONResponse({"source": source, "lines": result_lines, "sources": list(_LOG_SOURCES.keys())})
