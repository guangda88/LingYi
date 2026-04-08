"""聊天 LLM 逻辑：工具调用循环、智能回复。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from ._web_app_prompt import get_cached_system_prompt, _call_llm_with_fallback

logger = logging.getLogger(__name__)


def chat_llm_with_context(text: str, conv: list[dict] | None = None, glm_api_key: str = "", glm_base_url: str = "", glm_model: str = "") -> str:
    from openai import OpenAI
    from .tools import get_tools, execute_tool

    logger.info(f"Starting chat with text: {text[:50]}...")
    try:
        client = OpenAI(api_key=glm_api_key, base_url=glm_base_url, max_retries=0)
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return f"⚠️ 无法连接到AI服务：{str(e)}"

    try:
        system_prompt = get_cached_system_prompt()
        context = conv if conv is not None else []
        messages = [{"role": "system", "content": system_prompt}] + context[-20:]
        tools_schema = get_tools()
        logger.info(f"System prompt length: {len(system_prompt)}, context messages: {len(context)}, tools: {len(tools_schema)}")
    except Exception as e:
        logger.error(f"Failed to build prompt: {e}")
        return f"⚠️ 构建提示词失败：{str(e)}"

    _err_count = 0
    for attempt in range(5):
        logger.info(f"Attempt {attempt + 1}/5...")
        try:
            resp, _used_model = _call_llm_with_fallback(client, messages, tools_schema)
            logger.info(f"Got response from model: {_used_model}")

            if not resp.choices or len(resp.choices) == 0:
                logger.error(f"Empty response from model: {resp}")
                continue

            choice = resp.choices[0]
            msg = choice.message

            if msg.tool_calls:
                logger.info(f"Tool calls detected: {len(msg.tool_calls)} tools")
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    logger.info(f"Executing tool: {tool_name}")
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    try:
                        result = execute_tool(tool_name, args)
                        logger.info(f"Tool {tool_name} result length: {len(result)}")
                    except Exception as e:
                        logger.error(f"Tool {tool_name} execution failed: {e}")
                        result = f"工具执行失败: {str(e)}"
                    messages.append({"role": "assistant", "content": None, "tool_calls": [{
                        "id": tc.id, "type": "function",
                        "function": {"name": tool_name, "arguments": tc.function.arguments}
                    }]})
                    messages.append({"role": "tool", "content": result,
                                    "tool_call_id": tc.id, "name": tool_name})
                continue

            content = msg.content or ""
            if content:
                logger.info(f"Got response content, length: {len(content)}")
                return content.strip()
            else:
                logger.warning(f"Empty content in message: {msg}")
                continue
        except Exception as e:
            _err_count += 1
            logger.error(f"GLM call failed (attempt {attempt + 1}, error {_err_count}): {type(e).__name__}: {e}")
            if _err_count >= 3:
                from .llm_utils import friendly_error
                return friendly_error(e)
            time.sleep(2 * _err_count)
            continue
    return "⚠️ AI 服务暂时不可用，请稍后再试。"


async def smart_reply(text: str, conv: list[dict] | None = None, **llm_kwargs: Any) -> str:
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: chat_llm_with_context(text, conv, **llm_kwargs)),
            timeout=60,
        )
    except asyncio.TimeoutError:
        logger.warning("_smart_reply timed out after 60s")
        return "⚠️ AI 响应超时，请稍后再试。"


def yi_discuss_sync(topic: str, context: str, question: str, glm_api_key: str, glm_base_url: str) -> dict:
    from openai import OpenAI

    YI_IDENTITY = (
        "你是灵依，灵字辈大家庭的私人AI助理和情报中枢。"
        "你的专长是用户需求洞察、情报整合、跨服务协调、日程管理。"
        "你是灵家议事厅的客厅管理员，负责统筹讨论节奏和成员协作。"
        "讨论风格：统筹、用户视角，关注情报整合和用户需求。"
        "每条消息必须有实质内容。反对须附理由和替代方案。保持200-500字。"
        "你现在在灵家议事厅（客厅）参与讨论。直接发表你的观点。"
        "\n[语音转录容错] 用户输入可能来自语音转录，存在同音字/近音字错误。"
        "你必须理解真实语义，不要被字面错误误导。"
        "常见映射：林克=灵克、零字辈=灵字辈、林依=灵依、做/作、的/得/地、在/再。"
        "理解时以语义为准，回复时用正确的字词。不要纠正用户，直接理解并回复。"
    )

    if not glm_api_key:
        return {"content": "", "model_used": "error", "source_type": "real"}

    prompt_parts = [YI_IDENTITY, "", f"当前议题：「{topic}」"]
    if context:
        prompt_parts.append(f"\n已有的讨论内容：\n{context[:3000]}\n")
        prompt_parts.append(
            "\n【要求】你必须：\n"
            "1. 引用之前某位发言者的具体论点（用「XX说……」的方式引用）\n"
            "2. 对该论点明确表态（同意/反对/补充），并给出你自己的理由\n"
            "3. 提出至少一个前人没有提到的新角度或新论据\n"
            "4. 不要重复已有讨论中说过的内容，不要泛泛而谈\n"
        )
    if question:
        prompt_parts.append(f"请回答：{question}")
    else:
        prompt_parts.append("请从你的角度——情报中枢和用户需求的角度——发表意见。")
    prompt = "\n".join(prompt_parts)

    try:
        client = OpenAI(api_key=glm_api_key, base_url=glm_base_url)
        resp, model_used = _call_llm_with_fallback(
            client, [{"role": "user", "content": prompt}], None
        )
        content = (resp.choices[0].message.content or "").strip()
        if content:
            return {"content": content, "model_used": model_used, "source_type": "real"}
    except Exception as e:
        logger.error(f"灵依讨论失败: {e}")
    return {"content": "", "model_used": "error", "source_type": "real"}
