"""共享 LLM 调用模块 — 模型自动降级 + 清晰错误提示"""

import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PRIMARY_MODEL = os.environ.get("GLM_MODEL", "glm-5.1")
_FALLBACK_MODELS = ["glm-5", "glm-4.5-air", "glm-4-flash"]
_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

# 配额耗尽的模型缓存: {model_name: quota_reset_timestamp}
_quota_exhausted: dict[str, float] = {}
_QUOTA_COOLDOWN = 5 * 3600  # 5小时


def _load_glm_key() -> str:
    key = os.environ.get(
        "GLM_CODING_PLAN_KEY",
        os.environ.get("GLM_API_KEY", ""),
    )
    if key:
        return key
    for kf in [
        Path.home() / ".glm_api_key",
        Path("/home/ai/zhineng-knowledge-system/.env"),
    ]:
        if kf.exists() and kf.suffix == ".env":
            for line in kf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GLM_CODING_PLAN_KEY="):
                    return line.split("=", 1)[1].strip()
                if line.startswith("GLM_API_KEY=") and not key:
                    key = line.split("=", 1)[1].strip()
            if key:
                return key
        elif kf.exists():
            return kf.read_text(encoding="utf-8").strip()
    return key


GLM_API_KEY = _load_glm_key()
GLM_BASE_URL = _GLM_BASE_URL
GLM_MODELS = [_PRIMARY_MODEL] + [m for m in _FALLBACK_MODELS if m != _PRIMARY_MODEL]


def _get_available_models(primary_model: str | None = None) -> list[str]:
    """返回可用模型列表，跳过配额耗尽的模型。"""
    now = time.time()
    first = primary_model or _PRIMARY_MODEL
    all_models = [first] + [m for m in _FALLBACK_MODELS if m != first]
    available = []
    for m in all_models:
        if m in _quota_exhausted:
            if now >= _quota_exhausted[m]:
                del _quota_exhausted[m]
                logger.info(f"模型 {m} 配额冷却期已过，重新启用")
            else:
                remaining = int(_quota_exhausted[m] - now)
                logger.debug(f"跳过 {m}（配额耗尽，{remaining // 60}分钟后恢复）")
                continue
        available.append(m)
    if not available:
        logger.warning("所有模型配额均耗尽，强制重试全部")
        return all_models
    return available


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
            return resp
        except Exception as e:
            err = str(e)
            if "1113" in err or "余额不足" in err or "429" in err:
                _quota_exhausted[model] = time.time() + _QUOTA_COOLDOWN
                logger.warning(f"Model {model} 配额耗尽，{ _QUOTA_COOLDOWN // 3600}小时后再试，降级到下一个")
                continue
            logger.error(f"Model {model} unexpected error: {e}")
            raise
    raise RuntimeError(f"所有模型均不可用，已尝试: {tried}")


def friendly_error(err: Exception) -> str:
    """将 LLM 错误转为用户友好的提示。"""
    msg = str(err)
    if "1113" in msg or "余额不足" in msg:
        return "⚠️ 智谱API当前时段配额已用完，约5小时后恢复，已自动降级到可用模型。"
    if "429" in msg or "rate" in msg.lower():
        return "⚠️ API调用频率超限，已自动降级到可用模型。"
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "⚠️ AI服务响应超时，请稍后再试。"
    if "所有模型均不可用" in msg:
        return "⚠️ 所有AI模型配额均已用完，请等待配额刷新（约5小时）后重试。"
    return f"⚠️ AI服务暂时异常：{msg[:100]}"


def create_client() -> Any:
    """创建禁用自动重试的 OpenAI 客户端。"""
    from openai import OpenAI

    return OpenAI(api_key=GLM_API_KEY, base_url=GLM_BASE_URL, max_retries=0)
