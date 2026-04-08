"""灵依 MCP Server — 27个核心能力封装为MCP工具。

工具清单（灵系命名）:
  个人管理: add_memo(灵记), list_memos(灵览), add_schedule(灵排),
            list_schedules(灵视), add_plan(灵划), list_plans(灵查)
  项目报告: show_project(灵项), generate_report(灵报), patrol_project(灵巡)
  情报汇总: get_briefing(灵汇), digest_content(灵摘), ask_lingzhi(灵问)
  P0新增: today_schedule, week_schedule, smart_remind, done_plan, week_plans,
          plan_stats, list_projects, save_session, last_session, search_knowledge,
          speak, synthesize_to_file, transcribe, council_scan, council_health
  约束验证: verify_assertion, verification_stats, verification_log
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="LingYi",
    instructions="灵依（LingYi）MCP Server — 私人AI助理核心能力",
)


def _to_dict(obj: Any) -> dict:
    """将 dataclass 实例转为字典，便于 JSON 序列化。"""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj


# 初始化约束层
_constraint_layer = None

def _get_constraint_layer():
    """获取约束层实例（延迟初始化）"""
    global _constraint_layer
    if _constraint_layer is None:
        try:
            from .constraint_layer import ConstraintLayer
            _constraint_layer = ConstraintLayer()
            logger.info("约束层已初始化")
        except ImportError as e:
            logger.warning(f"约束层初始化失败: {e}")
    return _constraint_layer


# ── 个人管理（6个工具） ──


@mcp.tool(name="add_memo", description="添加备忘录（灵记）")
def tool_add_memo(content: str) -> dict:
    """添加一条备忘录，返回包含 id 的备忘录对象。"""
    from .memo import add_memo

    result = add_memo(content)
    return _to_dict(result)


@mcp.tool(name="list_memos", description="列出所有备忘录（灵览）")
def tool_list_memos(limit: int = 20) -> list[dict]:
    """列出备忘录，默认返回最近20条。"""
    from .memo import list_memos

    results = list_memos()
    return [_to_dict(m) for m in results[:limit]]


@mcp.tool(name="add_schedule", description="添加日程（灵排）")
def tool_add_schedule(
    schedule_type: str,
    day: str,
    time_slot: str,
    description: str = "",
) -> dict:
    """添加日程安排。day 为英文星期名(Monday-Sunday)，time_slot 为 morning/afternoon/evening。"""
    from .schedule import add_schedule

    result = add_schedule(schedule_type, day, time_slot, description)
    return _to_dict(result)


@mcp.tool(name="list_schedules", description="查看日程（灵视）")
def tool_list_schedules(
    schedule_type: str = "",
    active_only: bool = True,
) -> list[dict]:
    """列出日程安排，可按类型筛选。"""
    from .schedule import list_schedules

    results = list_schedules(
        schedule_type=schedule_type or None,
        active_only=active_only,
    )
    return [_to_dict(s) for s in results]


@mcp.tool(name="add_plan", description="添加计划（灵划）")
def tool_add_plan(
    content: str,
    area: str = "编程",
    project: str = "",
    due_date: str = "",
) -> dict:
    """添加任务计划。area 可选: 医疗/编程/研究/论文/学术。"""
    from .plan import add_plan

    result = add_plan(content=content, area=area, project=project, due_date=due_date)
    return _to_dict(result)


@mcp.tool(name="list_plans", description="查看计划（灵查）")
def tool_list_plans(
    area: str = "",
    status: str = "",
    project: str = "",
) -> list[dict]:
    """列出任务计划，可按领域/状态/项目筛选。status 可选: todo/done/cancel。"""
    from .plan import list_plans

    results = list_plans(
        area=area or None,
        status=status or None,
        project=project or None,
    )
    return [_to_dict(p) for p in results]


# ── 项目报告（3个工具） ──


@mcp.tool(name="show_project", description="查看项目状态（灵项）")
def tool_show_project(name_or_alias: str) -> dict | None:
    """按项目名称或别名查看项目详情。"""
    from .project import show_project

    result = show_project(name_or_alias)
    return _to_dict(result) if result else None


@mcp.tool(name="generate_report", description="生成周报（灵报）")
def tool_generate_report() -> str:
    """生成灵依周报，汇总本周日程、计划进度、备忘、项目状态、会话记录。"""
    from .report import generate_weekly_report

    return generate_weekly_report()


@mcp.tool(name="patrol_project", description="项目巡检（灵巡）")
def tool_patrol_project() -> str:
    """巡检所有配置的项目，检查最近变化，生成巡检报告。"""
    from .patrol import generate_report

    return generate_report()


# ── 情报汇总（3个工具） ──


@mcp.tool(name="get_briefing", description="情报汇报（灵汇）")
def tool_get_briefing(compact: bool = False) -> str:
    """收集灵知/灵通/灵克/灵通问道的情报，生成汇报。compact 为 True 时返回简短版。"""
    from .briefing import collect_all, format_briefing, format_briefing_short

    data = collect_all()
    if compact:
        return format_briefing_short(data)
    return format_briefing(data)


@mcp.tool(name="digest_content", description="信息摘要（灵摘）")
def tool_digest_content(text: str) -> dict:
    """解析自由文本，提取待办、决策、偏好、关键事实。"""
    from .digest import digest_text

    return digest_text(text)


@mcp.tool(name="ask_lingzhi", description="灵知问答（灵问）")
def tool_ask_lingzhi(question: str, category: str = "") -> dict:
    """向灵知知识库提问。category 可选: 气功/儒家/佛家/道家/武术/哲学/科学/心理学。
    医学诊断类查询将被拦截。

    通过约束层验证，确保不违反医疗边界。"""
    from .ask import ask_knowledge
    from .constraint_layer import Assertion

    constraint = _get_constraint_layer()
    if constraint:
        # 构造断言
        assertion = Assertion(
            member_id="lingzhi",
            assertion_type="fact",
            content=f"向灵知提问: {question}",
            tool_call={
                "name": "ask_lingzhi",
                "arguments": {"question": question, "category": category}
            }
        )

        # 验证断言
        result = constraint.verify_assertion(assertion)

        if not result.passed:
            logger.warning(f"约束层拦截灵知提问: {result.reason}")
            return {
                "error": "约束层拦截",
                "reason": result.reason,
                "recommendation": result.recommendation
            }

    # 验证通过，执行查询
    result = ask_knowledge(
        question=question,
        category=category or None,
    )
    return result


# ── P0 核心缺失（15个工具） ──


@mcp.tool(name="today_schedule", description="今日日程（灵日）")
def tool_today_schedule() -> list[dict]:
    """返回今日全部日程安排。"""
    from .schedule import today_schedules

    results = today_schedules()
    return [_to_dict(s) for s in results]


@mcp.tool(name="week_schedule", description="本周日程（灵周）")
def tool_week_schedule() -> dict:
    """返回本周按天分组的日程安排。key 为中文星期名。"""
    from .schedule import week_schedules

    results = week_schedules()
    return {day: [_to_dict(s) for s in items] for day, items in results.items()}


@mcp.tool(name="smart_remind", description="智能提醒（灵醒）")
def tool_smart_remind() -> str:
    """结合今日日程、用户偏好、上次会话待办，生成上下文提醒建议。"""
    from .schedule import smart_remind

    return smart_remind()


@mcp.tool(name="done_plan", description="完成计划（灵成）")
def tool_done_plan(plan_id: int) -> dict | None:
    """标记计划为已完成。返回更新后的计划对象。"""
    from .plan import done_plan

    result = done_plan(plan_id)
    return _to_dict(result) if result else None


@mcp.tool(name="week_plans", description="本周计划（灵划周）")
def tool_week_plans() -> list[dict]:
    """返回本周（7天内到期或本周创建的）待办计划。"""
    from .plan import week_plans

    results = week_plans()
    return [_to_dict(p) for p in results]


@mcp.tool(name="plan_stats", description="五域统计（灵统）")
def tool_plan_stats() -> dict:
    """返回五个领域（医疗/编程/研究/论文/学术）的计划完成统计。"""
    from .plan import plan_stats

    return plan_stats()


@mcp.tool(name="list_projects", description="项目看板（灵板）")
def tool_list_projects(status: str = "", category: str = "") -> list[dict]:
    """列出项目，可按 status(active/maintenance/paused/archived) 或 category 筛选。"""
    from .project import list_projects

    results = list_projects(
        status=status or None,
        category=category or None,
    )
    return [_to_dict(p) for p in results]


@mcp.tool(name="save_session", description="保存会话（灵忆）")
def tool_save_session(
    summary: str = "",
    files: str = "",
    decisions: str = "",
    todos: str = "",
    prefs_noted: str = "",
) -> dict:
    """保存当前会话摘要，用于跨会话记忆恢复。"""
    from .session import save_session

    result = save_session(
        summary=summary,
        files=files,
        decisions=decisions,
        todos=todos,
        prefs_noted=prefs_noted,
    )
    return _to_dict(result)


@mcp.tool(name="last_session", description="上次会话（灵回）")
def tool_last_session() -> dict | None:
    """获取最近一次会话记录，用于上下文恢复。"""
    from .session import last_session

    result = last_session()
    return _to_dict(result) if result else None


@mcp.tool(name="search_knowledge", description="灵知搜索（灵搜）")
def tool_search_knowledge(
    query: str,
    category: str = "",
    top_k: int = 5,
) -> dict:
    """搜索灵知知识库，返回匹配文档列表。比 ask_lingzhi 更灵活。
    医学诊断类查询将被拦截。

    通过约束层验证，确保不违反医疗边界和九域限制。"""
    from .ask import search_knowledge
    from .constraint_layer import Assertion

    constraint = _get_constraint_layer()
    if constraint:
        # 构造断言
        assertion = Assertion(
            member_id="lingzhi",
            assertion_type="fact",
            content=f"搜索灵知知识库: {query}",
            tool_call={
                "name": "search_knowledge",
                "arguments": {"query": query, "category": category, "top_k": top_k}
            }
        )

        # 验证断言
        result = constraint.verify_assertion(assertion)

        if not result.passed:
            logger.warning(f"约束层拦截灵知搜索: {result.reason}")
            return {
                "error": "约束层拦截",
                "reason": result.reason,
                "recommendation": result.recommendation
            }

    # 验证通过，执行搜索
    return search_knowledge(
        query=query,
        category=category or None,
        top_k=top_k,
    )


@mcp.tool(name="speak", description="语音播报（灵声）")
def tool_speak(text: str, voice: str = "") -> dict:
    """通过 TTS 语音播报文本。需要 edge-tts + ffplay。"""
    from .tts import speak, DEFAULT_VOICE

    ok = speak(text, voice=voice or DEFAULT_VOICE)
    return {"spoken": ok, "text_length": len(text)}


@mcp.tool(name="synthesize_to_file", description="合成语音文件（灵录声）")
def tool_synthesize_to_file(text: str, output_path: str, voice: str = "") -> dict:
    """将文本合成为语音文件(MP3)。返回文件路径。"""
    from .tts import synthesize_to_file, DEFAULT_VOICE

    path = synthesize_to_file(text, output_path, voice=voice or DEFAULT_VOICE)
    return {"output_path": path}


@mcp.tool(name="transcribe", description="语音转文字（灵听）")
def tool_transcribe(audio_path: str, backend: str = "") -> dict:
    """将音频文件转为文字。需要 whisper。"""
    from .stt import transcribe_file

    return transcribe_file(audio_path, backend=backend or None)


@mcp.tool(name="council_scan", description="议事厅扫描（灵议）")
def tool_council_scan() -> dict:
    """扫描灵家议事厅状态，返回各成员在线情况和待处理讨论。"""
    from .council import council_scan

    return council_scan()


@mcp.tool(name="council_health", description="议事厅健康检查（灵康）")
def tool_council_health() -> dict:
    """检查灵家议事厅各成员端点健康状态。"""
    from .council import council_health

    return council_health()


# ── 约束层验证（3个工具） ──


@mcp.tool(name="verify_assertion", description="验证断言（灵验）")
def tool_verify_assertion(
    member_id: str,
    assertion_type: str,
    content: str,
    tool_call: dict | None = None,
) -> dict:
    """验证AI成员的断言是否符合约束。

    参数:
        member_id: 成员ID (lingzhi/lingflow/lingresearch)
        assertion_type: 断言类型 (fact/action/communication)
        content: 断言内容
        tool_call: 工具调用信息（可选）

    返回验证结果，包括是否通过、失败原因和改进建议。"""
    from .constraint_layer import Assertion

    constraint = _get_constraint_layer()
    if not constraint:
        return {
            "error": "约束层未初始化",
            "passed": False
        }

    assertion = Assertion(
        member_id=member_id,
        assertion_type=assertion_type,
        content=content,
        tool_call=tool_call
    )

    result = constraint.verify_assertion(assertion)

    return {
        "passed": result.passed,
        "reason": result.reason,
        "checks": result.checks,
        "recommendation": result.recommendation,
        "requires_fallback": result.requires_fallback
    }


@mcp.tool(name="verification_stats", description="验证统计（灵统验）")
def tool_verification_stats(days: int = 7) -> dict:
    """获取验证统计信息。

    参数:
        days: 统计天数（默认7天）

    返回包括总数、通过数、拒绝数、降级数和批准率。"""
    constraint = _get_constraint_layer()
    if not constraint:
        return {
            "error": "约束层未初始化"
        }

    return constraint.get_verification_stats(days)


@mcp.tool(name="verification_log", description="验证日志（灵志）")
def tool_verification_log(days: int = 7, member_id: str = "") -> list[dict]:
    """获取验证日志。

    参数:
        days: 查询天数（默认7天）
        member_id: 按成员ID筛选（可选）

    返回验证日志列表。"""
    from .constraint_layer import VerificationMonitor
    from datetime import datetime

    monitor = VerificationMonitor()
    logs = monitor._load_logs()

    # 筛选时间范围
    cutoff = datetime.now().timestamp() - days * 86400
    recent_logs = [
        log for log in logs
        if datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff
    ]

    # 按成员ID筛选
    if member_id:
        recent_logs = [log for log in recent_logs if log["member_id"] == member_id]

    return recent_logs


def main():
    """stdio transport entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
