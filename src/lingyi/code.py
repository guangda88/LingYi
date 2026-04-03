"""灵克对接：通过 LingClaude SDK 实现编程辅助。"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LINGCLAUDE_PATH = Path("/home/ai/LingClaude")


def check_lingclaude() -> dict:
    """检查灵克是否可用。"""
    try:
        import lingclaude
        return {"available": True, "version": lingclaude.__version__}
    except ImportError:
        return {"available": False, "version": None}


def ask_code(question: str, project_path: str | None = None) -> dict:
    """向灵克提问编程问题。

    Args:
        question: 编程问题
        project_path: 项目路径（可选）

    Returns:
        {"answer": str, "available": bool}
    """
    try:
        from lingclaude import QueryEngine, QueryEngineConfig
        config = QueryEngineConfig(max_turns=3)
        engine = QueryEngine(config=config)
        result = engine.query(question)
        return {
            "answer": result.output if hasattr(result, "output") else str(result),
            "available": True,
        }
    except ImportError:
        logger.debug("灵克 SDK 不可用")
        return {"answer": "灵克 SDK 未安装。", "available": False}
    except Exception as e:
        logger.debug(f"灵克请求失败: {e}")
        return {"answer": f"灵克处理失败（{e}）。", "available": False}


def format_code_result(data: dict) -> str:
    """格式化灵克回答。"""
    if not data.get("available"):
        return f"⚠ {data.get('answer', '灵克不可用')}"

    answer = data.get("answer", "无结果")
    return f"💻 灵克回答：\n{answer}"
