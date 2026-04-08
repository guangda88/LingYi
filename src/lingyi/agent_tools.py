"""Agent 工具实现 — function calling 工具函数与调度表"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Callable

logger = logging.getLogger(__name__)

_ToolFn = Callable[..., str]


def _check_github(repo: str) -> str:
    try:
        url = f"https://api.github.com/repos/{repo}"
        req = urllib.request.Request(url, headers={"User-Agent": "LingYi/0.16"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        result = {
            "repo": repo,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "default_branch": data.get("default_branch", ""),
            "updated_at": data.get("updated_at", ""),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _check_pypi(package: str) -> str:
    try:
        url = f"https://pypi.org/pypi/{package}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "LingYi/0.16"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        info = data.get("info", {})
        result = {
            "package": package,
            "version": info.get("version", ""),
            "summary": info.get("summary", ""),
            "project_urls": info.get("project_urls", {}),
        }
        try:
            stats_url = f"https://pypistats.org/api/packages/{package}/recent"
            req2 = urllib.request.Request(stats_url, headers={"User-Agent": "LingYi/0.16"})
            with urllib.request.urlopen(req2, timeout=5) as resp2:
                stats = json.loads(resp2.read().decode())
            result["downloads_last_month"] = stats.get("data", {}).get("last_month", "N/A")
        except Exception:
            result["downloads_last_month"] = "查询失败"
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _list_memos() -> str:
    try:
        from .memo import list_memos
        memos = list_memos()
        if not memos:
            return "目前没有备忘录。"
        lines = [f"#{m.id} {m.content} ({m.created_at[:16]})" for m in memos[:10]]
        return "\n".join(lines)
    except Exception as e:
        return f"查询失败: {e}"


def _add_memo(content: str) -> str:
    try:
        from .memo import add_memo
        m = add_memo(content)
        return f"已记录：{content}（备忘 #{m.id}）"
    except Exception as e:
        return f"记录失败: {e}"


def _check_schedule(range: str = "today") -> str:
    try:
        from .schedule import format_today, format_week
        if range == "week":
            return format_week() or "本周没有安排。"
        return format_today() or "今天没有安排。"
    except Exception as e:
        return f"查询失败: {e}"


def _list_plans(area: str = "") -> str:
    try:
        from .plan import list_plans, plan_stats
        plans = list_plans(area=area or None)
        if not plans:
            return "没有找到匹配的计划。"
        lines = [f"#{p.id} [{p.status}] {p.content}（{p.area}）" for p in plans[:10]]
        stats = plan_stats()
        summary = " | ".join(f"{k}: {v.get('done',0)}/{v.get('total',0)}" for k, v in stats.items())
        return summary + "\n" + "\n".join(lines)
    except Exception as e:
        return f"查询失败: {e}"


def _list_projects() -> str:
    try:
        from .project import list_projects
        projects = list_projects()
        if not projects:
            return "没有项目记录。"
        lines = [f"- {p.name}({p.alias}) [{p.status}] 优先级:{p.priority} 版本:{p.version}" for p in projects]
        return "\n".join(lines)
    except Exception as e:
        return f"查询失败: {e}"


def _check_briefing() -> str:
    try:
        from .briefing import collect_all
        data = collect_all()
        lines = []
        for key, label in [("lingzhi", "灵知"), ("lingflow", "灵通"), ("lingclaude", "灵克"), ("lingtongask", "灵通问道")]:
            info = data.get(key, {})
            if info.get("available"):
                lines.append(f"- {label}: 在线")
            else:
                lines.append(f"- {label}: 离线")
        lc = data.get("lingclaude", {})
        if lc.get("sessions"):
            lines.append(f"- 灵克开发会话: {lc['sessions']} 条")
        return "\n".join(lines)
    except Exception as e:
        return f"收集失败: {e}"


def _list_lingmessage(status: str = "") -> str:
    try:
        from .lingmessage import list_discussions
        discussions = list_discussions(status=status or None)
        if not discussions:
            return "灵信中暂无讨论。"
        lines = []
        for d in discussions[:8]:
            parts = ", ".join(d.get("participants", []))
            lines.append(f"- [{d['status']}] {d['topic']} (参与者: {parts}, {d.get('message_count',0)}条)")
        return "\n".join(lines)
    except Exception as e:
        return f"查询失败: {e}"


def _read_lingmessage(discussion_id: str) -> str:
    try:
        from .lingmessage import read_discussion
        disc = read_discussion(discussion_id)
        if not disc:
            return f"未找到讨论: {discussion_id}"
        lines = [f"主题: {disc['topic']}", f"状态: {disc.get('status','')} 发起: {disc.get('initiator_name','')}"]
        for msg in disc.get("messages", []):
            lines.append(f"\n{msg.get('from_name','?')} [{msg.get('timestamp','')[:16]}]")
            lines.append(f"  {msg.get('content','')}")
        return "\n".join(lines)
    except Exception as e:
        return f"读取失败: {e}"


def _search_web(query: str) -> str:
    try:
        url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote_plus(query)}&tags=story&hitsPerPage=8"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LingYi)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        lines = []
        for i, hit in enumerate(data.get("hits", [])[:8]):
            title = (hit.get("title") or "").strip()
            link = hit.get("url", "")
            points = hit.get("points") or 0
            if not title:
                continue
            line = f"{i+1}. {title} ({points}pts)"
            if link:
                line += f"\n   {link}"
            lines.append(line)
        return "\n".join(lines) if lines else "未找到相关结果。"
    except Exception as e:
        return f"搜索失败: {e}"


def _patrol_projects() -> str:
    try:
        from .patrol import generate_report
        return generate_report()
    except Exception as e:
        return f"巡检失败: {e}"


TOOL_MAP: dict[str, _ToolFn] = {
    "check_github": _check_github,
    "check_pypi": _check_pypi,
    "list_memos": _list_memos,
    "add_memo": _add_memo,
    "check_schedule": _check_schedule,
    "list_plans": _list_plans,
    "list_projects": _list_projects,
    "check_briefing": _check_briefing,
    "list_lingmessage": _list_lingmessage,
    "read_lingmessage": _read_lingmessage,
    "search_web": _search_web,
    "patrol_projects": _patrol_projects,
}


def quick_route(text: str) -> str | None:
    t = text.lower().strip()
    if any(kw in t for kw in ("备忘", "记一下", "提醒我")):
        content = text
        for kw in ("备忘", "记一下", "提醒我", "帮我"):
            content = content.replace(kw, "", 1)
        content = content.strip()
        if content:
            return _add_memo(content)
        return "你想记什么？"
    if any(kw in t for kw in ("再见", "拜拜", "挂了", "挂电话", "结束", "晚安")):
        return "好的，再见！随时找我。"
    return None
