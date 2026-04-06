"""共享 LLM 调用模块 — 模型自动降级 + 清晰错误提示"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PRIMARY_MODEL = os.environ.get("GLM_MODEL", "glm-5.1")
_FALLBACK_MODELS = ["glm-5", "glm-4.5-air", "glm-4-flash"]
_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


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


def call_llm_with_fallback(
    client: Any,
    messages: list[dict],
    tools: list[dict] | None = None,
    primary_model: str | None = None,
) -> Any:
    """按优先级尝试模型，429/余额不足时自动降级。返回 response 对象。"""
    from openai import OpenAI

    tried = []
    models = [primary_model or _PRIMARY_MODEL] + _FALLBACK_MODELS
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
                logger.warning(f"Model {model} unavailable (429), trying next...")
                continue
            logger.error(f"Model {model} unexpected error: {e}")
            raise
    raise RuntimeError(f"所有模型均不可用，已尝试: {tried}")


def friendly_error(err: Exception) -> str:
    """将 LLM 错误转为用户友好的提示。"""
    msg = str(err)
    if "1113" in msg or "余额不足" in msg:
        return "⚠️ 智谱API余额不足，请充值后继续使用。"
    if "429" in msg or "rate" in msg.lower():
        return "⚠️ API调用频率超限，请稍后再试。"
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return "⚠️ AI服务响应超时，请稍后再试。"
    return f"⚠️ AI服务暂时异常：{msg[:100]}"


def create_client() -> Any:
    """创建禁用自动重试的 OpenAI 客户端。"""
    from openai import OpenAI

    return OpenAI(api_key=GLM_API_KEY, base_url=GLM_BASE_URL, max_retries=0)
