"""灵依工具注册表 — 为 Qwen function calling 提供统一工具接口。

每个工具 = schema 定义 + 执行函数。web.py / voicecall.py 调用 get_tools() 获取
Qwen 格式的工具列表，调用 execute_tool() 执行模型选择的工具。
"""

from __future__ import annotations

from ._registry import get_tools, execute_tool  # noqa: F401
from . import _domain  # noqa: F401
from . import _network  # noqa: F401
from . import _system  # noqa: F401
