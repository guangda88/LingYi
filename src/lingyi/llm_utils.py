"""共享 LLM 调用模块 — 模型自动降级 + 配额窗口感知 + 清晰错误提示 + 用量统计"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PRIMARY_MODEL = os.environ.get("GLM_MODEL", "glm-5.1")
_FALLBACK_MODELS = ["glm-5", "glm-4.5-air", "glm-4-flash"]
_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

_RESET_ANCHOR_HOUR = 15
_RESET_ANCHOR_MIN = 57
_RESET_INTERVAL = 5 * 3600

_quota_exhausted: dict[str, float] = {}

_last_probe_time: float = 0.0
_probe_interval = 300

import threading

_usage_tracker: dict[str, dict] = {}
_usage_lock = threading.Lock()


GLM_API_KEY = ""
GLM_BASE_URL = _GLM_BASE_URL


def _init_keys() -> None:
    global GLM_API_KEY
    import sys
    sys.path.insert(0, str(Path.home() / ".ling_lib"))
    try:
        from ling_key_store import get_key
        GLM_API_KEY = get_key("GLM_CODING_PLAN_KEY") or get_key("GLM_API_KEY") or ""
        _GLM_BASE_URL = get_key("GLM_BASE_URL") or _GLM_BASE_URL
    except Exception:
        pass


_init_keys()
GLM_MODELS = [_PRIMARY_MODEL] + [m for m in _FALLBACK_MODELS if m != _PRIMARY_MODEL]


def _next_reset_time() -> float:
    """计算下一个配额重置的 Unix 时间戳。"""
    now = datetime.now()
    # 今天的锚点时刻
    anchor = now.replace(hour=_RESET_ANCHOR_HOUR, minute=_RESET_ANCHOR_MIN, second=0, microsecond=0)
    anchor_ts = anchor.timestamp()

    # 从锚点往前推算，找到 <= now 的最近重置点
    intervals_ago = int((now.timestamp() - anchor_ts) / _RESET_INTERVAL)
    last_reset = anchor_ts + intervals_ago * _RESET_INTERVAL
    if last_reset > now.timestamp():
        last_reset -= _RESET_INTERVAL

    # 下一次重置
    return last_reset + _RESET_INTERVAL


def _seconds_to_next_reset() -> int:
    """距离下一次配额重置还有多少秒。"""
    return max(0, int(_next_reset_time() - time.time()))


def _clear_expired_quotas() -> None:
    """清除已过重置时刻的配额缓存。"""
    now = time.time()
    next_reset = _next_reset_time()
    expired = [m for m, ts in _quota_exhausted.items() if now >= ts]
    for m in expired:
        del _quota_exhausted[m]
        logger.info(f"模型 {m} 配额冷却期已过，重新启用")


def _get_available_models(primary_model: str | None = None) -> list[str]:
    """返回可用模型列表，跳过配额耗尽的模型。"""
    _clear_expired_quotas()
    first = primary_model or _PRIMARY_MODEL
    all_models = [first] + [m for m in _FALLBACK_MODELS if m != first]
    available = []
    for m in all_models:
        if m in _quota_exhausted:
            remaining = int(_quota_exhausted[m] - time.time())
            if remaining > 0:
                logger.debug(f"跳过 {m}（配额耗尽，{remaining // 60}分钟后恢复）")
                continue
            else:
                del _quota_exhausted[m]
        available.append(m)
    if not available:
        logger.warning("所有模型配额均耗尽，强制重试全部")
        return all_models
    return available


def probe_premium_models() -> dict[str, str]:
    """探测 premium 模型是否可用，返回 {model: 'available'/'exhausted'}。"""
    global _last_probe_time
    _last_probe_time = time.time()

    premium = [_PRIMARY_MODEL] + [m for m in _FALLBACK_MODELS if m not in ("glm-4.5-air", "glm-4-flash")]
    results = {}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=GLM_API_KEY, base_url=GLM_BASE_URL, max_retries=0)
        for model in premium:
            try:
                client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=5,
                )
                results[model] = "available"
                if model in _quota_exhausted:
                    del _quota_exhausted[model]
            except Exception as e:
                err = str(e)
                if "1113" in err or "余额不足" in err or "429" in err:
                    results[model] = "exhausted"
                else:
                    results[model] = f"error: {err[:50]}"
    except Exception as e:
        logger.error(f"探测失败: {e}")

    # 免费模型始终可用
    for m in ("glm-4.5-air", "glm-4-flash"):
        results[m] = "available"

    return results


def get_model_status() -> dict:
    """返回当前模型状态信息，供 API/UI 展示。"""
    _clear_expired_quotas()
    status = {}
    all_models = [_PRIMARY_MODEL] + _FALLBACK_MODELS
    for m in all_models:
        if m in _quota_exhausted:
            remaining = max(0, int(_quota_exhausted[m] - time.time()))
            status[m] = {"state": "exhausted", "resets_in": f"{remaining // 60}分钟"}
        else:
            status[m] = {"state": "available"}
    status["_meta"] = {
        "next_reset": datetime.fromtimestamp(_next_reset_time()).strftime("%H:%M"),
        "seconds_to_reset": _seconds_to_next_reset(),
    }
    return status


def call_llm_with_fallback(
    client: Any,
    messages: list[dict],
    tools: list[dict] | None = None,
    primary_model: str | None = None,
) -> Any:
    """按优先级尝试模型，429/配额耗尽时自动降级，跳过已知耗尽的模型。"""
    tried = []
    models = _get_available_models(primary_model)
    for model in models:
        if model in tried:
            continue
        tried.append(model)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
            )
            if model != (primary_model or _PRIMARY_MODEL):
                logger.info(f"LLM fallback to {model}")
            _track_usage(model, resp)
            return resp, model
        except Exception as e:
            err = str(e)
            if "1113" in err or "余额不足" in err or "429" in err:
                # 缓存到下一次重置时刻而非固定5小时
                _quota_exhausted[model] = _next_reset_time()
                logger.warning(f"Model {model} 配额耗尽，{_next_reset_time()} 后重置，降级到下一个")
                continue
            logger.error(f"Model {model} unexpected error: {e}")
            raise
    raise RuntimeError(f"所有模型均不可用，已尝试: {tried}")


def friendly_error(err: Exception) -> str:
    """将 LLM 错误转为用户友好的提示。"""
    msg = str(err)
    if "1113" in msg or "余额不足" in msg:
        mins = _seconds_to_next_reset() // 60
        reset_h = datetime.fromtimestamp(_next_reset_time()).strftime("%H:%M")
        return f"⚠️ 当前时段配额已用完，{mins}分钟后重置（{reset_h}），已自动降级。"
    if "429" in msg or "rate" in msg.lower():
        return "⚠️ API调用频率超限，已自动降级到可用模型。"
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "⚠️ AI服务响应超时，请稍后再试。"
    if "所有模型均不可用" in msg:
        return "⚠️ 所有AI模型配额均已用完，请等待配额刷新后重试。"
    return f"⚠️ AI服务暂时异常：{msg[:100]}"


def _next_reset_time_human() -> str:
    """下一次重置的可读时间。"""
    return datetime.fromtimestamp(_next_reset_time()).strftime("%H:%M")


def _quota_window_id() -> str:
    """返回当前配额窗口的标识（锚点时间戳）。"""
    now = datetime.now()
    anchor = now.replace(hour=_RESET_ANCHOR_HOUR, minute=_RESET_ANCHOR_MIN, second=0, microsecond=0)
    anchor_ts = anchor.timestamp()
    intervals_ago = int((now.timestamp() - anchor_ts) / _RESET_INTERVAL)
    window_start = anchor_ts + intervals_ago * _RESET_INTERVAL
    if window_start > now.timestamp():
        window_start -= _RESET_INTERVAL
    return str(int(window_start))


def _track_usage(model: str, resp: Any) -> None:
    """记录一次成功的 LLM 调用用量。"""
    try:
        window = _quota_window_id()
        usage = getattr(resp, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", 0) or 0
        with _usage_lock:
            if window not in _usage_tracker:
                _usage_tracker[window] = {}
            w = _usage_tracker[window]
            if model not in w:
                w[model] = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            m = w[model]
            m["calls"] += 1
            m["prompt_tokens"] += prompt_tokens
            m["completion_tokens"] += completion_tokens
            m["total_tokens"] += total_tokens
    except Exception:
        pass


def get_usage_stats() -> dict:
    """返回用量统计，按配额窗口分组。"""
    with _usage_lock:
        current_window = _quota_window_id()
        current = _usage_tracker.get(current_window, {})
        total_calls = sum(m["calls"] for m in current.values())
        total_tokens = sum(m["total_tokens"] for m in current.values())
        return {
            "current_window": {
                "window_id": current_window,
                "resets_at": datetime.fromtimestamp(_next_reset_time()).strftime("%H:%M"),
                "seconds_to_reset": _seconds_to_next_reset(),
                "total_calls": total_calls,
                "total_tokens": total_tokens,
                "models": dict(current),
            },
            "all_windows": {k: dict(v) for k, v in _usage_tracker.items()},
        }


def create_client() -> Any:
    """创建禁用自动重试的 OpenAI 客户端。"""
    from openai import OpenAI

    return OpenAI(api_key=GLM_API_KEY, base_url=GLM_BASE_URL, max_retries=0)
