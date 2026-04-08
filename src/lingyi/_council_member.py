"""灵家议事厅成员交互 — 通知、去重、真实API调用、唤醒。"""

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Optional

from .lingmessage import (
    _ensure_store, _load_discussion,
    _project_name, _now,
)
from ._council_config import (
    MEMBER_ENDPOINTS, MAX_TURNS_PER_MEMBER, MAX_MESSAGES_PER_DISCUSSION,
)

logger = logging.getLogger(__name__)


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

    context_parts = []
    for msg in messages_list[-10:]:
        sender = msg.get("from_name", msg.get("from_id", "?"))
        content = msg.get("content", "")
        context_parts.append(f"【{sender}】{content}")
    context_text = "\n\n".join(context_parts)

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

            try:
                from .constraint_layer import Assertion, ConstraintLayer
                constraint = ConstraintLayer()

                assertion = Assertion(
                    member_id=member_id,
                    assertion_type="communication",
                    content=content,
                    tool_call={
                        "name": "council_reply",
                        "arguments": {"topic": topic, "discussion_id": disc.get("disc_id", "")}
                    }
                )

                result = constraint.verify_assertion(assertion)

                if not result.passed:
                    logger.warning(f"❌ 约束层拦截{member_id}的讨论回复: {result.reason}")
                    if result.requires_fallback:
                        logger.info(f"⚠️ {member_id}的回复虽未通过验证但允许降级处理")
                        content = content + f"\n\n[约束层警告: {result.recommendation or result.reason}]"
                    else:
                        logger.warning(f"⛔ {member_id}的回复被约束层拒绝")
                        return None
            except ImportError:
                logger.debug("约束层未初始化，跳过验证")
            except Exception as e:
                logger.warning(f"约束层验证失败: {e}")

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

    if len(messages) >= MAX_MESSAGES_PER_DISCUSSION:
        logger.info(f"讨论 {disc_id} 已有 {len(messages)} 条消息，达到上限，停止唤醒")
        return None

    member_msg_count = sum(1 for m in messages if m.get("from_id") == member_id)
    if member_msg_count >= MAX_TURNS_PER_MEMBER:
        logger.debug(f"{member_name} 已发言 {member_msg_count} 次，达到上限")
        return None

    if not messages:
        logger.debug(f"讨论 {disc_id} 无已有消息，不需要唤醒 {member_name}")
        return None

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
        logger.info(f"讨论末尾已有 {recent_auto_chain} 条同一成员的连续自动回复，暂停唤醒 {member_name}")
        return None

    member_msgs = [m for m in messages if m.get("from_id") == member_id]

    if endpoint.get("notify_only"):
        _send_notify_to_member(member_id, disc, disc_id)
        return None

    result = _call_real_member(member_id, disc)
    if not result:
        logger.info(f"真实API不可用，跳过: {member_name}")
        return None

    if member_msgs:
        last_content = member_msgs[-1].get("content", "")
        if last_content and _is_near_duplicate(result, last_content):
            logger.info(f"{member_name} 的回复与上一条消息重复度>80%，跳过")
            return None

    return result
