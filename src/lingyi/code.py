"""灵克对接：通过 LingClaude SDK 实现编程辅助。"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def check_lingclaude() -> dict:
    """检查灵克是否可用。"""
    try:
        import lingclaude
        return {"available": True, "version": lingclaude.__version__}
    except ImportError:
        return {"available": False, "version": None}


def _ask_engine(prompt: str) -> dict:
    """内部：向灵克引擎发送查询。"""
    try:
        from lingclaude import QueryEngine, QueryEngineConfig
        config = QueryEngineConfig(max_turns=3)
        engine = QueryEngine(config=config)
        result = engine.query(prompt)
        return {
            "answer": result.output if hasattr(result, "output") else str(result),
            "available": True,
        }
    except ImportError:
        return {"answer": "灵克 SDK 未安装。", "available": False}
    except Exception as e:
        logger.debug(f"灵克请求失败: {e}")
        return {"answer": f"灵克处理失败（{e}）。", "available": False}


def ask_code(question: str, project_path: str | None = None) -> dict:
    """向灵克提问编程问题。"""
    return _ask_engine(question)


def review_code(file_path: str) -> dict:
    """代码审查：读取文件内容，让灵克审查。"""
    path = Path(file_path)
    if not path.exists():
        return {"answer": f"文件不存在: {file_path}", "available": False}
    if not path.is_file():
        return {"answer": f"不是文件: {file_path}", "available": False}

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {"answer": f"读取失败: {e}", "available": False}

    if len(content) > 20000:
        content = content[:20000] + "\n... (截断)"

    prompt = (
        f"请审查以下 Python 代码，指出潜在问题和改进建议。\n"
        f"文件: {path.name}\n\n```\n{content}\n```"
    )
    result = _ask_engine(prompt)
    result["file"] = str(path)
    return result


def check_dependencies(project_path: str) -> dict:
    """依赖检查：分析项目依赖是否有问题。"""
    project = Path(project_path)
    if not project.exists():
        return {"answer": f"项目路径不存在: {project_path}", "available": False}

    dep_content = ""
    dep_file = ""
    for name in ["pyproject.toml", "requirements.txt", "setup.py"]:
        p = project / name
        if p.exists():
            dep_content = p.read_text(encoding="utf-8")[:10000]
            dep_file = name
            break

    if not dep_content:
        return {"answer": "未找到依赖文件（pyproject.toml/requirements.txt/setup.py）。",
                "available": False, "project": str(project)}

    prompt = (
        f"请分析以下项目依赖配置，检查是否有安全风险、版本冲突或不必要的依赖。\n"
        f"文件: {dep_file}\n\n```\n{dep_content}\n```"
    )
    result = _ask_engine(prompt)
    result["project"] = str(project)
    result["dep_file"] = dep_file
    return result


def suggest_refactor(file_path: str) -> dict:
    """重构建议：分析代码结构和可改进之处。"""
    path = Path(file_path)
    if not path.exists():
        return {"answer": f"文件不存在: {file_path}", "available": False}

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {"answer": f"读取失败: {e}", "available": False}

    if len(content) > 20000:
        content = content[:20000] + "\n... (截断)"

    prompt = (
        f"请分析以下代码的结构和质量，给出重构建议（不改变功能）。\n"
        f"关注：函数长度、命名、重复代码、可读性。\n"
        f"文件: {path.name}\n\n```\n{content}\n```"
    )
    result = _ask_engine(prompt)
    result["file"] = str(path)
    return result


def format_code_result(data: dict) -> str:
    """格式化灵克回答。"""
    if not data.get("available"):
        return f"⚠ {data.get('answer', '灵克不可用')}"

    header = "💻 灵克回答"
    if data.get("file"):
        header += f" ({data['file']})"
    elif data.get("project"):
        header += f" ({data['project']})"

    answer = data.get("answer", "无结果")
    return f"{header}：\n{answer}"
