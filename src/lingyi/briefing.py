"""情报汇总 — 从灵通/灵知/灵克收集情报，整理汇报。"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_LINGFLOW_PATH = Path("/home/ai/LingFlow")
_LINGZHI_URL = "http://localhost:8000"
_LINGCLAUDE_PATH = Path("/home/ai/LingClaude")


def collect_lingzhi() -> dict:
    """收集灵知情报。"""
    try:
        import urllib.request
        r = urllib.request.urlopen(f"{_LINGZHI_URL}/", timeout=5)
        data = json.loads(r.read().decode())
        return {
            "available": True,
            "status": data.get("status", "unknown"),
            "version": data.get("version", ""),
            "categories": data.get("categories", []),
            "total_queries": data.get("stats", {}).get("total", 0),
            "errors": data.get("stats", {}).get("errors", 0),
        }
    except Exception as e:
        logger.debug(f"灵知收集失败: {e}")
        return {"available": False, "error": str(e)}


def collect_lingflow() -> dict:
    """收集灵通情报。"""
    result = {"available": True, "feedback_count": 0, "feedback_open": 0,
              "github_trends": 0, "daily_reports": 0, "audits": [],
              "optimization_reports": 0}

    feedback_path = _LINGFLOW_PATH / ".lingflow" / "feedback" / "feedbacks.json"
    if feedback_path.exists():
        try:
            feedbacks = json.loads(feedback_path.read_text(encoding="utf-8"))
            if isinstance(feedbacks, list):
                result["feedback_count"] = len(feedbacks)
                result["feedback_open"] = sum(
                    1 for f in feedbacks if f.get("status") == "open"
                )
        except Exception:
            pass

    trends_dir = _LINGFLOW_PATH / ".lingflow" / "reports" / "github_trends"
    if trends_dir.exists():
        result["github_trends"] = len(list(trends_dir.glob("*.json")))

    daily_dir = _LINGFLOW_PATH / ".lingflow" / "intelligence" / "reports" / "daily"
    if daily_dir.exists():
        result["daily_reports"] = len(list(daily_dir.iterdir())) if daily_dir.exists() else 0

    audit_dir = _LINGFLOW_PATH / ".lingflow" / "reports" / "audits"
    if audit_dir.exists():
        result["audits"] = [f.name for f in sorted(audit_dir.glob("*.md"))[-5:]]

    opt_dir = _LINGFLOW_PATH / ".lingflow" / "reports"
    if opt_dir.exists():
        result["optimization_reports"] = len(list(opt_dir.glob("optimization_report_*")))

    return result


def collect_lingclaude() -> dict:
    """收集灵克情报。"""
    result = {"available": True, "sessions": 0, "recent_queries": []}

    session_path = _LINGCLAUDE_PATH / "data" / "session_history.json"
    if session_path.exists():
        try:
            sessions = json.loads(session_path.read_text(encoding="utf-8"))
            if isinstance(sessions, list):
                result["sessions"] = len(sessions)
                recent = sessions[-3:] if len(sessions) >= 3 else sessions
                result["recent_queries"] = [
                    {
                        "query": s.get("query", s.get("title", ""))[:80],
                        "timestamp": s.get("timestamp", s.get("created_at", "")),
                    }
                    for s in recent
                ]
        except Exception:
            pass

    return result


def collect_all() -> dict:
    """收集全部情报。"""
    return {
        "timestamp": datetime.now().isoformat(),
        "lingzhi": collect_lingzhi(),
        "lingflow": collect_lingflow(),
        "lingclaude": collect_lingclaude(),
    }


def format_briefing(data: dict, compact: bool = False) -> str:
    """格式化情报汇报。"""
    ts = data.get("timestamp", "")[:19].replace("T", " ")
    lines = [f"📊 灵依情报汇报  {ts}", "=" * 40]

    lingzhi = data.get("lingzhi", {})
    if lingzhi.get("available"):
        lines.append(f"\n🔮 灵知知识系统")
        lines.append(f"  状态: 运行中  版本: {lingzhi.get('version', '?')}")
        lines.append(f"  分类: {', '.join(lingzhi.get('categories', []))}")
        lines.append(f"  累计查询: {lingzhi.get('total_queries', 0)}  错误: {lingzhi.get('errors', 0)}")
    else:
        lines.append(f"\n🔮 灵知知识系统: 不可用")

    lingflow = data.get("lingflow", {})
    if lingflow.get("available"):
        lines.append(f"\n🔧 灵通开发平台")
        fb = lingflow.get("feedback_count", 0)
        fb_open = lingflow.get("feedback_open", 0)
        lines.append(f"  反馈: {fb} 条（{fb_open} 条待处理）")
        trends = lingflow.get("github_trends", 0)
        if trends:
            lines.append(f"  GitHub 趋势报告: {trends} 份")
        opt = lingflow.get("optimization_reports", 0)
        if opt:
            lines.append(f"  优化报告: {opt} 份")
        audits = lingflow.get("audits", [])
        if audits:
            lines.append(f"  最近审计: {', '.join(audits[:3])}")
    else:
        lines.append(f"\n🔧 灵通开发平台: 不可用")

    lingclaude = data.get("lingclaude", {})
    if lingclaude.get("available"):
        lines.append(f"\n💻 灵克编程助手")
        sessions = lingclaude.get("sessions", 0)
        lines.append(f"  会话记录: {sessions} 条")
        recent = lingclaude.get("recent_queries", [])
        if recent:
            lines.append("  最近查询:")
            for q in recent[:3]:
                query_text = q.get("query", "")[:50]
                lines.append(f"    - {query_text}")
    else:
        lines.append(f"\n💻 灵克编程助手: 不可用")

    return "\n".join(lines)


def format_briefing_short(data: dict) -> str:
    """简短汇报（一行摘要）。"""
    parts = []
    lingzhi = data.get("lingzhi", {})
    if lingzhi.get("available"):
        parts.append(f"灵知:运行中({lingzhi.get('total_queries', 0)}查询)")
    else:
        parts.append("灵知:离线")

    lingflow = data.get("lingflow", {})
    if lingflow.get("available"):
        fb = lingflow.get("feedback_open", 0)
        parts.append(f"灵通:{lingflow.get('feedback_count', 0)}反馈{f'({fb}待处理)' if fb else ''}")
    else:
        parts.append("灵通:离线")

    lingclaude = data.get("lingclaude", {})
    if lingclaude.get("available"):
        parts.append(f"灵克:{lingclaude.get('sessions', 0)}会话")
    else:
        parts.append("灵克:离线")

    return " | ".join(parts)
