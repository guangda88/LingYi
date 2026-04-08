"""认知循环：主动推送、观察-思考-行动、智桥连接。"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

from ._web_app_chat_store import save_chat_message

logger = logging.getLogger(__name__)

MAX_CONVERSATION = 60


def cognitive_observe() -> dict:
    now = datetime.now()
    obs = {
        "weekday": now.weekday(),
        "hour": now.hour,
        "minute": now.minute,
        "date_str": now.strftime("%Y-%m-%d"),
        "is_weekend": now.weekday() >= 5,
    }
    try:
        from ..schedule import today_schedules
        obs["schedules_today"] = len(today_schedules())
    except Exception:
        obs["schedules_today"] = 0
    try:
        from ..memo import list_memos
        obs["memo_count"] = len(list_memos())
    except Exception:
        obs["memo_count"] = 0
    try:
        from ..lingmessage import list_discussions
        discs = list_discussions(status="open")
        obs["open_discussions"] = len(discs)
    except Exception:
        obs["open_discussions"] = 0
    return obs


def cognitive_think(obs: dict, state: dict) -> list[dict]:
    actions = []
    now = datetime.now()
    hour = obs["hour"]

    last_push_date = state.get("last_push_date")
    last_lingmsg_count = state.get("last_lingmsg_count", 0)

    if 7 <= hour < 8 and last_push_date != obs["date_str"] and obs["schedules_today"] > 0:
        actions.append({"type": "morning_briefing", "priority": "high"})
        state["last_push_date"] = obs["date_str"]

    slot_hours = {"morning": 8, "afternoon": 14, "evening": 19}
    for slot_name, slot_hour in slot_hours.items():
        reminder_key = f"reminded_{obs['date_str']}_{slot_name}"
        if hour == slot_hour - 1 and now.minute >= 30 and state.get(reminder_key) is None:
            if obs["schedules_today"] > 0:
                actions.append({"type": "schedule_reminder", "slot": slot_name, "priority": "normal"})
                state[reminder_key] = True

    if obs["open_discussions"] > last_lingmsg_count and last_lingmsg_count > 0:
        diff = obs["open_discussions"] - last_lingmsg_count
        if diff > 0:
            actions.append({"type": "new_lingmsg", "count": diff, "priority": "low"})
    state["last_lingmsg_count"] = obs["open_discussions"]

    reminder_key_evening = f"evening_{obs['date_str']}"
    if hour == 21 and state.get(reminder_key_evening) is None:
        actions.append({"type": "evening_summary", "priority": "low"})
        state[reminder_key_evening] = True

    return actions


async def cognitive_act(action: dict, push_fn, do_tts_fn):
    atype = action["type"]
    if atype == "morning_briefing":
        text = await build_briefing_push()
        await push_fn("morning_briefing", text)
        save_chat_message("assistant", f"[晨报推送] {text[:100]}...")

    elif atype == "schedule_reminder":
        slot = action.get("slot", "")
        slot_cn = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}.get(slot, slot)
        text = f"⏰ 灵通老师，{slot_cn}的日程快到了，注意准备。"
        await push_fn("reminder", text)

    elif atype == "new_lingmsg":
        count = action.get("count", 1)
        text = f"📬 有 {count} 条新的灵信讨论待处理。"
        await push_fn("lingmessage", text)

    elif atype == "evening_summary":
        text = build_evening_summary()
        if text:
            await push_fn("evening_summary", text)
            save_chat_message("assistant", f"[晚间总结] {text[:100]}...")


async def build_briefing_push() -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_briefing_push_sync)


def _build_briefing_push_sync() -> str:
    parts = [f"🌅 灵通老师早上好！{date.today().isoformat()} 灵依晨报：\n"]
    try:
        from ..schedule import format_today
        today = format_today()
        if today:
            parts.append("【今日日程】\n" + today)
    except Exception:
        pass
    try:
        from ..memo import list_memos
        memos = list_memos()
        if memos:
            parts.append("【备忘】\n" + "\n".join(f"  - {m.content}" for m in memos[:5]))
    except Exception:
        pass
    try:
        from ..briefing import collect_all, format_briefing
        data = collect_all()
        brief = format_briefing(data)
        if brief:
            parts.append("【灵字辈状态】\n" + brief)
    except Exception:
        pass
    return "\n\n".join(parts)


async def build_reminder_push() -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_reminder_push_sync)


def _build_reminder_push_sync() -> str:
    try:
        from ..schedule import today_schedules, format_slot_cn
        now = datetime.now()
        upcoming = []
        for s in today_schedules():
            desc = s.description or s.type
            slot = format_slot_cn(s.time_slot)
            upcoming.append(f"  - {slot} {desc}")
        if upcoming:
            return f"⏰ 今日提醒（{now.strftime('%H:%M')}）：\n" + "\n".join(upcoming)
    except Exception:
        pass
    return ""


def build_evening_summary() -> str:
    parts = ["🌙 灵通老师，今天的总结：\n"]
    try:
        from ..schedule import format_today
        today = format_today()
        if today:
            parts.append("【今日日程】\n" + today)
    except Exception:
        pass
    try:
        from ..plan import list_plans
        done_today = [p for p in list_plans(status="done") if hasattr(p, 'updated_at')]
        if done_today:
            parts.append(f"【已完成】{len(done_today)} 项计划")
    except Exception:
        pass
    try:
        from ..lingmessage import list_discussions
        discs = list_discussions(status="open")
        if discs:
            parts.append(f"【灵信】{len(discs)} 个待处理讨论")
    except Exception:
        pass
    parts.append("\n明天见！早点休息 🌙")
    return "\n\n".join(parts)


def council_scan_sync() -> dict:
    from ..council import council_scan
    return council_scan()


async def auto_push_loop(
    active_ws: set,
    bridge_ws: list,
    cognitive_state: dict,
    push_fn,
    do_tts_fn,
    council_scan_interval: int = 300,
):
    last_council_scan = 0.0
    while True:
        await asyncio.sleep(120)
        try:
            if active_ws or bridge_ws:
                observation = cognitive_observe()
                actions = cognitive_think(observation, cognitive_state)
                for action in actions:
                    await cognitive_act(action, push_fn, do_tts_fn)
        except Exception as exc:
            logger.error(f"Cognitive loop error: {exc}")

        try:
            import time as _time
            now_ts = _time.time()
            if now_ts - last_council_scan >= council_scan_interval:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, council_scan_sync)
                last_council_scan = now_ts
                if result.get("woken_members"):
                    names = ", ".join(result["woken_members"])
                    await push_fn("council", f"🏛️ 议事厅活动：{names} 被唤醒参与讨论")
        except Exception as exc:
            logger.error(f"Council scan error: {exc}")


async def auto_health_check_loop():
    while True:
        try:
            await asyncio.sleep(60)
            from ..endpoint_monitor import check_all_endpoints
            check_all_endpoints()
        except Exception as exc:
            logger.error(f"Health check loop error: {exc}")


async def run_bridge_connector(on_chat, on_registered):
    from ..bridge_client import connect_to_bridge
    await connect_to_bridge(on_chat=on_chat, on_registered=on_registered)
