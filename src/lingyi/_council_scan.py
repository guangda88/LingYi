"""灵家议事厅扫描逻辑 — 讨论判断、扫描、健康检查。"""

import json
import logging
from typing import Optional

from .lingmessage import (
    PROJECTS, _ensure_store, _load_index, _load_discussion,
    _project_name, _now,
)
from .llm_utils import create_client, call_llm_with_fallback
from ._council_config import (
    MEMBER_ENDPOINTS, _load_state, _save_state,
)
from ._council_member import wake_member

logger = logging.getLogger(__name__)


def _judge_discussion_with_llm(disc: dict) -> Optional[dict]:
    """灵依用LLM判断讨论状态和下一步。只建议有真实端点的在线成员。"""
    topic = disc.get("topic", "")
    messages_list = disc.get("messages", [])
    participants = disc.get("participants", [])

    context_parts = []
    for msg in messages_list[-10:]:
        sender = msg.get("from_name", "?")
        content = msg.get("content", "")[:200]
        context_parts.append(f"【{sender}】{content}")

    online_members = list(MEMBER_ENDPOINTS.keys())
    system_prompt = (
        "你是灵依，灵家议事厅的客厅管理员。你的任务是判断当前讨论的状态。\n"
        "请用JSON格式回答：\n"
        '{"should_continue": true/false, "next_speakers": ["member_id1", "member_id2"], '
        '"reason": "判断理由", "consensus_reached": true/false}\n'
        "判断标准：\n"
        "- 如果讨论已经充分（各方观点已表达，无新论点），consensus_reached=true\n"
        "- 如果还需要更多人发言，should_continue=true，列出next_speakers\n"
        "- 如果讨论空洞、跑题、或成员在重复相同观点，should_continue=false\n"
        "- 每个成员最多发言2次，已经发言2次的成员不要再推荐\n"
        "- 讨论总消息数超过12条时应倾向于结束\n"
        "- 只有以下成员在线且有真实端点，只能从这些成员中选择: "
        + ", ".join(online_members)
    )

    user_msg = (
        f"议题：「{topic}」\n"
        f"参与者：{', '.join(participants)}\n"
        f"消息数：{len(messages_list)}\n\n"
        f"讨论内容：\n{chr(10).join(context_parts)}"
    )

    try:
        client = create_client()
        resp, _model_used = call_llm_with_fallback(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        content = resp.choices[0].message.content or ""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(content)
        if not isinstance(result, dict):
            return None
        result.setdefault("should_continue", False)
        result.setdefault("next_speakers", [])
        result.setdefault("reason", "")
        result.setdefault("consensus_reached", False)
        return result
    except Exception as e:
        logger.error(f"灵依判断讨论状态失败: {e}")
        return None


def council_scan() -> dict:
    """扫描灵信存储，处理需要唤醒的讨论。"""
    state = _load_state()
    store = _ensure_store()
    index = _load_index(store)

    results = {
        "scanned_at": _now(),
        "open_discussions": 0,
        "woken_members": [],
        "real_calls": [],
        "errors": [],
    }

    open_discs = [d for d in index if d.get("status") == "open"]
    results["open_discussions"] = len(open_discs)

    for entry in open_discs:
        disc_id = entry.get("id") or entry.get("thread_id", "")
        if not disc_id:
            continue

        disc = _load_discussion(store, disc_id)
        if not disc:
            continue

        messages = disc.get("messages", [])
        if not messages:
            continue

        auto_reply_count = sum(1 for m in messages if "auto_reply" in m.get("tags", []))
        if auto_reply_count >= 10:
            logger.info(f"跳过讨论 '{disc.get('topic', '')[:30]}' — 已有 {auto_reply_count} 条自动回复")
            continue

        if "auto_reply" in messages[-1].get("tags", []):
            continue

        recent_auto_chain = 0
        last_auto_member = None
        for m in reversed(messages[-5:]):
            if "auto_reply" in m.get("tags", []):
                if last_auto_member is None:
                    last_auto_member = m.get("from_id")
                    recent_auto_chain = 1
                elif m.get("from_id") == last_auto_member:
                    recent_auto_chain += 1
                else:
                    last_auto_member = m.get("from_id")
                    recent_auto_chain = 1
            else:
                break
        if recent_auto_chain >= 3:
            logger.info(f"讨论 '{disc.get('topic', '')[:30]}' 末尾已有 {recent_auto_chain} 条同一成员的连续自动回复，暂停唤醒")
            continue

        last_msg_time = messages[-1].get("timestamp", "")
        if state.last_scan_time and last_msg_time <= state.last_scan_time:
            continue

        last_msg_from = messages[-1].get("from_id", "")
        if last_msg_from == "lingyi" and len(messages) > 1:
            prev_from = messages[-2].get("from_id", "")
            if prev_from == "lingyi":
                continue

        if last_msg_from in ("user", "lingyi") or last_msg_from not in PROJECTS:
            judgment = _judge_discussion_with_llm(disc)
            if judgment and judgment.get("should_continue"):
                next_speakers = judgment.get("next_speakers", [])
                for speaker_id in next_speakers[:3]:
                    reply = wake_member(speaker_id, disc_id)
                    if reply:
                        from .lingmessage import send_message
                        send_message(
                            from_id=speaker_id,
                            topic=disc["topic"],
                            content=reply,
                            source_type="real",
                        )
                        member_name = _project_name(speaker_id)
                        results["woken_members"].append(member_name)
                        results["real_calls"].append(member_name)
                    elif MEMBER_ENDPOINTS.get(speaker_id, {}).get("notify_only"):
                        member_name = _project_name(speaker_id)
                        results["real_calls"].append(f"{member_name}(notified)")
            elif judgment and judgment.get("consensus_reached"):
                logger.info(f"讨论 '{disc['topic']}' 已达成共识，可进入表决")
        else:
            judgment = _judge_discussion_with_llm(disc)
            if judgment and judgment.get("should_continue"):
                current_participants = set(
                    m.get("from_id", "") for m in messages
                )
                next_speakers = judgment.get("next_speakers", [])
                for speaker_id in next_speakers[:2]:
                    if speaker_id not in current_participants:
                        reply = wake_member(speaker_id, disc_id)
                        if reply:
                            from .lingmessage import send_message
                            send_message(
                                from_id=speaker_id,
                                topic=disc["topic"],
                                content=reply,
                                source_type="real",
                            )
                            member_name = _project_name(speaker_id)
                            results["woken_members"].append(member_name)
                            results["real_calls"].append(member_name)
                        elif MEMBER_ENDPOINTS.get(speaker_id, {}).get("notify_only"):
                            member_name = _project_name(speaker_id)
                            results["real_calls"].append(f"{member_name}(notified)")

    state.last_scan_time = _now()
    state.wake_count += len(results["woken_members"])
    state.discussions_monitored = results["open_discussions"]
    _save_state(state)

    for entry in open_discs:
        disc_id = entry.get("id") or entry.get("thread_id", "")
        if not disc_id:
            continue
        disc = _load_discussion(store, disc_id)
        if disc:
            scan_alerts = _check_discussion_health(disc_id, disc)
            for alert in scan_alerts:
                logger.warning(f"🏥 {alert}")

    return results


def _check_discussion_health(disc_id: str, disc: dict) -> list[str]:
    """检查单个讨论的健康状态，返回告警列表。"""
    alerts = []
    messages = disc.get("messages", [])
    topic = disc.get("topic", "?")[:30]
    status = disc.get("status", "open")

    if status != "open":
        return alerts

    if not messages:
        return alerts

    total = len(messages)
    auto_count = sum(1 for m in messages if "auto_reply" in m.get("tags", []))
    auto_ratio = auto_count / total if total > 0 else 0

    if total > 30:
        alerts.append(f"[消息过多] {disc_id} | {topic} | {total}条消息")

    if total > 10 and auto_ratio > 0.6:
        alerts.append(f"[自动回复泛滥] {disc_id} | {topic} | 自动{auto_count}/{total} ({auto_ratio:.0%})")

    recent_auto_chain = 0
    last_auto_member = None
    for m in reversed(messages):
        if "auto_reply" in m.get("tags", []):
            if last_auto_member is None:
                last_auto_member = m.get("from_id")
                recent_auto_chain = 1
            elif m.get("from_id") == last_auto_member:
                recent_auto_chain += 1
            else:
                last_auto_member = m.get("from_id")
                recent_auto_chain = 1
        else:
            break
    if recent_auto_chain >= 3:
        alerts.append(f"[自动回复连锁] {disc_id} | {topic} | 末尾同一成员连续{recent_auto_chain}条自动回复")

    _HALLUCINATION_PATTERNS = [
        "CVE-", "v2.1.3", "v2.3.0", "v1.0.0-beta",
    ]
    fabricated = []
    for m in messages[-20:]:
        content = m.get("content", "")
        for pat in _HALLUCINATION_PATTERNS:
            if pat in content:
                fabricated.append(m.get("from_name", "?"))
                break
    if len(fabricated) >= 3:
        alerts.append(f"[疑似幻觉传播] {disc_id} | {topic} | {len(fabricated)}条消息引用可疑数据(CVE/假版本号)")

    try:
        store = _ensure_store()
        disc_path = store / "discussions" / f"{disc_id}.json"
        if not disc_path.exists():
            disc_path = store / "discussions" / disc_id / "thread.json"
        if disc_path.exists():
            size_kb = disc_path.stat().st_size / 1024
            if size_kb > 100:
                alerts.append(f"[文件过大] {disc_id} | {topic} | {size_kb:.0f}KB")
    except Exception:
        pass

    return alerts
