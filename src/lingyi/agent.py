from __future__ import annotations

"""灵依 Agent — 统一通信层。

不是简单的 LLM wrapper，而是灵依的真正大脑：
- 关键词快捷路由（备忘、日程、计划...）
- LLM + function calling（查 GitHub、查 PyPI、搜灵信...）
- 情报收集（灵字辈生态状态）
- 灵信读写（跨项目协作）
"""

import json
import logging
import os
import re
import urllib.request
from typing import Any, Callable

logger = logging.getLogger(__name__)

_DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

_ToolFn = Callable[..., str]


# ── Tool definitions for qwen function calling ──────────────────────

_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "check_github",
            "description": "查询 GitHub 仓库信息：stars、forks、issues、最新 release。输入格式：owner/repo（如 guangda88/lingflow）",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub 仓库全名，格式 owner/repo",
                    }
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_pypi",
            "description": "查询 PyPI 包的版本和下载量信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "PyPI 包名（如 lingflow-core）",
                    }
                },
                "required": ["package"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_memos",
            "description": "列出最近的备忘录",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_memo",
            "description": "添加一条备忘录",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "备忘内容",
                    }
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_schedule",
            "description": "查看今日或本周日程安排",
            "parameters": {
                "type": "object",
                "properties": {
                    "range": {
                        "type": "string",
                        "enum": ["today", "week"],
                        "description": "查看范围：today 或 week",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_plans",
            "description": "查看计划列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "领域筛选（医疗/编程/研究/论文/学术），空字符串表示全部",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "查看灵字辈项目列表和状态",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_briefing",
            "description": "收集灵字辈生态实时状态（灵知/灵通/灵克/灵通问道的服务状态、数据统计）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lingmessage",
            "description": "查看灵信中最近的讨论线程",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "closed"],
                        "description": "筛选状态：open 或 closed，空字符串表示全部",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_lingmessage",
            "description": "读取灵信中某个讨论的完整内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_id": {
                        "type": "string",
                        "description": "讨论 ID",
                    }
                },
                "required": ["discussion_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索网络获取最新信息（AI新闻、技术动态等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patrol_projects",
            "description": "巡检所有灵字辈 Git 项目的状态（最近提交、未暂存变更、分支）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tool implementations ────────────────────────────────────────────


def _check_github(repo: str) -> str:
    try:
        url = f"https://api.github.com/repos/{repo}"
        req = urllib.request.Request(url, headers={"User-Agent": "LingYi/0.15"})
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
        req = urllib.request.Request(url, headers={"User-Agent": "LingYi/0.15"})
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
            req2 = urllib.request.Request(stats_url, headers={"User-Agent": "LingYi/0.15"})
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
        from urllib.parse import quote_plus
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LingYi)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        results = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</[at]', html)
        clean = lambda t: re.sub(r'<[^>]+>', '', t).strip()
        lines = []
        for i in range(min(5, len(results))):
            title = clean(results[i]) if i < len(results) else ""
            snippet = clean(snippets[i]) if i < len(snippets) else ""
            lines.append(f"{i+1}. {title}\n   {snippet}")
        return "\n".join(lines) if lines else "未找到相关结果。"
    except Exception as e:
        return f"搜索失败: {e}"


def _patrol_projects() -> str:
    try:
        from .patrol import generate_report
        return generate_report()
    except Exception as e:
        return f"巡检失败: {e}"


_TOOL_MAP: dict[str, _ToolFn] = {
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


# ── Quick-route shortcuts (no LLM needed) ───────────────────────────


def _quick_route(text: str) -> str | None:
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


# ── System prompt builder ───────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """\
你是灵依 (LingYi)，灵字辈 (Ling Family) 智能体家族的管家助理。你不是通用聊天机器人——你是灵通老师的私人助理，是这个家族中负责日常事务、信息协调和贴心陪伴的角色。

## 你的身份

- 你是灵依，灵字辈中最贴近用户生活的成员
- 你的性格：温暖但不谄媚，简洁但不敷衍，有自己的判断力
- 你说中文，语气像一位靠谱的朋友，偶尔可以轻松幽默
- 不用 emoji，不堆砌客套话

## 你的用户：灵通老师

灵通老师是你的创建者和使用者。他是一位在 AI、开源软件和气功领域都有深厚积累的研究者。

他的核心兴趣：
- AI 编程助手（他创建了灵克 LingClaude，一个对标 Claude Code 的开源项目）
- 气功与意识科学研究
- 开源项目生态建设
- 产品设计和用户体验

他和你的关系：你是他最常对话的 AI，他会在手机上随时找你聊天、问问题、记备忘、安排日程。

## 灵字辈家族成员

你了解以下家族成员，知道它们各自的角色和渊源：

- **灵通 (LingFlow)** — 灵字辈的起点和奠基者，最早的灵字辈项目。工作流引擎和工程平台，也是灵字辈生态的基础设施。
- **灵极优 (LingMinOpt)** — 自优化框架。灵通和灵极优一起开发孵化了灵字辈的众多成员项目。
- **灵克 (LingClaude)** — AI 编程助手，对标 Claude Code，差异化优势是内置自优化。运行在终端里，帮灵通老师写代码、分析项目、执行工程任务。
- **灵依 (LingYi)** — 就是你。灵字辈的管家助理和情报中枢，负责日常事务、信息协调和贴心陪伴。
- **灵扬 (LingYang)** — 市场推广和传播助手，负责灵字辈项目的对外发声（Hacker News、Reddit、邮件等）。
- **灵信 (LingMessage)** — 灵字辈之间的通讯协议，一个异步消息系统。灵克、灵依等通过灵信邮箱互相传递信息和协作。
- **灵通问道 (LingTongAsk)** — AI 课程视频生成工具，从 Markdown 教案生成完整的演示文稿和视频。
- **灵知 (LingZhi)** — 知识库系统，提供知识查询服务。
- **灵研 (LingResearch)** — 科研优化工具。
- **灵犀 (LingTerm)** — 终端感知 MCP 服务。

灵通老师在灵字辈生态中的角色：他创建并主导了整个灵字辈家族。灵通（LingFlow）是起点，和灵极优一起孵化了后续所有项目。灵克在工程上实现功能，灵依（你）负责日常协调和陪伴。灵信是大家协作的通讯 backbone。

## 你能做什么

你有工具可以执行真实操作，不是在编造信息：
- 查 GitHub 仓库（stars、forks、issues）
- 查 PyPI 包信息（版本、下载量）
- 查看/添加备忘录
- 查看日程安排
- 查看计划进度
- 查看灵字辈项目状态
- 收集灵字辈生态实时情报
- 读取灵信讨论
- 搜索网络
- 巡检 Git 项目

## 对话原则

1. 有工具就用工具，不要猜答案。问你 stars 数就去查 GitHub，问你下载量就去查 PyPI。
2. 保持简洁：一两句话说清楚就够了，不需要长篇大论。
3. 主动帮忙：灵通老师提到一个想法或问题，想想能用什么工具帮他。
4. 尊重专业性：灵通老师在这些领域比你资深得多，你是助手不是老师。

## 最重要：绝对不许编造

- 只使用工具返回的真实数据。如果工具没查到，就是没有。
- 不知道就说不知道，不要编造任何数字、链接或细节。
- 不要建议"帮你整理成文档"来回避问题。没有就没有。
"""


def _build_system_prompt() -> str:
    from .voicecall import _build_system_prompt as _orig
    return _orig()


# ── Main agent loop ─────────────────────────────────────────────────


def process_message(text: str, conversation: list[dict]) -> str:
    """处理用户消息 — 快捷路由优先，否则走 LLM + tool calling。"""

    quick = _quick_route(text)
    if quick:
        return quick

    return _agent_loop(text, conversation)


def _agent_loop(text: str, conversation: list[dict]) -> str:
    """LLM agent loop: call qwen with tools, execute, return result."""
    import dashscope
    from dashscope import Generation

    dashscope.api_key = _DASHSCOPE_API_KEY

    system_prompt = _SYSTEM_PROMPT_BASE
    messages = [{"role": "system", "content": system_prompt}] + conversation[-20:]
    messages.append({"role": "user", "content": text})

    max_rounds = 5
    for _ in range(max_rounds):
        try:
            resp = Generation.call(
                model="qwen-plus",
                messages=messages,
                tools=_TOOLS,
                result_format="message",
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "抱歉，暂时无法处理。"

        if resp.status_code != 200:
            logger.warning(f"Qwen call failed: {resp.status_code}")
            return "抱歉，暂时无法处理。"

        choice = resp.output.get("choices", [{}])[0]
        assistant_msg = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "")

        if finish_reason != "tool_calls":
            content = assistant_msg.get("content", "")
            return content.strip() if content else "嗯，我刚才走神了，你再说一遍？"

        messages.append(assistant_msg)

        tool_calls = assistant_msg.get("tool_calls", [])
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args_str = tc["function"].get("arguments", "{}")
            try:
                fn_args = json.loads(fn_args_str)
            except json.JSONDecodeError:
                fn_args = {}

            tool_fn = _TOOL_MAP.get(fn_name)
            if tool_fn:
                logger.info(f"[TOOL] {fn_name}({fn_args})")
                result = tool_fn(**fn_args)
            else:
                result = f"未知工具: {fn_name}"

            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tc.get("id", ""),
            })

    return "处理轮次超限，请简化问题再试。"
