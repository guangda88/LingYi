"""领域工具 — 备忘/日程/计划/项目/情报/巡检/灵信/偏好/会话/知识库。"""

from __future__ import annotations

from ._registry import _register


# ── 备忘 ──────────────────────────────────────────────

def _memo_add(content: str) -> str:
    from ..memo import add_memo
    m = add_memo(content)
    return f"已记录备忘 #{m.id}：{content}"


def _memo_list() -> str:
    from ..memo import list_memos
    memos = list_memos()
    if not memos:
        return "暂无备忘"
    lines = [f"#{m.id} {m.content}" for m in memos[:10]]
    return "\n".join(lines)


def _memo_delete(memo_id: int) -> str:
    from ..memo import delete_memo
    ok = delete_memo(memo_id)
    return f"已删除备忘 #{memo_id}" if ok else f"未找到备忘 #{memo_id}"


_register("memo_add", "添加一条备忘录", {
    "content": {"type": "string", "description": "备忘内容"},
}, ["content"], _memo_add)

_register("memo_list", "查看最近的备忘录", {}, executor=_memo_list)

_register("memo_delete", "删除一条备忘录", {
    "memo_id": {"type": "integer", "description": "备忘ID"},
}, ["memo_id"], _memo_delete)


# ── 日程 ──────────────────────────────────────────────

def _schedule_today() -> str:
    from ..schedule import format_today
    result = format_today()
    return result or "今天没有日程"


def _schedule_week() -> str:
    from ..schedule import format_week
    return format_week()


def _schedule_add(schedule_type: str, day: str, time_slot: str, description: str) -> str:
    from ..schedule import add_schedule
    s = add_schedule(schedule_type, day, time_slot, description)
    return f"已添加日程 #{s.id}：{day} {time_slot} {description}"


_register("schedule_today", "查看今天的日程安排", {}, executor=_schedule_today)

_register("schedule_week", "查看本周的日程安排", {}, executor=_schedule_week)

_register("schedule_add", "添加一条日程", {
    "type": {"type": "string", "description": "日程类型（clinic/practice/ask/journal）"},
    "day": {"type": "string", "description": "星期几（Monday/Tuesday/...）"},
    "time_slot": {"type": "string", "description": "时间段（morning/afternoon/evening）"},
    "description": {"type": "string", "description": "日程描述"},
}, ["type", "day", "time_slot", "description"], _schedule_add)


# ── 计划 ──────────────────────────────────────────────

def _plan_list(area: str = "", status: str = "") -> str:
    from ..plan import list_plans, format_plan_short
    plans = list_plans(area=area or None, status=status or None)
    if not plans:
        return "没有符合条件的计划"
    return "\n".join(format_plan_short(p) for p in plans[:15])


def _plan_add(content: str, area: str = "编程") -> str:
    from ..plan import add_plan
    p = add_plan(content, area=area)
    return f"已添加计划 #{p.id}：{content}（{area}）"


def _plan_done(plan_id: int) -> str:
    from ..plan import done_plan
    p = done_plan(plan_id)
    return f"已完成计划 #{plan_id}" if p else f"未找到计划 #{plan_id}"


_register("plan_list", "查看计划列表", {
    "area": {"type": "string", "description": "领域筛选（医疗/编程/研究/论文/学术）"},
    "status": {"type": "string", "description": "状态筛选（todo/done/cancel）"},
}, executor=_plan_list)

_register("plan_add", "添加一条计划", {
    "content": {"type": "string", "description": "计划内容"},
    "area": {"type": "string", "description": "领域（医疗/编程/研究/论文/学术），默认编程"},
}, ["content"], _plan_add)

_register("plan_done", "标记计划为完成", {
    "plan_id": {"type": "integer", "description": "计划ID"},
}, ["plan_id"], _plan_done)


# ── 项目 ──────────────────────────────────────────────

def _project_list(status: str = "") -> str:
    from ..project import list_projects, format_project_short
    projects = list_projects(status=status or None)
    if not projects:
        return "没有项目"
    return "\n".join(format_project_short(p) for p in projects)


def _project_show(name: str) -> str:
    from ..project import show_project, format_project_detail
    p = show_project(name)
    if not p:
        return f"未找到项目: {name}"
    return format_project_detail(p)


_register("project_list", "查看项目列表", {
    "status": {"type": "string", "description": "状态筛选（active/maintenance/paused/archived）"},
}, executor=_project_list)

_register("project_show", "查看项目详情", {
    "name": {"type": "string", "description": "项目名或别名"},
}, ["name"], _project_show)


# ── 情报 ──────────────────────────────────────────────

def _briefing() -> str:
    from ..briefing import collect_all, format_briefing
    data = collect_all()
    return format_briefing(data, compact=True)


_register("briefing", "获取灵字辈情报汇总", {}, executor=_briefing)


# ── 巡检 ──────────────────────────────────────────────

def _patrol() -> str:
    from ..patrol import generate_report
    return generate_report()


_register("patrol", "执行项目巡检（检查各项目Git变更）", {}, executor=_patrol)


# ── 灵信 ──────────────────────────────────────────────

def _msg_list() -> str:
    from ..lingmessage import list_discussions, format_discussion_list
    discussions = list_discussions(status="open")
    return format_discussion_list(discussions)


def _msg_send(topic: str, content: str) -> str:
    from ..lingmessage import send_message
    msg = send_message(from_id="lingyi", topic=topic, content=content)
    return f"已发送灵信 [{topic}]: {msg.id}"


def _msg_read(discussion_id: str) -> str:
    from ..lingmessage import read_discussion, format_discussion_thread
    disc = read_discussion(discussion_id)
    if not disc:
        return f"未找到讨论: {discussion_id}"
    return format_discussion_thread(disc)


_register("msg_list", "查看灵信讨论列表", {}, executor=_msg_list)

_register("msg_send", "发送灵信消息", {
    "topic": {"type": "string", "description": "讨论主题"},
    "content": {"type": "string", "description": "消息内容"},
}, ["topic", "content"], _msg_send)

_register("msg_read", "阅读灵信讨论详情", {
    "discussion_id": {"type": "string", "description": "讨论ID"},
}, ["discussion_id"], _msg_read)


# ── 偏好 ──────────────────────────────────────────────

def _pref_list() -> str:
    from ..pref import list_prefs, format_pref_list
    prefs = list_prefs()
    return format_pref_list(prefs)


def _pref_set(key: str, value: str) -> str:
    from ..pref import set_pref
    set_pref(key, value)
    return f"已设置偏好 {key} = {value}"


_register("pref_list", "查看用户偏好设置", {}, executor=_pref_list)

_register("pref_set", "设置用户偏好", {
    "key": {"type": "string", "description": "偏好键名"},
    "value": {"type": "string", "description": "偏好值"},
}, ["key", "value"], _pref_set)


# ── 会话 ──────────────────────────────────────────────

def _session_last() -> str:
    from ..session import last_session, format_session_resume
    s = last_session()
    if not s:
        return "没有最近的会话记录"
    return format_session_resume(s)


_register("session_last", "查看上次会话摘要", {}, executor=_session_last)


# ── 知识库 ────────────────────────────────────────────

def _ask(query: str) -> str:
    from ..ask import ask_knowledge
    return ask_knowledge(query)


_register("ask", "向灵知知识库查询", {
    "query": {"type": "string", "description": "查询内容"},
}, ["query"], _ask)
