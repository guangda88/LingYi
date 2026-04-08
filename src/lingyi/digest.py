"""信息整理与摘要 — 从外部对话/笔记中提取关键信息。"""

import re

from .memo import add_memo
from .pref import set_pref

_TODO_PATTERNS = [
    re.compile(r"(?:需要|得|要|必须|记得|别忘了|TODO)\s*(.{2,80})", re.IGNORECASE),
    re.compile(r"^(.{2,60})\s*[，,]?\s*(?:要做|待办|待完成|待处理)"),
]
_DECISION_PATTERNS = [
    re.compile(r"(?:决定|确定|选用|选择|敲定|就)\s*(.{2,80})"),
]
_PREF_PATTERNS = [
    re.compile(r"(?:喜欢|偏好|习惯|倾向|更爱|更喜)\s*(.{2,80})"),
]
_FACT_PATTERNS = [
    re.compile(r"(?:重要|关键|核心|注意|务必)\s*[：:]?\s*(.{2,100})"),
]


def digest_text(text: str) -> dict:
    """解析自由文本，提取待办、决策、偏好、关键事实。"""
    if not text or not text.strip():
        return {"todos": [], "decisions": [], "prefs": [], "facts": [], "raw_lines": 0}

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    todos, decisions, prefs, facts = [], [], [], []

    for line in lines:
        for pat in _TODO_PATTERNS:
            m = pat.search(line)
            if m:
                todos.append(m.group(1).rstrip("。，,.").strip())
                break
        for pat in _DECISION_PATTERNS:
            m = pat.search(line)
            if m:
                decisions.append(m.group(1).rstrip("。，,.").strip())
                break
        for pat in _PREF_PATTERNS:
            m = pat.search(line)
            if m:
                prefs.append(m.group(1).rstrip("。，,.").strip())
                break
        for pat in _FACT_PATTERNS:
            m = pat.search(line)
            if m:
                facts.append(m.group(1).rstrip("。，,.").strip())
                break

    return {
        "todos": todos,
        "decisions": decisions,
        "prefs": prefs,
        "facts": facts,
        "raw_lines": len(lines),
    }


def save_digest(data: dict) -> dict:
    """将提取结果保存到备忘录和偏好。返回保存计数。"""
    memo_ids = []
    pref_keys = []

    for item in data.get("todos", []):
        m = add_memo(f"[待办] {item}")
        memo_ids.append(m.id)

    for item in data.get("decisions", []):
        m = add_memo(f"[决策] {item}")
        memo_ids.append(m.id)

    for item in data.get("facts", []):
        m = add_memo(f"[要点] {item}")
        memo_ids.append(m.id)

    for i, item in enumerate(data.get("prefs", [])):
        key = f"偏好_{i + 1}"
        set_pref(key, item)
        pref_keys.append(key)

    return {"memos_saved": len(memo_ids), "prefs_saved": len(pref_keys),
            "memo_ids": memo_ids, "pref_keys": pref_keys}


def format_digest(data: dict) -> str:
    """格式化摘要结果供显示。"""
    parts = [f"📄 分析了 {data.get('raw_lines', 0)} 行文本"]
    todos = data.get("todos", [])
    decisions = data.get("decisions", [])
    prefs = data.get("prefs", [])
    facts = data.get("facts", [])

    if not any([todos, decisions, prefs, facts]):
        parts.append("未提取到结构化信息。")
        return "\n".join(parts)

    if todos:
        parts.append(f"\n📋 待办 ({len(todos)})")
        for t in todos:
            parts.append(f"  - {t}")

    if decisions:
        parts.append(f"\n✅ 决策 ({len(decisions)})")
        for d in decisions:
            parts.append(f"  - {d}")

    if prefs:
        parts.append(f"\n⚙ 偏好 ({len(prefs)})")
        for p in prefs:
            parts.append(f"  - {p}")

    if facts:
        parts.append(f"\n💡 要点 ({len(facts)})")
        for f in facts:
            parts.append(f"  - {f}")

    return "\n".join(parts)
