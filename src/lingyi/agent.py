from __future__ import annotations

import json
import logging
import os
from typing import Callable

from .llm_utils import create_client, call_llm_with_fallback, friendly_error
from .agent_tools import TOOL_MAP as _TOOL_MAP, quick_route as _quick_route  # noqa: F401
from ._agent_schemas import _TOOLS

logger = logging.getLogger(__name__)

_DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

_ToolFn = Callable[..., str]


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


def process_message(text: str, conversation: list[dict]) -> str:
    """处理用户消息 — 快捷路由优先，否则走 LLM + tool calling。"""

    quick = _quick_route(text)
    if quick:
        return quick

    return _agent_loop(text, conversation)


def _extract_text_from_messages(messages: list[dict]) -> str:
    """Extract the best text content from conversation messages for partial results."""
    for msg in reversed(messages):
        content = msg.get("content")
        role = msg.get("role", "")
        if content and role == "assistant":
            return content.strip()
    return ""


def _agent_loop(text: str, conversation: list[dict]) -> str:
    """LLM agent loop: call GLM with tools, execute, return result."""
    client = create_client()

    system_prompt = _SYSTEM_PROMPT_BASE
    messages = [{"role": "system", "content": system_prompt}] + conversation[-20:]
    messages.append({"role": "user", "content": text})

    max_rounds = 10
    for round_idx in range(max_rounds):
        try:
            resp, _model_used = call_llm_with_fallback(client, messages, tools=_TOOLS)
        except Exception as e:
            logger.error(f"LLM call failed (round {round_idx + 1}): {e}")
            if round_idx >= 2:
                _partial = _extract_text_from_messages(messages)
                if _partial:
                    return _partial + "\n\n⚠️ 部分结果（LLM调用中途失败）"
            return friendly_error(e)

        choice = resp.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            content = msg.content or ""
            return content.strip() if content else "⚠️ AI服务无响应，请稍后再试。"

        messages.append({"role": "assistant", "content": None,
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name,
                                                       "arguments": tc.function.arguments}}
                                        for tc in msg.tool_calls]})

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args_str = tc.function.arguments or "{}"
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
                "tool_call_id": tc.id,
            })

    _partial = _extract_text_from_messages(messages)
    if _partial:
        return _partial + "\n\n⚠️ 处理轮次较多，以上是已收集的结果。"
    return "处理轮次超限，请稍后再试。"
