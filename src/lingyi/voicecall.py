"""语音通话 — 像打电话一样和灵依实时对话。

流程：VAD监听(说完了自动停止) → STT转文字 → AI生成回复 → TTS朗读 → 循环
"""

import json
import logging
from pathlib import Path

from .llm_utils import create_client, call_llm_with_fallback, friendly_error

from ._voicecall_audio import (
    _check_dependencies, _record_with_vad, _transcribe, _synthesize_and_play,
    _SILENCE_LIMIT,
)
from ._voicecall_prompt import _build_system_prompt

logger = logging.getLogger(__name__)

_GLM_MODEL = "glm-4.5-air"


def _chat_llm(conversation: list[dict]) -> str:
    """用 GLM 生成对话回复，支持 function calling。"""
    from .tools import get_tools, execute_tool

    client = create_client()
    system_prompt = _build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + conversation[-20:]
    tools = get_tools()

    try:
        resp, _model_used = call_llm_with_fallback(client, messages, tools=tools)
    except Exception as e:
        logger.warning(f"GLM call failed: {e}")
        return friendly_error(e)

    choice = resp.choices[0]
    msg = choice.message

    if msg.content:
        return msg.content.strip()

    if not msg.tool_calls:
        return ""

    messages.append({"role": "assistant", "content": None,
                     "tool_calls": [{"id": tc.id, "type": "function",
                                     "function": {"name": tc.function.name,
                                                   "arguments": tc.function.arguments}}
                                    for tc in msg.tool_calls]})

    results = []
    for tc in msg.tool_calls:
        fn = tc.function
        name = fn.name
        try:
            args = json.loads(fn.arguments or "{}")
        except Exception:
            args = {}
        logger.info(f"[工具调用] {name}({args})")
        result = execute_tool(name, args)
        logger.info(f"[工具结果] {result[:100]}")
        results.append(result)
        messages.append({
            "role": "tool",
            "content": result,
            "tool_call_id": tc.id,
        })

    try:
        resp2 = client.chat.completions.create(
            model=_GLM_MODEL,
            messages=messages,
            tools=tools,
        )
        if resp2.choices and resp2.choices[0].message.content:
            return resp2.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"GLM second call failed: {e}")

    return "\n".join(results)


def _generate_reply(text: str, conversation: list[dict]) -> str:
    """生成回复。快捷操作指令优先，其余走 Qwen 对话。"""
    text_lower = text.lower()

    if text_lower.startswith(("备忘", "记一下", "提醒我")):
        content = text
        for kw in ("备忘", "记一下", "提醒我", "帮我"):
            content = content.replace(kw, "", 1)
        content = content.strip()
        if content:
            from .memo import add_memo
            add_memo(content)
            return f"已记录：{content}"
        return "你想记什么？"

    if any(kw in text_lower for kw in ("再见", "拜拜", "挂了", "挂电话", "结束",
                                        "晚安", "下次聊", "先走了")):
        return "好的，再见！随时找我聊。"

    reply = _chat_llm(conversation)
    if reply:
        return reply

    return "嗯，我刚才走神了，你再说一遍？"


def voice_call(voice: str = "zh-CN-XiaoxiaoNeural",
               silence_limit: float = _SILENCE_LIMIT) -> None:
    """启动语音通话循环。

    Args:
        voice: TTS语音角色
        silence_limit: VAD静音检测阈值（秒），说完多久后自动识别
    """
    deps = _check_dependencies()
    missing = [k for k, v in deps.items() if not v]

    if missing:
        labels = {"vad": "语音活动检测(webrtcvad)", "stt": "语音识别(whisper)",
                  "tts": "语音合成(edge-tts)", "record": "录音(arecord)"}
        print("缺少依赖：")
        for m in missing:
            print(f"  - {labels.get(m, m)}")
        return

    print("📞 灵依语音通话")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("说话即可，说完自动识别回复")
    print("说'再见'或'挂了'结束通话")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    conversation: list[dict] = []

    try:
        import whisper
        print("⏳ 正在加载语音模型...")
        whisper.load_model("base")
        print("✅ 模型就绪，开始通话！")
        print()
    except ImportError:
        pass

    try:
        while True:
            print("🎤 [等待说话...]")
            audio_path = _record_with_vad(silence_limit=silence_limit)
            if audio_path is None:
                continue

            try:
                user_text = _transcribe(audio_path)
            except Exception as e:
                logger.debug(f"转录失败: {e}")
                print("⚠ 识别失败，请再说一次")
                continue
            finally:
                Path(audio_path).unlink(missing_ok=True)

            if not user_text:
                continue

            print(f"你：{user_text}")

            conversation.append({"role": "user", "content": user_text})

            if any(kw in user_text for kw in ("再见", "拜拜", "挂了", "挂电话", "结束通话")):
                reply = "好的，再见！随时找我聊。"
                print(f"灵依：{reply}")
                _synthesize_and_play(reply, voice=voice)
                break

            reply = _generate_reply(user_text, conversation)
            print(f"灵依：{reply}")

            conversation.append({"role": "assistant", "content": reply})

            print("🔊 [朗读中...]")
            _synthesize_and_play(reply, voice=voice)

    except KeyboardInterrupt:
        print("\n\n📞 通话结束，再见！")


def check_voice_call() -> dict:
    """检查语音通话功能是否可用。"""
    return _check_dependencies()


def format_voice_call_status(deps: dict) -> str:
    """格式化语音通话状态。"""
    labels = {"vad": "语音活动检测 (webrtcvad)", "stt": "语音识别 (whisper)",
              "tts": "语音合成 (edge-tts)", "record": "录音 (arecord)"}

    all_ok = all(deps.values())
    if all_ok:
        lines = ["📞 语音通话就绪"]
        for k, v in deps.items():
            lines.append(f"  ✅ {labels.get(k, k)}")
        return "\n".join(lines)

    lines = ["📞 语音通话 — 部分组件缺失"]
    for k, v in deps.items():
        icon = "✅" if v else "❌"
        lines.append(f"  {icon} {labels.get(k, k)}")
    return "\n".join(lines)
