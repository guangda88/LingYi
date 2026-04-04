"""灵知对接：通过 REST API 检索知识库。"""

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000"
_TIMEOUT = 15


def _request(url: str, data: dict | None = None) -> dict:
    """发送 HTTP 请求，返回 JSON。"""
    body = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=body, method="POST" if body else "GET")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_lingzhi(base_url: str = _DEFAULT_BASE_URL) -> dict:
    """检查灵知服务状态。"""
    try:
        result = _request(f"{base_url}/health")
        return {"available": True, "status": result.get("status", "unknown")}
    except (URLError, OSError, ValueError) as e:
        logger.debug(f"灵知不可用: {e}")
        return {"available": False, "status": "unreachable"}


def _is_medical_query(question: str) -> bool:
    """检查是否为医疗诊断类查询（宪章边界：不碰医学知识检索）。"""
    _MEDICAL_KW = ("诊断", "辨证", "方剂", "处方", "怎么治", "吃什么药", "治疗方案")
    q = question.lower()
    return any(kw in q for kw in _MEDICAL_KW)


def ask_knowledge(question: str, category: str | None = None,
                  base_url: str = _DEFAULT_BASE_URL) -> dict:
    """向灵知提问，返回答案和来源。

    Args:
        question: 问题
        category: 可选分类（气功/儒家/佛家/道家/武术/哲学/科学/心理学）
        base_url: 灵知服务地址

    Returns:
        {"answer": str, "sources": list, "available": bool}
    """
    if _is_medical_query(question):
        return {
            "answer": "⚠ 灵依不做医学知识检索，请咨询专业医师。",
            "sources": [], "available": False,
        }

    payload = {"question": question}
    if category:
        payload["category"] = category

    try:
        result = _request(f"{base_url}/api/v1/ask", data=payload)
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "available": True,
        }
    except (URLError, OSError, ValueError) as e:
        logger.debug(f"灵知请求失败: {e}")
        return {
            "answer": f"灵知服务不可用（{e}）。",
            "sources": [],
            "available": False,
        }


def search_knowledge(query: str, category: str | None = None,
                     top_k: int = 5, base_url: str = _DEFAULT_BASE_URL) -> dict:
    """搜索灵知知识库。

    Returns:
        {"results": list, "total": int, "available": bool}
    """
    if _is_medical_query(query):
        return {"results": [], "total": 0, "available": False}

    params = f"?query={query}&top_k={top_k}"
    if category:
        params += f"&category={category}"

    try:
        result = _request(f"{base_url}/api/v1/search{params}")
        results = result if isinstance(result, list) else result.get("results", [])
        return {
            "results": results,
            "total": len(results),
            "available": True,
        }
    except (URLError, OSError, ValueError) as e:
        logger.debug(f"灵知搜索失败: {e}")
        return {"results": [], "total": 0, "available": False}


def get_categories(base_url: str = _DEFAULT_BASE_URL) -> dict:
    """获取灵知知识库分类列表。"""
    try:
        result = _request(f"{base_url}/api/v1/categories")
        return {"categories": result.get("categories", []), "available": True}
    except (URLError, OSError, ValueError) as e:
        logger.debug(f"灵知分类获取失败: {e}")
        return {"categories": [], "available": False}


def format_ask_result(data: dict) -> str:
    """格式化灵知问答结果。"""
    if not data.get("available"):
        return f"⚠ {data.get('answer', '灵知服务不可用')}"

    answer = data.get("answer", "无结果")
    sources = data.get("sources", [])
    lines = ["📖 灵知回答：", f"{answer}"]
    if sources:
        lines.append("")
        lines.append(f"来源（{len(sources)}条）：")
        for s in sources[:3]:
            title = s.get("title", "")
            content = s.get("content", "")[:80]
            lines.append(f"  · {title}：{content}…")
    return "\n".join(lines)
