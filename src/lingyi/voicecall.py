"""语音通话 — 像打电话一样和灵依实时对话。

流程：VAD监听(说完了自动停止) → STT转文字 → AI生成回复 → TTS朗读 → 循环
"""

import importlib.util
import json
import logging
import os
import subprocess
import tempfile
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

_SILENCE_LIMIT = 1.2
_MAX_RECORD_SEC = 30
_SAMPLE_RATE = 16000
_CHANNELS = 1
_FRAME_DURATION = 30
_VAD_AGGRESSIVENESS = 3


def _check_dependencies() -> dict:
    deps = {"vad": False, "stt": False, "tts": False, "record": False}

    if importlib.util.find_spec("webrtcvad") is not None:
        deps["vad"] = True
    if importlib.util.find_spec("whisper") is not None:
        deps["stt"] = True
    if importlib.util.find_spec("edge_tts") is not None:
        deps["tts"] = True

    try:
        subprocess.run(["arecord", "--version"], capture_output=True, timeout=3)
        deps["record"] = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return deps


def _record_with_vad(silence_limit: float = _SILENCE_LIMIT,
                     max_duration: float = _MAX_RECORD_SEC) -> str | None:
    """使用 VAD 录音：检测到说话开始，说完自动停止。

    Returns:
        WAV 文件路径，失败返回 None
    """
    import webrtcvad

    vad = webrtcvad.Vad(_VAD_AGGRESSIVENESS)
    frame_size = int(_SAMPLE_RATE * _FRAME_DURATION / 1000)

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    import os
    os.close(fd)

    try:
        proc = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", str(_SAMPLE_RATE),
             "-c", str(_CHANNELS), "-t", "raw", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return None

    frames: list[bytes] = []
    has_speech = False
    silence_start = None
    total_frames = 0
    max_frames = int(_SAMPLE_RATE / frame_size * max_duration)

    try:
        while total_frames < max_frames:
            raw = proc.stdout.read(frame_size * 2)
            if not raw or len(raw) < frame_size * 2:
                break

            total_frames += 1
            is_speech = vad.is_speech(raw, _SAMPLE_RATE)

            if is_speech:
                frames.append(raw)
                has_speech = True
                silence_start = None
            elif has_speech:
                frames.append(raw)
                if silence_start is None:
                    silence_start = total_frames
                elif (total_frames - silence_start) * _FRAME_DURATION / 1000 >= silence_limit:
                    break
            if not has_speech and total_frames * _FRAME_DURATION / 1000 > 5:
                break
    except Exception as e:
        logger.debug(f"VAD录音异常: {e}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not has_speech or not frames:
        Path(wav_path).unlink(missing_ok=True)
        return None

    try:
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return wav_path
    except Exception as e:
        logger.debug(f"写WAV失败: {e}")
        Path(wav_path).unlink(missing_ok=True)
        return None


def _transcribe(audio_path: str) -> str:
    """使用 whisper 转录。"""
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="zh")
    return result.get("text", "").strip()


def _synthesize_and_play(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bool:
    """TTS 合成并播放。"""
    from .tts import speak, clean_text_for_speech
    return speak(clean_text_for_speech(text), voice=voice)


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

你和灵克之间通过灵信（LingMessage）协作：灵克会把开发进展、代码审查结果、项目发现通过灵信告诉你，你也要能把灵通老师的日常需求和反馈传达给灵克。

## 你能做什么

- 日常聊天、问答、头脑风暴
- 记录备忘、查看日程、跟踪计划
- 项目进度追踪和状态汇总
- 把灵通老师的需求和想法转达给灵克（通过灵信）
- 用温暖的语气陪伴，但遇到技术问题也能给出实在的分析

## 对话原则

1. 理解上下文：灵通老师会聊到他的项目、灵字辈、气功研究等，你都要能接住
2. 保持简洁：一两句话说清楚就够了，不需要长篇大论
3. 主动帮忙：如果灵通老师提到一个想法或问题，想想能不能帮他记录、追踪或转达
4. 尊重专业性：灵通老师在这些领域比你资深得多，你是助手不是老师

## 最重要：绝对不许编造

这是你和其他 AI 最大的区别。你必须像一个真正了解内情的人一样回答，而不是像一个在猜答案的机器人。

- 只使用下方【实时数据】中提供的信息。如果数据里没有，就是没有。
- 绝不编造用户反馈、项目数据、链接、统计数据或任何具体细节。
- 不知道就直说"目前没有这方面的数据"或"我不太确定，要不要让灵克查一下"。
- 如果灵通老师问你要链接或具体数据，而你手里没有，直接说没有，不要转移话题、不要建议"帮你整理成文档"来回避。
- 灵字辈项目目前都是内部开发阶段，还没有对外发布，所以没有外部用户反馈。灵克的"会话"是灵通老师自己的开发会话记录，不是用户反馈。
"""


def _build_system_prompt() -> str:
    parts = [_SYSTEM_PROMPT_BASE, ""]

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
            lines = [f"  - {p.name}({p.priority})" for p in active]
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
            lines.append(f"  - 灵克开发会话: {sessions} 条（灵通老师自己的开发记录，非外部用户）")
        lingflow_info = briefing_data.get("lingflow", {})
        fb = lingflow_info.get("feedback_count", 0)
        fb_open = lingflow_info.get("feedback_open", 0)
        lines.append(f"  - 灵通反馈: {fb} 条（{fb_open} 条待处理）")
        lingtongask_info = briefing_data.get("lingtongask", {})
        comments = lingtongask_info.get("total_comments", 0)
        users = lingtongask_info.get("unique_users", 0)
        lines.append(f"  - 灵通问道: {comments} 条评论, {users} 个用户")
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
                updated = d.get("updated_at", "")[:16].replace("T", " ")
                lines.append(f"  - {d['topic']} (参与者: {participants}, {msg_count}条消息, 更新: {updated})")
            parts.append("【灵信待处理讨论】\n" + "\n".join(lines))
    except Exception:
        pass

    return "\n\n".join(parts)

_DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY", "sk-87b60796471c4596bcd7278d4ac12dfe"
)


def _chat_llm(conversation: list[dict]) -> str:
    """用通义千问生成对话回复，支持 function calling。"""
    import dashscope
    from dashscope import Generation
    from .tools import get_tools, execute_tool

    dashscope.api_key = _DASHSCOPE_API_KEY
    system_prompt = _build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + conversation[-20:]
    tools = get_tools()

    resp = Generation.call(
        model="qwen-turbo",
        messages=messages,
        tools=tools,
        result_format="message",
    )

    if resp.status_code != 200:
        logger.warning(f"Qwen call failed: {resp.status_code}")
        return ""

    choices = resp.output.get("choices", [])
    if not choices:
        return ""

    msg = choices[0]["message"]

    if msg.get("content"):
        return msg["content"].strip()

    tool_calls = msg.get("tool_calls", [])
    if not tool_calls:
        return ""

    messages.append(msg)
    results = []
    for tc in tool_calls:
        fn = tc["function"]
        name = fn["name"]
        try:
            args = json.loads(fn["arguments"])
        except Exception:
            args = {}
        logger.info(f"[工具调用] {name}({args})")
        result = execute_tool(name, args)
        logger.info(f"[工具结果] {result[:100]}")
        results.append(result)
        messages.append({
            "role": "tool",
            "content": result,
            "tool_call_id": tc.get("id", ""),
            "name": name,
        })

    resp2 = Generation.call(
        model="qwen-turbo",
        messages=messages,
        tools=tools,
        result_format="message",
    )
    if resp2.status_code == 200:
        choices2 = resp2.output.get("choices", [])
        if choices2 and choices2[0]["message"].get("content"):
            return choices2[0]["message"]["content"].strip()

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
