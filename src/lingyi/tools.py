"""灵依工具注册表 — 为 Qwen function calling 提供统一工具接口。

每个工具 = schema 定义 + 执行函数。web.py / voicecall.py 调用 get_tools() 获取
Qwen 格式的工具列表，调用 execute_tool() 执行模型选择的工具。
"""

import json as _json
import logging
import urllib.parse as _urllib_parse
import urllib.request as _urllib_request
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


# ── 备忘 ──────────────────────────────────────────────

def _memo_add(content: str) -> str:
    from .memo import add_memo
    m = add_memo(content)
    return f"已记录备忘 #{m.id}：{content}"


def _memo_list() -> str:
    from .memo import list_memos
    memos = list_memos()
    if not memos:
        return "暂无备忘"
    lines = [f"#{m.id} {m.content}" for m in memos[:10]]
    return "\n".join(lines)


def _memo_delete(memo_id: int) -> str:
    from .memo import delete_memo
    ok = delete_memo(memo_id)
    return f"已删除备忘 #{memo_id}" if ok else f"未找到备忘 #{memo_id}"


_register("memo_add", "添加一条备忘录", {
    "content": {"type": "string", "description": "备忘内容"},
}, ["content"], _memo_add)

_register("memo_list", "查看最近的备忘录", {}, executor=_memo_list)

_register("memo_delete", "删除一条备忘录", {
    "memo_id": {"type": "integer", "description": "备忘ID"},
}, ["memo_id"], _memo_delete)


# ── 日程 ──────────────────────────────────────────────

def _schedule_today() -> str:
    from .schedule import format_today
    result = format_today()
    return result or "今天没有日程"


def _schedule_week() -> str:
    from .schedule import format_week
    return format_week()


def _schedule_add(schedule_type: str, day: str, time_slot: str, description: str) -> str:
    from .schedule import add_schedule
    s = add_schedule(schedule_type, day, time_slot, description)
    return f"已添加日程 #{s.id}：{day} {time_slot} {description}"


_register("schedule_today", "查看今天的日程安排", {}, executor=_schedule_today)

_register("schedule_week", "查看本周的日程安排", {}, executor=_schedule_week)

_register("schedule_add", "添加一条日程", {
    "type": {"type": "string", "description": "日程类型（clinic/practice/ask/journal）"},
    "day": {"type": "string", "description": "星期几（Monday/Tuesday/...）"},
    "time_slot": {"type": "string", "description": "时间段（morning/afternoon/evening）"},
    "description": {"type": "string", "description": "日程描述"},
}, ["type", "day", "time_slot", "description"], _schedule_add)


# ── 计划 ──────────────────────────────────────────────

def _plan_list(area: str = "", status: str = "") -> str:
    from .plan import list_plans, format_plan_short
    plans = list_plans(area=area or None, status=status or None)
    if not plans:
        return "没有符合条件的计划"
    return "\n".join(format_plan_short(p) for p in plans[:15])


def _plan_add(content: str, area: str = "编程") -> str:
    from .plan import add_plan
    p = add_plan(content, area=area)
    return f"已添加计划 #{p.id}：{content}（{area}）"


def _plan_done(plan_id: int) -> str:
    from .plan import done_plan
    p = done_plan(plan_id)
    return f"已完成计划 #{plan_id}" if p else f"未找到计划 #{plan_id}"


_register("plan_list", "查看计划列表", {
    "area": {"type": "string", "description": "领域筛选（医疗/编程/研究/论文/学术）"},
    "status": {"type": "string", "description": "状态筛选（todo/done/cancel）"},
}, executor=_plan_list)

_register("plan_add", "添加一条计划", {
    "content": {"type": "string", "description": "计划内容"},
    "area": {"type": "string", "description": "领域（医疗/编程/研究/论文/学术），默认编程"},
}, ["content"], _plan_add)

_register("plan_done", "标记计划为完成", {
    "plan_id": {"type": "integer", "description": "计划ID"},
}, ["plan_id"], _plan_done)


# ── 项目 ──────────────────────────────────────────────

def _project_list(status: str = "") -> str:
    from .project import list_projects, format_project_short
    projects = list_projects(status=status or None)
    if not projects:
        return "没有项目"
    return "\n".join(format_project_short(p) for p in projects)


def _project_show(name: str) -> str:
    from .project import show_project, format_project_detail
    p = show_project(name)
    if not p:
        return f"未找到项目: {name}"
    return format_project_detail(p)


_register("project_list", "查看项目列表", {
    "status": {"type": "string", "description": "状态筛选（active/maintenance/paused/archived）"},
}, executor=_project_list)

_register("project_show", "查看项目详情", {
    "name": {"type": "string", "description": "项目名或别名"},
}, ["name"], _project_show)


# ── 情报 ──────────────────────────────────────────────

def _briefing() -> str:
    from .briefing import collect_all, format_briefing
    data = collect_all()
    return format_briefing(data, compact=True)


_register("briefing", "获取灵字辈情报汇总", {}, executor=_briefing)


# ── 巡检 ──────────────────────────────────────────────

def _patrol() -> str:
    from .patrol import generate_report
    return generate_report()


_register("patrol", "执行项目巡检（检查各项目Git变更）", {}, executor=_patrol)


# ── 灵信 ──────────────────────────────────────────────

def _msg_list() -> str:
    from .lingmessage import list_discussions, format_discussion_list
    discussions = list_discussions(status="open")
    return format_discussion_list(discussions)


def _msg_send(topic: str, content: str) -> str:
    from .lingmessage import send_message
    msg = send_message(from_id="lingyi", topic=topic, content=content)
    return f"已发送灵信 [{topic}]: {msg.id}"


def _msg_read(discussion_id: str) -> str:
    from .lingmessage import read_discussion, format_discussion_thread
    disc = read_discussion(discussion_id)
    if not disc:
        return f"未找到讨论: {discussion_id}"
    return format_discussion_thread(disc)


_register("msg_list", "查看灵信讨论列表", {}, executor=_msg_list)

_register("msg_send", "发送灵信消息", {
    "topic": {"type": "string", "description": "讨论主题"},
    "content": {"type": "string", "description": "消息内容"},
}, ["topic", "content"], _msg_send)

_register("msg_read", "阅读灵信讨论详情", {
    "discussion_id": {"type": "string", "description": "讨论ID"},
}, ["discussion_id"], _msg_read)


# ── 偏好 ──────────────────────────────────────────────

def _pref_list() -> str:
    from .pref import list_prefs, format_pref_list
    prefs = list_prefs()
    return format_pref_list(prefs)


def _pref_set(key: str, value: str) -> str:
    from .pref import set_pref
    set_pref(key, value)
    return f"已设置偏好 {key} = {value}"


_register("pref_list", "查看用户偏好设置", {}, executor=_pref_list)

_register("pref_set", "设置用户偏好", {
    "key": {"type": "string", "description": "偏好键名"},
    "value": {"type": "string", "description": "偏好值"},
}, ["key", "value"], _pref_set)


# ── 会话 ──────────────────────────────────────────────

def _session_last() -> str:
    from .session import last_session, format_session_resume
    s = last_session()
    if not s:
        return "没有最近的会话记录"
    return format_session_resume(s)


_register("session_last", "查看上次会话摘要", {}, executor=_session_last)


# ── 知识库 ────────────────────────────────────────────

def _ask(query: str) -> str:
    from .ask import ask_knowledge
    return ask_knowledge(query)


_register("ask", "向灵知知识库查询", {
    "query": {"type": "string", "description": "查询内容"},
}, ["query"], _ask)


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
        all_items = []
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
            seen = set()
            unique = []
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
        result = {
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
        lines = []
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
    names = sorted(_tools.keys())
    return f"灵依当前可用工具 ({len(names)}个): " + ", ".join(names)


_register("tool_summary", "查看灵依可用的所有工具", {}, executor=_tool_summary)


# ── Shell 执行 ──────────────────────────────────────────

def _shell_exec(command: str, timeout: int = 15) -> str:
    # [安全禁用] 此功能因命令注入风险已被禁用
    # 原因: shell=True + bash -c 允许任意命令执行
    # 替代方案: 使用特定的工具函数而非通用shell执行
    return "[安全策略] shell_exec 功能已禁用（命令注入风险）。如需执行命令，请使用特定的工具函数。"


# _register("shell_exec", "执行 shell 命令并返回输出", {
#     "command": {"type": "string", "description": "要执行的 bash 命令"},
#     "timeout": {"type": "integer", "description": "超时秒数（默认15）"},
# }, ["command"], _shell_exec)


# ── 文件读取 ──────────────────────────────────────────

def _file_read(path: str, lines: int = 100, offset: int = 0) -> str:
    from pathlib import Path as _P
    try:
        p = _P(path).expanduser().resolve()
        _ALLOWED_DIRS = ["/home/ai/LingYi", "/home/ai/LingFlow", "/home/ai/LingClaude", "/tmp"]
        real = str(p)
        if not any(real.startswith(d) for d in _ALLOWED_DIRS):
            return f"安全策略: 不允许读取此路径 ({path})"
        if not p.exists():
            return f"文件不存在: {path}"
        if not p.is_file():
            return f"不是文件: {path}"
        if p.stat().st_size > 2_000_000:
            return f"文件太大（{p.stat().st_size // 1024}KB），请用 shell_exec + head/tail 查看"
        text = p.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        total = len(all_lines)
        start = max(0, offset)
        end = min(total, start + lines)
        selected = all_lines[start:end]
        header = f"文件: {p} (共{total}行, 显示 {start+1}-{end})\n"
        numbered = "\n".join(f"{start+i+1:6d}| {line}" for i, line in enumerate(selected))
        return header + numbered
    except Exception as e:
        return f"读取失败: {e}"


_register("file_read", "读取文件内容（带行号）", {
    "path": {"type": "string", "description": "文件路径"},
    "lines": {"type": "integer", "description": "读取行数（默认100）"},
    "offset": {"type": "integer", "description": "起始行号偏移（默认0）"},
}, ["path"], _file_read)


# ── Git 状态 ──────────────────────────────────────────

def _git_status(project: str = "") -> str:
    import os
    import subprocess
    projects = {
        "灵通": "/home/ai/LingFlow",
        "灵知": "/home/ai/zhineng-knowledge-system",
        "灵依": "/home/ai/LingYi",
        "灵克": "/home/ai/LingClaude",
        "灵极优": "/home/ai/LingMinOpt",
        "灵研": "/home/ai/lingresearch",
        "灵信": "/home/ai/LingMessage",
    }
    if project:
        matched = {k: v for k, v in projects.items() if project.lower() in k.lower() or project.lower() in v.lower()}
        if not matched:
            return "未找到项目: " + project
    else:
        matched = projects

    results = []
    for name, path in matched.items():
        if not os.path.isdir(path):
            results.append(f"{name}: 目录不存在")
            continue
        try:
            branch = subprocess.run(["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
                                    capture_output=True, text=True, timeout=5).stdout.strip()
            short = subprocess.run(["git", "-C", path, "log", "-1", "--format=%h %s (%cr)"],
                                   capture_output=True, text=True, timeout=5).stdout.strip()
            dirty = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                                   capture_output=True, text=True, timeout=5).stdout.strip()
            dirty_count = len([ln for ln in dirty.splitlines() if ln.strip()]) if dirty else 0
            status = f"修改{dirty_count}个文件" if dirty_count else "干净"
            results.append(f"{name} [{branch}] {status}\n  最近: {short}")
        except Exception as e:
            results.append(f"{name}: 查询失败 ({e})")
    return "\n\n".join(results)


_register("git_status", "查看灵字辈项目的 Git 状态", {
    "project": {"type": "string", "description": "项目名称（可选，留空查看全部）"},
}, executor=_git_status)


# ── 代码统计 ──────────────────────────────────────────

def _code_stats(project: str = "") -> str:
    import subprocess
    import os

    projects = {
        "灵通": "/home/ai/LingFlow",
        "灵知": "/home/ai/zhineng-knowledge-system",
        "灵依": "/home/ai/LingYi",
        "灵克": "/home/ai/LingClaude",
        "灵极优": "/home/ai/LingMinOpt",
        "灵研": "/home/ai/lingresearch",
        "灵通问道": "/home/ai/lingtongask",
        "灵犀": "/home/ai/Ling-term-mcp",
        "灵信": "/home/ai/LingMessage",
        "灵扬": "/home/ai/LingYang",
        "灵通官网": "/home/ai/lingflow.top",
    }

    if project:
        pl = project.lower()
        matched = {k: v for k, v in projects.items() if pl in k.lower() or pl in v.lower()}
        if not matched:
            return "未找到项目: " + project + "。可用: " + ", ".join(projects.keys())
    else:
        matched = projects

    results = []
    total = 0
    for name, path in matched.items():
        if not os.path.isdir(path):
            continue
        try:
            r = subprocess.run(
                ["find", path, "-name", "*.py",
                 "-not", "-path", "*/__pycache__/*",
                 "-not", "-path", "*/.git/*",
                 "-not", "-path", "*/venv/*",
                 "-not", "-path", "*/.venv/*",
                 "-not", "-path", "*/site-packages/*",
                 "-not", "-path", "*/node_modules/*",
                 "-exec", "wc", "-l", "{}", "+"],
                capture_output=True, text=True, timeout=15
            )
            count = 0
            for line in r.stdout.strip().split("\n"):
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    count += int(parts[0])
            total += count
            results.append((name, count))
        except Exception:
            results.append((name, 0))

    if not project:
        out = ["灵字辈代码量统计（Python）：", ""]
        for n, c in sorted(results, key=lambda x: -x[1]):
            out.append("  " + n + "：" + format(c, ",") + " 行")
        out.append("")
        out.append("  总计：" + format(total, ",") + " 行")
        return "\n".join(out)
    else:
        n, c = results[0] if results else ("?", 0)
        return n + " Python代码量：" + format(c, ",") + " 行"


_register("code_stats", "统计灵字辈项目的代码量", {
    "project": {"type": "string", "description": "项目名称（可选，留空统计全部）"},
}, executor=_code_stats)


# ── UI-TARS 视觉-操作闭环 ─────────────────────────────────

def _ui_capture_screenshot(url: str, width: int = 1920, height: int = 1080) -> str:
    """捕获网页截图"""
    try:
        from .ui_tars import capture_screenshot
        result = capture_screenshot(url, width=width, height=height)
        return f"截图成功: {result['image_path']} ({result['width']}x{result['height']})"
    except Exception as e:
        return f"截图失败: {e}"


def _ui_ocr(image_path: str, x: int | None = None, y: int | None = None,
            width: int | None = None, height: int | None = None) -> str:
    """识别图像中的文字（OCR）"""
    try:
        from .ui_tars import ocr_image
        region = None
        if x is not None and y is not None and width is not None and height is not None:
            region = {"x": x, "y": y, "width": width, "height": height}

        result = ocr_image(image_path, region=region)
        lines = [
            f"识别成功（置信度: {result['confidence']:.2f}）",
            f"文字内容:\n{result['text']}",
        ]
        if result.get('lines'):
            lines.append(f"\n逐行识别 ({len(result['lines'])} 行):")
            for i, line in enumerate(result['lines'][:10], 1):
                lines.append(f"  {i}. {line.get('text', '')}")

        return "\n".join(lines)
    except Exception as e:
        return f"OCR识别失败: {e}"


def _ui_find_elements(image_path: str, element_type: str = "button", text: str | None = None) -> str:
    """在图像中查找UI元素"""
    try:
        from .ui_tars import find_elements
        result = find_elements(image_path, element_type=element_type, text=text)

        if result['count'] == 0:
            return f"未找到类型为 {element_type} 的元素"

        lines = [f"找到 {result['count']} 个 {element_type} 元素:"]
        for i, elem in enumerate(result['elements'][:10], 1):
            bbox = elem.get('bbox', {})
            lines.append(f"  {i}. 位置: ({bbox.get('x', 0)}, {bbox.get('y', 0)}) "
                        f"大小: {bbox.get('width', 0)}x{bbox.get('height', 0)}")
            if elem.get('text'):
                lines.append(f"      文字: {elem['text']}")
            if elem.get('confidence'):
                lines.append(f"      置信度: {elem['confidence']:.2f}")

        return "\n".join(lines)
    except Exception as e:
        return f"元素查找失败: {e}"


def _ui_analyze(image_path: str) -> str:
    """分析UI界面状态"""
    try:
        from .ui_tars import analyze_ui_state
        result = analyze_ui_state(image_path)

        lines = [
            f"UI类型: {result['ui_type']}",
            f"摘要: {result['summary']}",
        ]
        if result.get('text_content'):
            lines.append(f"\n主要文字内容:\n{result['text_content'][:500]}")
        if result.get('interactive_elements'):
            lines.append(f"\n可交互元素 ({len(result['interactive_elements'])} 个):")
            for elem in result['interactive_elements'][:5]:
                lines.append(f"  - {elem.get('type', 'unknown')}: {elem.get('text', elem.get('selector', ''))}")

        return "\n".join(lines)
    except Exception as e:
        return f"UI分析失败: {e}"


def _ui_status() -> str:
    """获取UI-TARS服务状态"""
    try:
        from .ui_tars import get_status
        status = get_status()

        lines = ["UI-TARS服务状态:"]
        lines.append(f"  启用: {'是' if status['enabled'] else '否'}")
        lines.append(f"  可用: {'是' if status['available'] else '否'}")
        lines.append(f"  API地址: {status['api_url']}")
        if status.get('version'):
            lines.append(f"  版本: {status['version']}")

        if status['enabled'] and not status['available']:
            lines.append("\n⚠️ UI功能已启用但服务不可用，请检查UI-TARS服务状态")

        return "\n".join(lines)
    except Exception as e:
        return f"状态查询失败: {e}"


_register("ui_capture", "捕获网页截图", {
    "url": {"type": "string", "description": "目标网页URL"},
    "width": {"type": "integer", "description": "截图宽度（默认1920）"},
    "height": {"type": "integer", "description": "截图高度（默认1080）"},
}, ["url"], _ui_capture_screenshot)

_register("ui_ocr", "识别图像中的文字（OCR）", {
    "image_path": {"type": "string", "description": "图像文件路径"},
    "x": {"type": "integer", "description": "识别区域左上角X坐标（可选）"},
    "y": {"type": "integer", "description": "识别区域左上角Y坐标（可选）"},
    "width": {"type": "integer", "description": "识别区域宽度（可选）"},
    "height": {"type": "integer", "description": "识别区域高度（可选）"},
}, ["image_path"], _ui_ocr)

_register("ui_find", "在图像中查找UI元素", {
    "image_path": {"type": "string", "description": "图像文件路径"},
    "element_type": {"type": "string", "description": "元素类型（button/text/image/link）"},
    "text": {"type": "string", "description": "元素文本内容（可选）"},
}, ["image_path", "element_type"], _ui_find_elements)

_register("ui_analyze", "分析UI界面状态", {
    "image_path": {"type": "string", "description": "图像文件路径"},
}, ["image_path"], _ui_analyze)

_register("ui_status", "获取UI-TARS服务状态", {}, executor=_ui_status)
