"""网络工具 — AI新闻/GitHub/PyPI/网络搜索/工具汇总。"""

from __future__ import annotations

import json as _json
import logging
import urllib.parse as _urllib_parse
import urllib.request as _urllib_request

from ._registry import _register

logger = logging.getLogger(__name__)


# ── AI新闻 ────────────────────────────────────────────

def _ai_news() -> str:
    from pathlib import Path
    from datetime import datetime
    news_dir = Path(__file__).parent.parent.parent / "docs"
    today_str = datetime.now().strftime("%Y%m%d")
    today_file = news_dir / f"AI_NEWS_{today_str}.md"

    if today_file.exists():
        content = today_file.read_text(encoding="utf-8")
        if len(content) > 3000:
            return content[:3000] + "\n\n...(完整报告请查看 " + today_file.name + ")"
        return content

    stale = sorted(news_dir.glob("AI_NEWS_*.md"), reverse=True)
    stale_info = ""
    if stale:
        stale_info = f"（本地最新: {stale[0].stem.replace('AI_NEWS_','')}，非今日）"

    try:
        queries = ["AI LLM GPT artificial intelligence", "AI agent open source model", "AI 人工智能 大模型"]
        all_items: list[str] = []
        for q in queries:
            try:
                url = f"https://hn.algolia.com/api/v1/search_by_date?query={_urllib_parse.quote_plus(q)}&tags=story&hitsPerPage=5"
                req = _urllib_request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LingYi)"})
                with _urllib_request.urlopen(req, timeout=10) as resp:
                    hn_data = _json.loads(resp.read().decode("utf-8"))
                for hit in hn_data.get("hits", []):
                    title = (hit.get("title") or "").strip()
                    if not title:
                        continue
                    link = hit.get("url", "")
                    points = hit.get("points") or 0
                    date_str = (hit.get("created_at") or "")[:10]
                    line = f"**{title}**"
                    if link:
                        line += f"\n[link]({link})"
                    line += f"\n{date_str} · {points} points"
                    if title not in [it.split("**")[1] if "**" in it else "" for it in all_items]:
                        all_items.append(line)
            except Exception:
                continue
        if all_items:
            seen: set[str] = set()
            unique: list[str] = []
            for item in all_items:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)
            report = f"# AI 新闻速报 {datetime.now().strftime('%Y-%m-%d')}{stale_info}\n\n"
            report += "\n\n".join(unique[:10])
            report += f"\n\n---\n*由灵依实时采集于 {datetime.now().strftime('%H:%M')}*"
            try:
                news_dir.mkdir(parents=True, exist_ok=True)
                today_file.write_text(report, encoding="utf-8")
            except Exception:
                pass
            return report[:3000]
    except Exception as e:
        if stale:
            content = stale[0].read_text(encoding="utf-8")
            return content[:3000] + f"\n\n⚠️ 实时采集失败({e})，以上为历史数据"
        return f"实时新闻采集失败: {e}"

    if stale:
        content = stale[0].read_text(encoding="utf-8")
        return content[:3000] + f"\n\n⚠️ 非今日数据{stale_info}"
    return "暂无AI新闻报告"


_register("ai_news", "获取最新的AI行业新闻报告", {}, executor=_ai_news)


# ── GitHub ────────────────────────────────────────────

def _check_github(repo: str) -> str:
    try:
        url = f"https://api.github.com/repos/{repo}"
        req = _urllib_request.Request(url, headers={"User-Agent": "LingYi/0.15"})
        with _urllib_request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
        result = {
            "repo": repo,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "default_branch": data.get("default_branch", ""),
            "updated_at": data.get("updated_at", ""),
        }
        return _json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return _json.dumps({"error": str(e)})


_register("check_github", "查询 GitHub 仓库信息（stars、forks、issues）", {
    "repo": {"type": "string", "description": "GitHub 仓库全名，格式 owner/repo"},
}, ["repo"], _check_github)


# ── PyPI ──────────────────────────────────────────────

def _check_pypi(package: str) -> str:
    try:
        url = f"https://pypi.org/pypi/{package}/json"
        req = _urllib_request.Request(url, headers={"User-Agent": "LingYi/0.15"})
        with _urllib_request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
        info = data.get("info", {})
        result: dict = {
            "package": package,
            "version": info.get("version", ""),
            "summary": info.get("summary", ""),
        }
        try:
            stats_url = f"https://pypistats.org/api/packages/{package}/recent"
            req2 = _urllib_request.Request(stats_url, headers={"User-Agent": "LingYi/0.15"})
            with _urllib_request.urlopen(req2, timeout=5) as resp2:
                stats = _json.loads(resp2.read().decode())
            result["downloads_last_month"] = stats.get("data", {}).get("last_month", "N/A")
        except Exception:
            result["downloads_last_month"] = "查询失败"
        return _json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return _json.dumps({"error": str(e)})


_register("check_pypi", "查询 PyPI 包的版本和下载量", {
    "package": {"type": "string", "description": "PyPI 包名"},
}, ["package"], _check_pypi)


# ── 网络搜索 ──────────────────────────────────────────

def _search_web(query: str) -> str:
    try:
        url = f"https://hn.algolia.com/api/v1/search?query={_urllib_parse.quote_plus(query)}&tags=story&hitsPerPage=8"
        req = _urllib_request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LingYi)"})
        with _urllib_request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        lines: list[str] = []
        for i, hit in enumerate(data.get("hits", [])[:8]):
            title = (hit.get("title") or "").strip()
            link = hit.get("url", "")
            points = hit.get("points") or 0
            if not title:
                continue
            line = f"{i+1}. {title} ({points}pts)"
            if link:
                line += f"\n   {link}"
            lines.append(line)
        return "\n".join(lines) if lines else "未找到相关结果。"
    except Exception as e:
        return f"搜索失败: {e}"


_register("search_web", "搜索网络获取最新信息", {
    "query": {"type": "string", "description": "搜索关键词"},
}, ["query"], _search_web)


# ── 汇总 ──────────────────────────────────────────────

def _tool_summary() -> str:
    from ._registry import _tools
    names = sorted(_tools.keys())
    return f"灵依当前可用工具 ({len(names)}个): " + ", ".join(names)


_register("tool_summary", "查看灵依可用的所有工具", {}, executor=_tool_summary)
