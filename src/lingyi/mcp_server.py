"""灵依 MCP Server — 30个核心能力封装为MCP工具。

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


from . import mcp_tools_p0  # noqa: F401, E402


def main():
    """stdio transport entry point."""
    mcp.run()


if __name__ == "__main__":
    main()
