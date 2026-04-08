"""系统提示词缓存与构建。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_CACHE: dict[str, tuple[str, datetime]] = {}
_CACHE_EXPIRE_SECONDS = 300


def _call_llm_with_fallback(client: Any, messages: list, tools_schema: list | None) -> tuple:
    """按优先级尝试模型，429/余额不足时自动降级"""
    from .llm_utils import call_llm_with_fallback as _do_fallback
    from .web_app import _GLM_MODEL
    return _do_fallback(client, messages, tools_schema, primary_model=_GLM_MODEL)


def get_cached_system_prompt() -> str:
    """获取缓存的系统提示词，如果缓存过期则重新构建"""
    from .agent import _SYSTEM_PROMPT_BASE

    cache_key = "system_prompt"
    now = datetime.now()

    if cache_key in _SYSTEM_PROMPT_CACHE:
        cached_prompt, cache_time = _SYSTEM_PROMPT_CACHE[cache_key]
        if (now - cache_time).total_seconds() < _CACHE_EXPIRE_SECONDS:
            return cached_prompt

    prompt = build_system_prompt_impl(_SYSTEM_PROMPT_BASE)
    _SYSTEM_PROMPT_CACHE[cache_key] = (prompt, now)
    return prompt


def build_system_prompt_impl(base_prompt: str) -> str:
    """实际构建系统提示词的实现"""
    parts = [base_prompt, ""]

    parts.append("\n【附加工具能力】除了上面提到的工具，你还拥有以下能力：")
    parts.append("  - file_read: 读取文件内容（带行号，限白名单目录）")
    parts.append("  - git_status: 查看 Git 仓库状态")
    parts.append("  - code_stats: 统计灵字辈项目代码量")
    parts.append("  - search_web: 搜索网络")
    parts.append("  - check_github / check_pypi: 查开源项目数据")
    parts.append("  - ai_news: 获取最新 AI 行业新闻")
    parts.append("")
    parts.append("【灵字辈 GitHub 仓库映射】")
    parts.append("  - 灵通 LingFlow: guangda88/lingflow")
    parts.append("  - 灵克 LingClaude: guangda88/lingclaude")
    parts.append("  - 灵依 LingYi: guangda88/lingyi")
    parts.append("  - 灵知 LingZhi: guangda88/zhineng-knowledge-system")
    parts.append("当灵通老师提到某个灵字辈项目的GitHub时，你应该直接调用 check_github，不要问仓库名。")

    try:
        from .schedule import format_today
        today = format_today()
        if today:
            parts.append("【今日日程】\n" + today)
    except Exception:
        pass

    try:
        from .memo import list_memos
        memos = list_memos()
        if memos:
            recent = memos[:5]
            lines = [f"  - {m.content}" for m in recent]
            parts.append("【最近备忘】\n" + "\n".join(lines))
    except Exception:
        pass

    try:
        from .plan import format_plan_week
        wp = format_plan_week()
        if wp:
            parts.append("【本周计划】\n" + wp)
    except Exception:
        pass

    try:
        from .project import list_projects
        active = list_projects(status="active")
        if active:
            lines = [f"  - {p.name}({p.alias}) {p.priority} [{p.category}]" for p in active]
            parts.append("【活跃项目】\n" + "\n".join(lines))
    except Exception:
        pass

    try:
        from .briefing import collect_all
        briefing_data = collect_all()
        lines = []
        for key, label in [("lingzhi", "灵知"), ("lingflow", "灵通"), ("lingclaude", "灵克"), ("lingtongask", "灵通问道")]:
            info = briefing_data.get(key, {})
            if info.get("available"):
                lines.append(f"  - {label}: 在线")
            else:
                lines.append(f"  - {label}: 离线")
        lingclaude_info = briefing_data.get("lingclaude", {})
        sessions = lingclaude_info.get("sessions", 0)
        if sessions:
            lines.append(f"  - 灵克开发会话: {sessions} 条")
        lingflow_info = briefing_data.get("lingflow", {})
        fb = lingflow_info.get("feedback_count", 0)
        fb_open = lingflow_info.get("feedback_open", 0)
        lines.append(f"  - 灵通反馈: {fb} 条（{fb_open} 条待处理）")
        parts.append("【灵字辈实时状态】（以下为全部数据，没有更多了）\n" + "\n".join(lines))
    except Exception:
        pass

    try:
        from .lingmessage import list_discussions
        discussions = list_discussions(status="open")
        if discussions:
            lines = []
            for d in discussions[:5]:
                participants = ", ".join(d.get("participants", []))
                msg_count = d.get("message_count", 0)
                lines.append(f"  - {d['topic']} (参与者: {participants}, {msg_count}条消息)")
            parts.append("【灵信待处理讨论】\n" + "\n".join(lines))
    except Exception:
        pass

    return "\n\n".join(parts)
