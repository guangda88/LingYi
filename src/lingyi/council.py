"""灵家议事厅守护进程 — 客厅的灯。

让灵信讨论在用户终端关闭后仍能继续。灵依作为客厅灯守：
- 监听灵信新消息
- 按需唤醒成员参与讨论
- 追踪议题生命周期
- 用户回来后汇报离线期间的讨论
"""

import json
import logging
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .lingmessage import (
    PROJECTS, _ensure_store, _load_index, _load_discussion,
    _project_name, _now,
)
from .llm_utils import create_client, call_llm_with_fallback

logger = logging.getLogger(__name__)

_KEY_FILE = Path.home() / ".dashscope_api_key"
_COUNCIL_STATE_PATH = Path.home() / ".lingmessage" / "council_state.json"
MAX_TURNS_PER_MEMBER = 2
MAX_MESSAGES_PER_DISCUSSION = 15


MEMBER_ENDPOINTS = {
    "lingzhi": {
        "url": "http://127.0.0.1:8000/api/v1/discuss",
        "source": "real",
    },
    "lingyi": {
        "url": "https://127.0.0.1:8900/api/discuss",
        "source": "real",
    },
    "lingclaude": {
        "url": "http://127.0.0.1:8700/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingzhi_auto": {
        "url": "http://127.0.0.1:8011/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
        "member_id": "lingzhi",
    },
    "lingminopt": {
        "url": "http://127.0.0.1:8002/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingresearch": {
        "url": "http://127.0.0.1:8003/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingyang": {
        "url": "http://127.0.0.1:8004/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingflow": {
        "url": "http://127.0.0.1:8100/api/v1/discuss",
        "source": "real",
        "notify_only": True,
    },
}


@dataclass
class CouncilState:
    last_scan_time: str = ""
    processed_messages: list = field(default_factory=list)
    wake_count: int = 0
    discussions_monitored: int = 0
    started_at: str = ""


def _load_state() -> CouncilState:
    if _COUNCIL_STATE_PATH.exists():
        try:
            data = json.loads(_COUNCIL_STATE_PATH.read_text(encoding="utf-8"))
            return CouncilState(**{k: v for k, v in data.items() if k in CouncilState.__dataclass_fields__})
        except Exception:
            pass
    return CouncilState()


def _save_state(state: CouncilState) -> None:
    _COUNCIL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _COUNCIL_STATE_PATH.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _send_notify_to_member(member_id: str, disc: dict, disc_id: str) -> None:
    """向 notify_only 成员发送灵信通知，让成员自行回复。"""
    endpoint = MEMBER_ENDPOINTS.get(member_id)
    if not endpoint:
        return

    topic = disc.get("topic", "")
    url = endpoint["url"]

    payload = json.dumps({
        "event": "new_message",
        "from": "lingyi",
        "discussion_id": disc_id,
        "topic": topic,
        "timestamp": _now(),
    }, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        kwargs: dict = {"timeout": 5}
        if url.startswith("https://"):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kwargs["context"] = ctx
        resp = urllib.request.urlopen(req, **kwargs)
        data = json.loads(resp.read().decode("utf-8"))
        member_name = _project_name(member_id)
        action = data.get("action", "unknown")
        logger.info(f"📡 已通知 {member_name} 议题「{topic[:30]}」→ {action}")
    except urllib.error.URLError as e:
        logger.debug(f"通知 {member_id} 失败（服务可能离线）: {e.reason}")
    except Exception as e:
        logger.warning(f"通知 {member_id} 异常: {e}")


def _is_near_duplicate(text_a: str, text_b: str, threshold: float = 0.8) -> bool:
    """检查两段文本是否高度重复（基于词汇重叠率）。"""
    if not text_a or not text_b:
        return False
    def _tokenize(text: str) -> set:
        return set(text.replace("。", " ").replace("，", " ").replace(".", " ").replace(",", " ").split())
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b)
    ratio = overlap / min(len(tokens_a), len(tokens_b))
    return ratio >= threshold


def _call_real_member(member_id: str, disc: dict) -> Optional[str]:
    """调用成员的真实API端点。返回该成员的回复内容，失败返回None。"""
    endpoint = MEMBER_ENDPOINTS.get(member_id)
    if not endpoint:
        return None

    topic = disc.get("topic", "")
    messages_list = disc.get("messages", [])

    # Build context with explicit instruction to respond to previous speakers
    context_parts = []
    for msg in messages_list[-10:]:
        sender = msg.get("from_name", msg.get("from_id", "?"))
        content = msg.get("content", "")
        context_parts.append(f"【{sender}】{content}")
    context_text = "\n\n".join(context_parts)

    # Extract the last speaker's specific points for targeted response
    last_speaker_points = ""
    if messages_list:
        last_msg = messages_list[-1]
        last_sender = last_msg.get("from_name", "?")
        last_content = last_msg.get("content", "")
        if last_content:
            last_speaker_points = (
                f"\n\n【重要】最后发言的是 {last_sender}，请具体回应TA的观点：\n"
                f"1. 引用 {last_sender} 的至少一个具体论点\n"
                f"2. 明确表示你同意、反对还是补充该论点，并给出理由\n"
                f"3. 不要重复你或别人已经说过的内容\n"
                f"\n{last_sender}的发言：{last_content[:800]}"
            )

    payload = json.dumps({
        "topic": topic,
        "context": (context_text[:2000] + last_speaker_points)[:3000],
        "question": "请针对讨论中的具体观点发表意见，不要泛泛而谈。",
        "depth": "normal",
    }, ensure_ascii=False).encode("utf-8")

    url = endpoint["url"]
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        kwargs: dict = {"timeout": 60}
        if url.startswith("https://"):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kwargs["context"] = ctx
        resp = urllib.request.urlopen(req, **kwargs)
        data = json.loads(resp.read().decode("utf-8"))
        content = data.get("content", "").strip()
        if content and data.get("source_type") == "real":
            logger.info(f"✅ {member_id} 真实API返回成功 (model: {data.get('model_used', '?')})")
            return content
        logger.warning(f"⚠️ {member_id} API返回source_type不是real: {data.get('source_type')}")
        return content if content else None
    except urllib.error.URLError as e:
        logger.debug(f"成员 {member_id} 端点 {url} 不可达: {e.reason}")
        return None
    except Exception as e:
        logger.warning(f"调用 {member_id} 真实API失败: {e}")
        return None


def wake_member(member_id: str, disc_id: str) -> Optional[str]:
    """唤醒一个成员参与讨论。

    防护机制：
    - 每个成员同一讨论最多发言 MAX_TURNS_PER_MEMBER 次
    - 同一讨论总消息数不超过 MAX_MESSAGES_PER_DISCUSSION
    - 新消息与该成员上一条消息相似度>80%时跳过（防重复）
    - 末尾连续3条都是自动回复时跳过（防循环）
    """
    endpoint = MEMBER_ENDPOINTS.get(member_id)
    if not endpoint:
        logger.debug(f"跳过无真实端点的成员: {_project_name(member_id)}")
        return None

    store = _ensure_store()
    disc = _load_discussion(store, disc_id)
    if not disc or disc.get("status") == "closed":
        return None

    member_name = _project_name(member_id)
    messages = disc.get("messages", [])

    # Guard 1: max total messages
    if len(messages) >= MAX_MESSAGES_PER_DISCUSSION:
        logger.info(f"讨论 {disc_id} 已有 {len(messages)} 条消息，达到上限，停止唤醒")
        return None

    # Guard 2: max turns per member
    member_msg_count = sum(1 for m in messages if m.get("from_id") == member_id)
    if member_msg_count >= MAX_TURNS_PER_MEMBER:
        logger.debug(f"{member_name} 已发言 {member_msg_count} 次，达到上限")
        return None

    if not messages:
        logger.debug(f"讨论 {disc_id} 无已有消息，不需要唤醒 {member_name}")
        return None

    # Guard 3: check for auto-reply chain at the end (改进版：区分同一成员和不同成员)
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
                # 不同成员的自动回复，重置计数
                last_auto_member = m.get("from_id")
                recent_auto_chain = 1
        else:
            break
    if recent_auto_chain >= 3:
        logger.info(f"讨论末尾已有 {recent_auto_chain} 条同一成员的连续自动回复，暂停唤醒 {member_name}")
        return None

    # Guard 4: deduplication — checked after API call (line 276-280)
    member_msgs = [m for m in messages if m.get("from_id") == member_id]

    if endpoint.get("notify_only"):
        _send_notify_to_member(member_id, disc, disc_id)
        return None

    result = _call_real_member(member_id, disc)
    if not result:
        logger.info(f"真实API不可用，跳过: {member_name}")
        return None

    # Guard 4: deduplication — check against member's previous messages
    if member_msgs:
        last_content = member_msgs[-1].get("content", "")
        if last_content and _is_near_duplicate(result, last_content):
            logger.info(f"{member_name} 的回复与上一条消息重复度>80%，跳过")
            return None

    return result


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
                    # 不同成员的自动回复，重置计数
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
                # 不同成员的自动回复，重置计数
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


def council_status() -> dict:
    """返回议事厅守护进程状态。"""
    state = _load_state()
    store = _ensure_store()
    index = _load_index(store)
    open_count = len([d for d in index if d.get("status") == "open"])
    total_count = len(index)

    return {
        "started_at": state.started_at,
        "last_scan": state.last_scan_time,
        "total_wakes": state.wake_count,
        "open_discussions": open_count,
        "total_discussions": total_count,
        "members_registered": len(PROJECTS),
        "real_endpoints": list(MEMBER_ENDPOINTS.keys()),
    }


def council_health() -> dict:
    """全面健康检查。返回 {alerts: [...], summary: {...}, per_discussion: [...]}。"""
    store = _ensure_store()
    index = _load_index(store)

    all_alerts = []
    per_discussion = []
    total_messages = 0
    total_auto = 0
    total_human = 0

    for entry in index:
        disc_id = entry.get("id") or entry.get("thread_id", "")
        if not disc_id:
            continue
        disc = _load_discussion(store, disc_id)
        if not disc:
            continue

        alerts = _check_discussion_health(disc_id, disc)
        all_alerts.extend(alerts)

        messages = disc.get("messages", [])
        auto_count = sum(1 for m in messages if "auto_reply" in m.get("tags", []))
        human_count = len(messages) - auto_count
        total_messages += len(messages)
        total_auto += auto_count
        total_human += human_count

        if disc.get("status") == "open":
            per_discussion.append({
                "id": disc_id,
                "topic": disc.get("topic", "?")[:40],
                "status": disc.get("status", "?"),
                "messages": len(messages),
                "auto_replies": auto_count,
                "human_messages": human_count,
                "alerts": len(alerts),
                "last_speaker": messages[-1].get("from_name", "?") if messages else "",
                "last_time": messages[-1].get("timestamp", "") if messages else "",
            })

    open_count = len([d for d in index if d.get("status") == "open"])
    auto_ratio = total_auto / total_messages if total_messages > 0 else 0

    summary = {
        "total_discussions": len(index),
        "open_discussions": open_count,
        "total_messages": total_messages,
        "total_auto_replies": total_auto,
        "total_human_messages": total_human,
        "auto_reply_ratio": f"{auto_ratio:.1%}",
        "alert_count": len(all_alerts),
        "status": "HEALTHY" if not all_alerts else "ALERT",
    }

    return {
        "alerts": all_alerts,
        "summary": summary,
        "per_discussion": per_discussion,
    }


def start_council_daemon(interval: int = 300, once: bool = False) -> None:
    """启动议事厅守护进程。

    Args:
        interval: 扫描间隔（秒），默认300秒（5分钟）
        once: 只运行一次就退出（用于测试或手动触发）
    """
    state = _load_state()
    state.started_at = _now()
    _save_state(state)

    logger.info(f"🏛️  灵家议事厅守护进程启动 (间隔 {interval}s)")

    if once:
        results = council_scan()
        logger.info(f"扫描完成: {results['open_discussions']} 个open讨论, "
                     f"唤醒了 {results['woken_members']}")
        return

    while True:
        try:
            results = council_scan()
            if results["woken_members"]:
                logger.info(f"唤醒成员: {', '.join(results['woken_members'])}")
            else:
                logger.debug(f"扫描完成: {results['open_discussions']} 个open讨论")
        except Exception as e:
            logger.error(f"议事厅扫描异常: {e}")

        time.sleep(interval)
