"""工具注册表核心 — _tools/_executors 字典与注册/查询/执行函数。"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_tools: dict[str, dict] = {}
_executors: dict[str, Callable] = {}


def _register(name: str, description: str, parameters: dict,
              required: list[str] | None = None,
              executor: Callable | None = None):
    _tools[name] = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                **({"required": required} if required else {}),
            },
        },
    }
    if executor:
        _executors[name] = executor


def get_tools() -> list[dict]:
    return list(_tools.values())


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    fn = _executors.get(name)
    if not fn:
        return f"未知工具: {name}"
    try:
        result = fn(**arguments)
        if result is None:
            return "操作完成（无返回内容）"
        if isinstance(result, str):
            return result
        return str(result)
    except Exception as exc:
        logger.error(f"工具 {name} 执行失败: {exc}")
        return f"工具执行失败: {exc}"
