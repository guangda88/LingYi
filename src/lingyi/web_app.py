"""灵依 WebUI — 真正的私人助理界面。

提供完整的 REST API + WebSocket 聊天，暴露所有灵依能力：
- 仪表盘（日程、备忘、项目、情报）
- 智能聊天（完整系统提示词 + 意图路由 + 指令执行）
- 数据管理（备忘、日程、项目、计划、偏好）
"""

import asyncio
import base64
import json
import logging
import os
import secrets
import tempfile
import time
import uuid
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
if not _DASHSCOPE_API_KEY:
    _key_file = Path.home() / ".dashscope_api_key"
    if _key_file.exists():
        _DASHSCOPE_API_KEY = _key_file.read_text(encoding="utf-8").strip()

_GLM_API_KEY = os.environ.get(
    "GLM_CODING_PLAN_KEY",
    os.environ.get("GLM_API_KEY", "")
)
if not _GLM_API_KEY:
    for _kf in [
        Path.home() / ".glm_api_key",
        Path("/home/ai/zhineng-knowledge-system/.env"),
    ]:
        if _kf.exists() and _kf.suffix == ".env":
            for _line in _kf.read_text(encoding="utf-8").splitlines():
                _line = _line.strip()
                if _line.startswith("GLM_CODING_PLAN_KEY="):
                    _GLM_API_KEY = _line.split("=", 1)[1].strip()
                    break
                if _line.startswith("GLM_API_KEY=") and not _GLM_API_KEY:
                    _GLM_API_KEY = _line.split("=", 1)[1].strip()
            if _GLM_API_KEY:
                break
        elif _kf.exists():
            _GLM_API_KEY = _kf.read_text(encoding="utf-8").strip()
            break
_GLM_BASE_URL = os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4")
_GLM_MODEL = os.environ.get("GLM_MODEL", "glm-5.1")

# 系统提示词缓存（5分钟过期）
_SYSTEM_PROMPT_CACHE: dict[str, tuple[str, datetime]] = {}
_CACHE_EXPIRE_SECONDS = 300

def _get_cached_system_prompt() -> str:
    """获取缓存的系统提示词，如果缓存过期则重新构建"""
    from .agent import _SYSTEM_PROMPT_BASE

    cache_key = "system_prompt"
    now = datetime.now()

    if cache_key in _SYSTEM_PROMPT_CACHE:
        cached_prompt, cache_time = _SYSTEM_PROMPT_CACHE[cache_key]
        if (now - cache_time).total_seconds() < _CACHE_EXPIRE_SECONDS:
            return cached_prompt

    # 缓存未命中或过期，重新构建
    prompt = _build_system_prompt_impl(_SYSTEM_PROMPT_BASE)
    _SYSTEM_PROMPT_CACHE[cache_key] = (prompt, now)
    return prompt

def _build_system_prompt_impl(base_prompt: str) -> str:
    """实际构建系统提示词的实现"""
    parts = [base_prompt, ""]

    parts.append("\n【附加工具能力】除了上面提到的工具，你还拥有以下能力：")
    parts.append("  - file_read: 读取文件内容（带行号，限白名单目录）")
    parts.append("  - git_status: 查看 Git 仓库状态")
    parts.append("  - code_stats: 统计灵字辈项目代码量")
    parts.append("  - search_web: 搜索网络")
    parts.append("  - check_github / check_pypi: 查开源项目数据")
    parts.append("  - ai_news: 获取最新 AI 行业新闻")
    parts.append("")
    parts.append("【灵字辈 GitHub 仓库映射】")
    parts.append("  - 灵通 LingFlow: guangda88/lingflow")
    parts.append("  - 灵克 LingClaude: guangda88/lingclaude")
    parts.append("  - 灵依 LingYi: guangda88/lingyi")
    parts.append("  - 灵知 LingZhi: guangda88/zhineng-knowledge-system")
    parts.append("当灵通老师提到某个灵字辈项目的GitHub时，你应该直接调用 check_github，不要问仓库名。")

    try:
        from .schedule import format_today
        today = format_today()
        if today:
            parts.append("【今日日程】\n" + today)
    except Exception:
        pass

    try:
        from .memo import list_memos
        memos = list_memos()
        if memos:
            recent = memos[:5]
            lines = [f"  - {m.content}" for m in recent]
            parts.append("【最近备忘】\n" + "\n".join(lines))
    except Exception:
        pass

    try:
        from .plan import format_plan_week
        wp = format_plan_week()
        if wp:
            parts.append("【本周计划】\n" + wp)
    except Exception:
        pass

    try:
        from .project import list_projects
        active = list_projects(status="active")
        if active:
            lines = [f"  - {p.name}({p.alias}) {p.priority} [{p.category}]" for p in active]
            parts.append("【活跃项目】\n" + "\n".join(lines))
    except Exception:
        pass

    try:
        from .briefing import collect_all
        briefing_data = collect_all()
        lines = []
        for key, label in [("lingzhi", "灵知"), ("lingflow", "灵通"), ("lingclaude", "灵克"), ("lingtongask", "灵通问道")]:
            info = briefing_data.get(key, {})
            if info.get("available"):
                lines.append(f"  - {label}: 在线")
            else:
                lines.append(f"  - {label}: 离线")
        lingclaude_info = briefing_data.get("lingclaude", {})
        sessions = lingclaude_info.get("sessions", 0)
        if sessions:
            lines.append(f"  - 灵克开发会话: {sessions} 条")
        lingflow_info = briefing_data.get("lingflow", {})
        fb = lingflow_info.get("feedback_count", 0)
        fb_open = lingflow_info.get("feedback_open", 0)
        lines.append(f"  - 灵通反馈: {fb} 条（{fb_open} 条待处理）")
        parts.append("【灵字辈实时状态】（以下为全部数据，没有更多了）\n" + "\n".join(lines))
    except Exception:
        pass

    try:
        from .lingmessage import list_discussions
        discussions = list_discussions(status="open")
        if discussions:
            lines = []
            for d in discussions[:5]:
                participants = ", ".join(d.get("participants", []))
                msg_count = d.get("message_count", 0)
                lines.append(f"  - {d['topic']} (参与者: {participants}, {msg_count}条消息)")
            parts.append("【灵信待处理讨论】\n" + "\n".join(lines))
    except Exception:
        pass

    return "\n\n".join(parts)


def _call_llm_with_fallback(client: Any, messages: list, tools_schema: list | None) -> tuple:
    """按优先级尝试模型，429/余额不足时自动降级"""
    from .llm_utils import call_llm_with_fallback as _do_fallback
    return _do_fallback(client, messages, tools_schema, primary_model=_GLM_MODEL)

_SESSIONS: dict[str, datetime] = {}
_PERSISTENT_TOKEN_PATH = Path.home() / ".lingyi" / ".web_tokens"
_MAX_SESSIONS = 200

_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SEC = 300


def _cleanup_sessions():
    """清理过期会话，超过上限时裁剪最旧的"""
    now = datetime.now()
    expired = [t for t, exp in _SESSIONS.items() if exp < now]
    for t in expired:
        del _SESSIONS[t]
    if len(_SESSIONS) > _MAX_SESSIONS:
        by_age = sorted(_SESSIONS.items(), key=lambda x: x[1])
        for t, _ in by_age[: len(_SESSIONS) - _MAX_SESSIONS]:
            del _SESSIONS[t]


def _check_login_rate(ip: str) -> bool:
    """检查IP是否超过登录尝试限制。返回True表示允许"""
    now = time.time()
    attempts = _LOGIN_ATTEMPTS[ip]
    _LOGIN_ATTEMPTS[ip] = [t for t in attempts if now - t < _LOGIN_WINDOW_SEC]
    if len(_LOGIN_ATTEMPTS[ip]) >= _LOGIN_MAX_ATTEMPTS:
        return False
    return True


def _record_login_attempt(ip: str):
    _LOGIN_ATTEMPTS[ip].append(time.time())


def _load_persistent_tokens() -> dict[str, str]:
    try:
        if _PERSISTENT_TOKEN_PATH.exists():
            data = json.loads(_PERSISTENT_TOKEN_PATH.read_text("utf-8"))
            now = datetime.now().isoformat()
            return {k: v for k, v in data.items() if v > now}
    except Exception:
        pass
    return {}


def _save_persistent_tokens(tokens: dict[str, str]):
    try:
        _PERSISTENT_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PERSISTENT_TOKEN_PATH.write_text(json.dumps(tokens, ensure_ascii=False, indent=2), "utf-8")
    except Exception as exc:
        logger.error(f"Failed to save persistent tokens: {exc}")


def _add_persistent_token(token: str, expires: datetime):
    tokens = _load_persistent_tokens()
    tokens[token] = expires.isoformat()
    _save_persistent_tokens(tokens)


def _remove_persistent_token(token: str):
    tokens = _load_persistent_tokens()
    tokens.pop(token, None)
    _save_persistent_tokens(tokens)


def _check_auth(token: str) -> bool:
    if not token:
        return False
    exp = _SESSIONS.get(token)
    if exp:
        if datetime.now() > exp:
            del _SESSIONS[token]
            return False
        return True
    persistent = _load_persistent_tokens()
    exp_str = persistent.get(token)
    if exp_str:
        if datetime.now() < datetime.fromisoformat(exp_str):
            return True
        else:
            _remove_persistent_token(token)
    return False


def _get_web_password() -> str:
    try:
        import json as _json
        presets_path = Path.home() / ".lingyi" / "presets.json"
        if presets_path.exists():
            data = _json.loads(presets_path.read_text("utf-8"))
            if data.get("web_password"):
                return str(data["web_password"])
    except Exception:
        pass
    return ""


def _generate_and_save_password() -> str:
    import string
    import json as _json
    chars = string.ascii_lowercase + string.digits
    pwd = "".join(secrets.choice(chars) for _ in range(8))
    try:
        presets_path = Path.home() / ".lingyi" / "presets.json"
        data = {}
        if presets_path.exists():
            data = _json.loads(presets_path.read_text("utf-8"))
        data["web_password"] = pwd
        presets_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as exc:
        logger.error(f"Failed to save web_password: {exc}")
    return pwd


def _hash_password(pwd: str) -> str:
    """使用 bcrypt 安全哈希密码（自动加盐）"""
    try:
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(pwd.encode('utf-8'), salt).decode('utf-8')
    except ImportError:
        # 如果 bcrypt 不可用，回退到 PBKDF2（仍比 SHA256 安全）
        import hashlib
        import os
        salt = os.urandom(32)
        # 使用 PBKDF2-HMAC-SHA256
        key = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt, 100000)
        return f"pbkdf2:{salt.hex()}:{key.hex()}"


def _check_password(pwd: str, hashed: str) -> bool:
    """验证密码"""
    try:
        import bcrypt
        return bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('utf-8'))
    except ImportError:
        # PBKDF2 回退验证
        if hashed.startswith("pbkdf2:"):
            import hashlib
            parts = hashed.split(":")
            salt = bytes.fromhex(parts[1])
            key = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt, 100000)
            return key.hex() == parts[2]
        # 旧 SHA256 兼容（不推荐，迁移后应删除）
        return hashlib.sha256(pwd.encode()).hexdigest() == hashed


def _serialize(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def create_app(password: str | None = None):
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from starlette.requests import Request

    app = FastAPI(title="灵依 — 私人助理")

    _web_pwd_hash = ""
    if password:
        _web_pwd_hash = _hash_password(password)
    else:
        stored = _get_web_password()
        if stored:
            _web_pwd_hash = _hash_password(stored)
        else:
            new_pwd = _generate_and_save_password()
            _web_pwd_hash = _hash_password(new_pwd)
            import click
            click.echo(click.style(f"\n🔐 Web UI 密码已生成: {new_pwd}", fg="green", bold=True))
            click.echo(click.style("   已保存到 ~/.lingyi/presets.json", fg="dim"))
            click.echo(click.style("   用 lingyi pref set web_password 新密码 可修改\n", fg="dim"))
    _auth_enabled = bool(_web_pwd_hash)

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        # 公开端点列表（明确列出）
        public_paths = {"/", "/login"}
        public_prefixes = {
            "/api/login", "/static", "/favicon",
            "/api/lingmessage/notify", "/api/lingmessage",
            "/api/discuss", "/api/dashboard",
            "/api/memos", "/api/schedules",
            "/api/projects", "/api/plans",
            "/api/preferences", "/api/briefing",
            "/api/status", "/api/models",
            "/api/usage", "/api/council",
            "/api/logs",
            "/ws/"
        }

        # 检查是否是公开路径
        if path in public_paths or any(path.startswith(prefix) for prefix in public_prefixes):
            return await call_next(request)

        # 认证未启用时的行为
        if not _auth_enabled:
            # 开发环境：记录警告但仍允许访问
            logger.warning(f"认证未启用，允许访问: {path}")
            return await call_next(request)

        # 需要认证
        token = request.cookies.get("lingyi_token", "")
        if not _check_auth(token):
            return JSONResponse({"error": "未授权"}, status_code=401)
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8900", "http://127.0.0.1:8900"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        if not _auth_enabled:
            return HTMLResponse('<script>location.href="/"</script>')
        return HTMLResponse((_TEMPLATE_DIR / "login.html").read_text("utf-8"))

    @app.post("/api/login")
    async def api_login(request: Request):
        ip = request.client.host if request.client else "unknown"
        if not _check_login_rate(ip):
            return JSONResponse(
                {"error": "登录尝试过多，请5分钟后重试"},
                status_code=429,
            )

        body = await request.json()
        pwd = body.get("password", "")
        remember = body.get("remember", False)
        if _check_password(pwd, _web_pwd_hash):
            token = secrets.token_hex(32)
            _cleanup_sessions()
            if remember:
                expires = datetime.now() + timedelta(days=30)
                _SESSIONS[token] = expires
                _add_persistent_token(token, expires)
                resp = JSONResponse({"ok": True})
                resp.set_cookie("lingyi_token", token, max_age=2592000, samesite="lax")
            else:
                _SESSIONS[token] = datetime.now() + timedelta(hours=24)
                resp = JSONResponse({"ok": True})
                resp.set_cookie("lingyi_token", token, max_age=86400, samesite="lax")
            return resp
        _record_login_attempt(ip)
        return JSONResponse({"error": "密码错误"}, status_code=403)

    @app.post("/api/logout")
    async def api_logout(request: Request):
        token = request.cookies.get("lingyi_token", "")
        if token:
            _SESSIONS.pop(token, None)
            _remove_persistent_token(token)
        resp = JSONResponse({"ok": True})
        resp.set_cookie("lingyi_token", "", max_age=0)
        return resp

    # ── 静态页面 ──────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if _auth_enabled:
            token = request.cookies.get("lingyi_token", "")
            if not _check_auth(token):
                return HTMLResponse('<script>location.href="/login"</script>')
        return HTMLResponse((_TEMPLATE_DIR / "index.html").read_text("utf-8"))

    # ── 仪表盘 API ────────────────────────────────────────
    @app.get("/api/dashboard")
    async def dashboard():
        from .schedule import today_schedules, format_day_cn, format_slot_cn
        from .memo import list_memos
        from .project import list_projects
        from .briefing import collect_all

        today_items = today_schedules()
        memos = list_memos()
        projects = list_projects(status="active")

        try:
            briefing = collect_all()
        except Exception:
            briefing = {}

        ling_status = []
        for key, label in [("lingzhi", "灵知"), ("lingflow", "灵通"), ("lingclaude", "灵克"), ("lingtongask", "灵通问道")]:
            info = briefing.get(key, {})
            ling_status.append({
                "name": label,
                "online": info.get("available", False),
                "detail": _briefing_detail(key, info),
            })

        return JSONResponse({
            "date": date.today().isoformat(),
            "weekday": format_day_cn(date.today().strftime("%A")),
            "today_schedules": [
                {
                    "id": s.id, "type": s.type,
                    "slot": format_slot_cn(s.time_slot),
                    "description": s.description or s.type,
                }
                for s in today_items
            ],
            "recent_memos": [{"id": m.id, "content": m.content, "time": m.created_at} for m in memos[:5]],
            "active_projects": [
                {
                    "id": p.id, "name": p.name, "alias": p.alias,
                    "priority": p.priority, "category": p.category,
                    "description": p.description, "status": p.status,
                }
                for p in projects[:8]
            ],
            "ling_family": ling_status,
        })

    def _briefing_detail(key, info):
        if not info.get("available"):
            return "离线"
        if key == "lingzhi":
            return f"查询 {info.get('total_queries', 0)}"
        if key == "lingflow":
            return f"反馈 {info.get('feedback_count', 0)}"
        if key == "lingclaude":
            return f"会话 {info.get('sessions', 0)}"
        if key == "lingtongask":
            return f"评论 {info.get('total_comments', 0)}"
        return ""

    # ── 备忘 API ──────────────────────────────────────────
    @app.get("/api/memos")
    async def api_memos():
        from .memo import list_memos
        return JSONResponse([_serialize(m) for m in list_memos()])

    @app.post("/api/memos")
    async def api_add_memo(request: dict):
        from .memo import add_memo
        content = request.get("content", "").strip()
        if not content:
            return JSONResponse({"error": "内容不能为空"}, status_code=400)
        m = add_memo(content)
        return JSONResponse(_serialize(m))

    @app.delete("/api/memos/{memo_id}")
    async def api_delete_memo(memo_id: int):
        from .memo import delete_memo
        ok = delete_memo(memo_id)
        return JSONResponse({"ok": ok})

    # ── 日程 API ──────────────────────────────────────────
    @app.get("/api/schedules")
    async def api_schedules(schedule_type: str | None = None):
        from .schedule import list_schedules, format_day_cn, format_slot_cn
        items = list_schedules(schedule_type=schedule_type, active_only=True)
        return JSONResponse([
            {
                "id": s.id, "type": s.type, "day": s.day,
                "day_cn": format_day_cn(s.day), "slot_cn": format_slot_cn(s.time_slot),
                "description": s.description, "active": s.is_active,
            }
            for s in items
        ])

    @app.get("/api/schedules/today")
    async def api_schedules_today():
        from .schedule import today_schedules, format_slot_cn
        items = today_schedules()
        return JSONResponse([
            {"id": s.id, "type": s.type, "slot": format_slot_cn(s.time_slot), "desc": s.description or s.type}
            for s in items
        ])

    @app.get("/api/schedules/week")
    async def api_schedules_week():
        from .schedule import week_schedules, format_day_cn, format_slot_cn
        data = week_schedules()
        result = {}
        for day, items in data.items():
            result[day] = {
                "cn": format_day_cn(day),
                "items": [
                    {"type": s.type, "slot": format_slot_cn(s.time_slot), "desc": s.description or s.type}
                    for s in items
                ],
            }
        return JSONResponse(result)

    # ── 项目 API ──────────────────────────────────────────
    @app.get("/api/projects")
    async def api_projects(status: str | None = None):
        from .project import list_projects
        items = list_projects(status=status)
        return JSONResponse([_serialize(p) for p in items])

    def _git_info(repo_name: str) -> dict:
        import subprocess as _sp
        home = Path.home()
        candidates = [home / repo_name, home / "lingtongask" / repo_name, home / "LingYi" / repo_name]
        repo_dir = next((c for c in candidates if (c / ".git").is_dir()), None)
        if not repo_dir:
            return {"repo_found": False}
        try:
            def _git(*args: str) -> str:
                return _sp.run(["git", "-C", str(repo_dir)] + list(args),
                               capture_output=True, text=True, timeout=5).stdout.strip()

            branch = _git("branch", "--show-current")
            last_msg = _git("log", "-1", "--format=%s")[:80]
            last_time = _git("log", "-1", "--format=%ar")
            last_iso = _git("log", "-1", "--format=%aI")
            tag = _git("describe", "--tags", "--abbrev=0") or ""
            dirty_raw = _git("status", "--porcelain")
            dirty = len([line for line in dirty_raw.split("\n") if line.strip()])
            week_commits_raw = _git("log", "--oneline", "--since=7 days ago")
            week_commits = len([line for line in week_commits_raw.split("\n") if line.strip()])

            return {
                "repo_found": True, "repo_path": str(repo_dir), "branch": branch,
                "last_commit": last_msg, "last_commit_time": last_time,
                "last_commit_iso": last_iso, "tag": tag, "dirty_files": dirty,
                "week_commits": week_commits,
            }
        except Exception:
            return {"repo_found": True, "repo_path": str(repo_dir)}

    @app.get("/api/projects/live")
    async def api_projects_live():
        from .project import list_projects
        items = list_projects()

        try:
            from .lingmessage import list_discussions as _list_disc
            threads = _list_disc()
        except Exception:
            threads = []

        _PROJECT_ALIASES = {
            "LingFlow": ["lingflow", "灵通"], "LingClaude": ["lingclaude", "灵克"],
            "灵知系统": ["lingzhi", "灵知"], "LingYi": ["lingyi", "灵依"],
            "lingtongask": ["lingtongask", "灵通问道"], "Ling-term-mcp": ["lingterm", "灵犀"],
            "LingMinOpt": ["lingminopt", "灵极优"], "zhineng-bridge": ["zhibridge", "智桥"],
            "lingresearch": ["lingresearch", "灵研"],
            "zhineng-knowledge-system": ["lingzhi", "灵知"],
        }

        results = []
        for p in items:
            d = _serialize(p)
            d["git"] = _git_info(p.repo)
            if d["git"].get("tag"):
                d["version"] = d["git"]["tag"]

            aliases = _PROJECT_ALIASES.get(p.name, [p.name.lower(), p.alias])
            related = []
            for t in threads:
                topic = t.get("topic", "")
                tags = t.get("tags", [])
                text = (topic + " " + " ".join(tags)).lower()
                if any(a.lower() in text for a in aliases):
                    related.append({
                        "id": t.get("id") or t.get("thread_id", ""),
                        "topic": topic[:60],
                        "messages": t.get("message_count", 0),
                        "updated": t.get("updated_at", ""),
                    })
            related.sort(key=lambda x: x.get("updated", ""), reverse=True)
            d["discussions"] = related[:3]
            results.append(d)

        return JSONResponse(results)

    @app.get("/api/projects/{name}")
    async def api_project_detail(name: str):
        from .project import show_project
        p = show_project(name)
        if not p:
            return JSONResponse({"error": "项目不存在"}, status_code=404)
        return JSONResponse(_serialize(p))

    # ── 日志 API ────────────────────────────────────────────
    _LOG_SOURCES: dict[str, list[str]] = {
        "灵依": ["/tmp/lingyi.log", "/tmp/lingyi_web.log"],
        "灵克": ["/tmp/lingclaude.log", "/tmp/lingclaude-api.log"],
        "灵知": ["/tmp/lingzhi.log", "/tmp/lingzhi-auto.log"],
        "灵研究": ["/tmp/lingresearch.log"],
        "灵民调": ["/tmp/lingminopt.log"],
        "灵养": ["/tmp/lingyang_responder.log"],
        "智桥": ["/home/ai/zhineng-bridge/logs/lingflow_*.log"],
        "灵通": ["/home/ai/LingFlow/logs/lingflow_*.log"],
        "系统监控": ["/home/ai/zhineng-knowledge-system/logs/monitor.log",
                     "/home/ai/zhineng-knowledge-system/logs/docker_monitor.log"],
        "议事厅告警": [str(Path.home() / ".lingyi" / "logs" / "council_health.jsonl")],
        "VNC": ["/tmp/x11vnc.log"],
    }

    _ERROR_KEYWORDS = ("ERROR", "error", "Exception", "Traceback", "CRITICAL",
                       "WARN", "WARNING", "告警", "失败", "异常", "超时")

    @app.get("/api/logs")
    async def api_logs(source: str = "灵依", lines: int = 30, errors_only: bool = False):
        import glob
        paths = _LOG_SOURCES.get(source, [])
        if not paths:
            return JSONResponse({"error": f"未知日志源: {source}", "sources": list(_LOG_SOURCES.keys())}, status_code=400)
        all_paths: list[str] = []
        for p in paths:
            all_paths.extend(sorted(glob.glob(p)))
        if not all_paths:
            return JSONResponse({"source": source, "lines": []})
        result_lines: list[str] = []
        for fp in reversed(all_paths):
            try:
                with open(fp, "r", errors="replace") as f:
                    file_lines = f.readlines()
                    result_lines.extend(file_lines[-lines:])
            except Exception:
                result_lines.append(f"[无法读取: {fp}]")
        if errors_only:
            result_lines = [ln for ln in result_lines
                           if any(kw in ln for kw in _ERROR_KEYWORDS)]
            result_lines = result_lines[-lines:]
        return JSONResponse({"source": source, "lines": result_lines, "sources": list(_LOG_SOURCES.keys())})

    # ── 计划 API ──────────────────────────────────────────
    @app.get("/api/plans")
    async def api_plans():
        from .plan import list_plans
        return JSONResponse([_serialize(p) for p in list_plans()])

    @app.post("/api/plans")
    async def api_add_plan(request: dict):
        from .plan import add_plan
        content = request.get("content", "").strip()
        if not content:
            return JSONResponse({"error": "内容不能为空"}, status_code=400)
        area = request.get("area", "编程")
        project = request.get("project", "")
        p = add_plan(content=content, area=area, project=project)
        return JSONResponse(_serialize(p))

    # ── 偏好 API ──────────────────────────────────────────
    @app.get("/api/preferences")
    async def api_preferences():
        from .pref import list_prefs
        return JSONResponse([{"key": k, "value": v} for k, v in list_prefs()])

    @app.post("/api/preferences")
    async def api_set_pref(request: dict):
        from .pref import set_pref
        key = request.get("key", "").strip()
        value = request.get("value", "").strip()
        if not key:
            return JSONResponse({"error": "key不能为空"}, status_code=400)
        set_pref(key, value)
        return JSONResponse({"ok": True})

    # ── 会话管理 API ───────────────────────────────────────
    @app.get("/api/sessions")
    async def api_list_sessions():
        """列出所有聊天会话"""
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT session_id, title, created_at, updated_at, message_count "
                "FROM chat_sessions ORDER BY updated_at DESC"
            ).fetchall()
            conn.close()
            sessions = [{
                "session_id": r["session_id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "message_count": r["message_count"],
            } for r in rows]
            return JSONResponse({"sessions": sessions})
        except Exception as exc:
            logger.error(f"Failed to list sessions: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.post("/api/sessions")
    async def api_create_session(request: dict):
        """创建新会话"""
        title = request.get("title", "新对话").strip() or "新对话"
        session_id = str(uuid.uuid4())
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            conn.execute(
                "INSERT INTO chat_sessions (session_id, title, message_count) VALUES (?, ?, 0)",
                (session_id, title)
            )
            conn.commit()
            conn.close()
            return JSONResponse({"session_id": session_id, "title": title})
        except Exception as exc:
            logger.error(f"Failed to create session: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.delete("/api/sessions/{session_id}")
    async def api_delete_session(session_id: str):
        """删除会话"""
        if session_id == "default":
            return JSONResponse({"error": "默认会话不能删除"}, status_code=403)
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            # 删除会话的所有消息
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            # 删除会话元数据
            conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
            return JSONResponse({"ok": True})
        except Exception as exc:
            logger.error(f"Failed to delete session: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.put("/api/sessions/{session_id}/title")
    async def api_update_session_title(session_id: str, request: dict):
        """更新会话标题"""
        title = request.get("title", "").strip()
        if not title:
            return JSONResponse({"error": "标题不能为空"}, status_code=400)
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE session_id = ?",
                (title, session_id)
            )
            conn.commit()
            conn.close()
            return JSONResponse({"ok": True, "title": title})
        except Exception as exc:
            logger.error(f"Failed to update session title: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.delete("/api/messages/{message_id}")
    async def api_delete_message(message_id: int):
        """删除单条消息"""
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            # 获取消息所属会话
            row = conn.execute(
                "SELECT session_id FROM chat_messages WHERE id = ?",
                (message_id,)
            ).fetchone()
            if not row:
                conn.close()
                return JSONResponse({"error": "消息不存在"}, status_code=404)

            session_id = row[0]
            # 删除消息
            conn.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))
            # 更新会话消息计数
            conn.execute(
                "UPDATE chat_sessions SET message_count = message_count - 1 "
                "WHERE session_id = ? AND message_count > 0",
                (session_id,)
            )
            conn.commit()
            conn.close()
            return JSONResponse({"ok": True})
        except Exception as exc:
            logger.error(f"Failed to delete message: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ── 情报 API ──────────────────────────────────────────
    @app.get("/api/briefing")
    async def api_briefing():
        from .briefing import collect_all, format_briefing
        data = collect_all()
        return JSONResponse({"raw": data, "formatted": format_briefing(data)})

    # ── 状态 API ──────────────────────────────────────────
    @app.get("/api/status")
    async def api_status():
        from datetime import datetime
        from .llm_utils import get_model_status
        return JSONResponse({
            "service": "灵依",
            "uptime_port": 8900,
            "bridge_connected": bool(_bridge_ws),
            "direct_ws_clients": len(_active_ws),
            "tools_count": 29,
            "cognitive_state": {
                "last_push_date": _last_push_date,
                "last_reminder_hour": _last_reminder_hour,
                "last_lingmsg_count": _last_lingmsg_count,
            },
            "models": get_model_status(),
            "timestamp": datetime.now().isoformat(),
        })

    # ── 灵信 API ──────────────────────────────────────────

    @app.get("/api/models")
    async def api_models():
        from .llm_utils import get_model_status
        return JSONResponse(get_model_status())

    @app.get("/api/usage")
    async def api_usage():
        from .llm_utils import get_usage_stats
        return JSONResponse(get_usage_stats())

    @app.post("/api/models")
    async def api_models_probe(request: Request):
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        action = body.get("action", "") or request.query_params.get("action", "")
        if action == "probe":
            from .llm_utils import probe_premium_models, get_model_status
            probe = probe_premium_models()
            results = []
            for model, st in probe.items():
                results.append({"model": model, "available": st == "available", "reason": "" if st == "available" else st})
            return JSONResponse({"results": results, "status": get_model_status()})
        return JSONResponse({"error": "unknown action"}, status_code=400)

    @app.get("/api/lingmessage")
    async def api_lingmessage(status: str | None = "open"):
        from .lingmessage import list_discussions
        return JSONResponse(list_discussions(status=status))

    @app.get("/api/lingmessage/{disc_id}")
    async def api_lingmessage_detail(disc_id: str):
        from .lingmessage import _load_discussion, _get_store
        disc = _load_discussion(_get_store(), disc_id)
        if not disc:
            return JSONResponse({"error": "讨论不存在"}, status_code=404)
        return JSONResponse(disc)

    @app.post("/api/lingmessage/send")
    async def api_lingmessage_send(request: dict):
        from .lingmessage import send_message
        topic = request.get("topic", "").strip()
        content = request.get("content", "").strip()
        from_id = request.get("from_id", "guangda").strip() or "guangda"
        if not topic or not content:
            return JSONResponse({"error": "topic和content必填"}, status_code=400)
        msg = send_message(from_id, topic, content)
        return JSONResponse(_serialize(msg))

    @app.post("/api/lingmessage/notify")
    async def api_lingmessage_notify(request: Request):
        client_host = request.client.host if request.client else ""
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        body = await request.json()
        from_id = body.get("from", "?")
        topic = body.get("topic", "?")
        logger.info(f"灵信通知: {from_id} 在 [{topic}] 发了新消息")
        preview = f"收到灵信: {_project_cn(from_id)} 在「{topic}」发了新消息"
        await _push_to_all("lingmessage", preview)
        return JSONResponse({"received": True})

    @app.get("/api/lingmessage/inbox/{member_id}")
    async def api_inbox_get(member_id: str):
        """获取成员的未读消息。"""
        from .lingmessage import get_inbox
        messages = get_inbox(member_id)
        return JSONResponse({"member_id": member_id, "unread_count": len(messages), "messages": messages})

    @app.post("/api/lingmessage/inbox/{member_id}/read")
    async def api_inbox_mark_read(member_id: str, request: dict):
        """标记消息为已读。"""
        body = await request.json()
        message_id = body.get("message_id", "")
        if not message_id:
            return JSONResponse({"error": "message_id必填"}, status_code=400)
        from .lingmessage import mark_inbox_read
        success = mark_inbox_read(member_id, message_id)
        return JSONResponse({"success": success})

    @app.post("/api/lingmessage/inbox/{member_id}/clean")
    async def api_inbox_clean(member_id: str, request: dict):
        """清理已读消息。"""
        body = await request.json()
        days = body.get("days", 7)
        from .lingmessage import clean_read_inbox
        deleted = clean_read_inbox(member_id, days)
        return JSONResponse({"deleted": deleted})

    def _project_cn(pid: str) -> str:
        _names = {
            "lingflow": "灵通", "lingclaude": "灵克", "lingzhi": "灵知",
            "lingyi": "灵依", "lingtongask": "灵通问道", "lingterm": "灵犀",
            "lingminopt": "灵极优", "lingresearch": "灵研", "zhibridge": "智桥",
            "lingyang": "灵扬", "guangda": "广大老师",
        }
        return _names.get(pid, pid)

    @app.get("/api/lingmessage/delivery/{message_id}")
    async def api_delivery_status(message_id: str):
        """获取消息的送达状态详情"""
        from .lingmessage import get_delivery_status
        status = get_delivery_status(message_id)
        return JSONResponse(status)

    # ── 端点健康监控 API ─────────────────────────────────

    @app.get("/api/health/endpoints")
    async def api_health_endpoints():
        """获取所有端点的健康状态"""
        from .endpoint_monitor import get_health_summary
        return JSONResponse(get_health_summary())

    @app.post("/api/health/check")
    async def api_health_check():
        """立即检查所有端点健康状态"""
        from .endpoint_monitor import check_all_endpoints, get_health_summary
        check_all_endpoints()
        return JSONResponse(get_health_summary())

    @app.get("/api/health/summary")
    async def api_health_summary():
        """获取健康状态摘要（文本格式）"""
        from .endpoint_monitor import get_health_summary, format_health_summary
        summary = get_health_summary()
        text = format_health_summary(summary)
        return JSONResponse({"summary": text, "data": summary})

    # ── 统一通信层 API ─────────────────────────────────

    @app.get("/api/unified/online")
    async def api_unified_online():
        """获取所有成员的统一在线状态"""
        from .unified_comm import UnifiedOnlineDetector, UNIFIED_MEMBERS
        detector = UnifiedOnlineDetector()
        online_status = detector.check_all_online()

        result = {}
        for member_id, online in online_status.items():
            member = UNIFIED_MEMBERS.get(member_id)
            if member:
                result[member_id] = {
                    "name": member.name,
                    "online": online,
                }

        return JSONResponse(result)

    @app.post("/api/unified/send")
    async def api_unified_send(request: Request):
        """统一发送消息（智能路由）"""
        body = await request.json()
        sender_id = body.get("sender_id", "lingyi")
        recipient_id = body.get("recipient_id")
        topic = body.get("topic")
        content = body.get("content")
        message_type = body.get("message_type", "discussion")

        if not recipient_id or not topic or not content:
            return JSONResponse(
                {"error": "recipient_id, topic, and content are required"},
                status_code=400
            )

        from .unified_comm import UnifiedOnlineDetector, UnifiedMessageRouter, UNIFIED_MEMBERS

        # 验证发送者和接收者
        if sender_id not in UNIFIED_MEMBERS:
            return JSONResponse({"error": f"Unknown sender: {sender_id}"}, status_code=400)
        if recipient_id not in UNIFIED_MEMBERS:
            return JSONResponse({"error": f"Unknown recipient: {recipient_id}"}, status_code=400)

        # 发送消息
        detector = UnifiedOnlineDetector()
        router = UnifiedMessageRouter(detector)
        result = router.send_message(sender_id, recipient_id, topic, content, message_type)

        return JSONResponse({
            "success": result.success,
            "message_id": result.message_id,
            "channel": result.channel,
            "error": result.error,
            "response_time_ms": result.response_time_ms,
        })

    @app.get("/api/unified/queue/{recipient_id}")
    async def api_unified_queue(recipient_id: str):
        """获取指定收件人的离线队列"""
        from .unified_comm import OfflineMessageQueue, UNIFIED_MEMBERS

        if recipient_id not in UNIFIED_MEMBERS:
            return JSONResponse({"error": f"Unknown recipient: {recipient_id}"}, status_code=400)

        queue = OfflineMessageQueue()
        messages = queue.dequeue(recipient_id)

        return JSONResponse({
            "recipient_id": recipient_id,
            "queued_count": len(messages),
            "messages": [asdict(msg) for msg in messages],
        })

    @app.get("/api/unified/queue-stats")
    async def api_unified_queue_stats():
        """获取所有队列统计"""
        from .unified_comm import OfflineMessageQueue

        queue = OfflineMessageQueue()
        stats = queue.get_queue_stats()

        total = sum(stats.values())
        return JSONResponse({
            "total_queued": total,
            "by_recipient": stats,
        })

    @app.post("/api/unified/retry")
    async def api_unified_retry():
        """手动触发队列重试"""
        from .unified_comm import OfflineMessageQueue, UnifiedOnlineDetector, UnifiedMessageRouter

        queue = OfflineMessageQueue()
        detector = UnifiedOnlineDetector()
        router = UnifiedMessageRouter(detector)

        stats = queue.retry_send(router, detector)

        return JSONResponse({
            "success": True,
            "stats": stats,
        })

    # ── WebSocket 智能聊天 ─────────────────────────────────
    _DB_PATH = Path.home() / ".lingyi" / "lingyi.db"

    def _ensure_chat_table():
        import sqlite3
        conn = sqlite3.connect(str(_DB_PATH))
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, id)")
        
        # 创建会话元数据表
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新对话',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_count INTEGER DEFAULT 0
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)")
        conn.commit()
        conn.close()

    def _load_recent_chat(session_id: str, limit: int = 40) -> list[dict]:
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            rows = conn.execute(
                "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
            conn.close()
            return [{"role": r, "content": c, "created_at": t} for r, c, t in reversed(rows)]
        except Exception:
            return []

    def _save_chat_message(session_id: str | None = None, role: str = "", content: str = ""):
        if session_id is None:
            session_id = "default"
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            conn.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
            # 更新会话元数据
            conn.execute(
                "INSERT INTO chat_sessions (session_id, title, message_count, updated_at) "
                "VALUES (?, '新对话', 1, CURRENT_TIMESTAMP) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP",
                (session_id,)
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error(f"Failed to save chat message: {exc}")

    _ensure_chat_table()

    _MAX_CONVERSATION = 60

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        raw_token = websocket.cookies.get("lingyi_token", "")
        if not raw_token:
            raw_token = websocket.query_params.get("token", "")
        if _auth_enabled and not _check_auth(raw_token):
            await websocket.close(code=4001, reason="unauthorized")
            return
        await websocket.accept()

        # 从查询参数获取session_id，如果没有则创建新会话
        initial_session_id = websocket.query_params.get("session_id", "")
        if not initial_session_id:
            initial_session_id = str(uuid.uuid4())
        
        current_session_id = initial_session_id
        local_conv: list[dict] = _load_recent_chat(current_session_id, 20)

        # Send current session info to client
        await websocket.send_json({"type": "session_joined", "session_id": current_session_id})

        # Send recent history to client
        if local_conv:
            await websocket.send_json({"type": "history", "session_id": current_session_id, "messages": local_conv[-20:]})

        async def _keepalive():
            try:
                while True:
                    await asyncio.sleep(30)
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        _active_ws.discard(websocket)
                        break
            except asyncio.CancelledError:
                pass

        _active_ws.add(websocket)
        ka_task = asyncio.create_task(_keepalive())
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=300)
                except asyncio.TimeoutError:
                    logger.info("WebSocket receive timed out after 300s")
                    break
                msg = json.loads(raw)
                mtype = msg.get("type", "text")

                if mtype == "ping":
                    continue

                if mtype == "switch_session":
                    # 切换会话
                    new_session_id = msg.get("session_id", "")
                    if new_session_id:
                        current_session_id = new_session_id
                        local_conv = _load_recent_chat(current_session_id, 20)
                        await websocket.send_json({
                            "type": "session_switched",
                            "session_id": current_session_id,
                            "messages": local_conv[-20:]
                        })
                    continue

                if mtype == "text":
                    user_text = msg.get("text", "").strip()
                    no_tts = msg.get("no_tts", False)
                    if not user_text:
                        continue
                    local_conv.append({"role": "user", "content": user_text})
                    _save_chat_message(current_session_id, "user", user_text)
                    reply = await _smart_reply(user_text, local_conv)
                    local_conv.append({"role": "assistant", "content": reply})
                    if len(local_conv) > _MAX_CONVERSATION:
                        local_conv[:] = local_conv[-_MAX_CONVERSATION:]
                    _save_chat_message(current_session_id, "assistant", reply)
                    audio_b64 = None if no_tts else await _do_tts(reply)
                    await websocket.send_json({"type": "reply", "text": reply, "audio": audio_b64})

                elif mtype == "audio":
                    audio_b64_data = msg.get("data", "")
                    no_tts = msg.get("no_tts", False)
                    if not audio_b64_data:
                        continue
                    try:
                        recognized = await asyncio.wait_for(_do_stt(audio_b64_data), timeout=30)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"type": "reply", "text": "语音识别超时，请重试", "audio": None})
                        continue
                    if not recognized:
                        await websocket.send_json({"type": "reply", "text": "未识别到语音，请重试", "audio": None})
                        continue
                    await websocket.send_json({"type": "recognized", "text": recognized})
                    local_conv.append({"role": "user", "content": recognized})
                    _save_chat_message(current_session_id, "user", recognized)
                    reply = await _smart_reply(recognized, local_conv)
                    local_conv.append({"role": "assistant", "content": reply})
                    if len(local_conv) > _MAX_CONVERSATION:
                        local_conv[:] = local_conv[-_MAX_CONVERSATION:]
                    _save_chat_message(current_session_id, "assistant", reply)
                    audio_b64 = None if no_tts else await _do_tts(reply)
                    await websocket.send_json({"type": "reply", "text": reply, "audio": audio_b64})

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected")
        except Exception as exc:
            logger.error(f"WebSocket error: {exc}")
        finally:
            ka_task.cancel()
            _active_ws.discard(websocket)

    async def _smart_reply(text: str, conv: list[dict] | None = None) -> str:
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: _chat_llm_with_context(text, conv)),
                timeout=60,
            )
        except asyncio.TimeoutError:
            logger.warning("_smart_reply timed out after 60s")
            return "⚠️ AI 响应超时，请稍后再试。"

    def _chat_llm_with_context(text: str, conv: list[dict] | None = None) -> str:
        from openai import OpenAI
        from .tools import get_tools, execute_tool

        logger.info(f"Starting chat with text: {text[:50]}...")
        try:
            client = OpenAI(api_key=_GLM_API_KEY, base_url=_GLM_BASE_URL, max_retries=0)
        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            return f"⚠️ 无法连接到AI服务：{str(e)}"

        try:
            system_prompt = _build_system_prompt()
            context = conv if conv is not None else []
            messages = [{"role": "system", "content": system_prompt}] + context[-20:]
            tools_schema = get_tools()
            logger.info(f"System prompt length: {len(system_prompt)}, context messages: {len(context)}, tools: {len(tools_schema)}")
        except Exception as e:
            logger.error(f"Failed to build prompt: {e}")
            return f"⚠️ 构建提示词失败：{str(e)}"

        _err_count = 0
        for attempt in range(5):
            logger.info(f"Attempt {attempt + 1}/5...")
            try:
                resp, _used_model = _call_llm_with_fallback(client, messages, tools_schema)
                logger.info(f"Got response from model: {_used_model}")

                if not resp.choices or len(resp.choices) == 0:
                    logger.error(f"Empty response from model: {resp}")
                    continue

                choice = resp.choices[0]
                msg = choice.message

                if msg.tool_calls:
                    logger.info(f"Tool calls detected: {len(msg.tool_calls)} tools")
                    import json as _json
                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        logger.info(f"Executing tool: {tool_name}")
                        try:
                            args = _json.loads(tc.function.arguments or "{}")
                        except Exception:
                            args = {}
                        try:
                            result = execute_tool(tool_name, args)
                            logger.info(f"Tool {tool_name} result length: {len(result)}")
                        except Exception as e:
                            logger.error(f"Tool {tool_name} execution failed: {e}")
                            result = f"工具执行失败: {str(e)}"
                        messages.append({"role": "assistant", "content": None, "tool_calls": [{
                            "id": tc.id, "type": "function",
                            "function": {"name": tool_name, "arguments": tc.function.arguments}
                        }]})
                        messages.append({"role": "tool", "content": result,
                                        "tool_call_id": tc.id, "name": tool_name})
                    continue

                content = msg.content or ""
                if content:
                    logger.info(f"Got response content, length: {len(content)}")
                    return content.strip()
                else:
                    logger.warning(f"Empty content in message: {msg}")
                    continue
            except Exception as e:
                _err_count += 1
                logger.error(f"GLM call failed (attempt {attempt + 1}, error {_err_count}): {type(e).__name__}: {e}")
                if _err_count >= 3:
                    from .llm_utils import friendly_error
                    return friendly_error(e)
                time.sleep(2 * _err_count)
                continue

    def _build_system_prompt() -> str:
        """获取系统提示词（带缓存）"""
        return _get_cached_system_prompt()

    # ── TTS/STT ───────────────────────────────────────────
    async def _do_tts(text: str) -> str | None:
        from .tts import clean_text_for_speech
        cleaned = clean_text_for_speech(text)
        if not cleaned:
            return None
        result = await _tts_edge(cleaned)
        if result:
            return result
        return await _tts_dashscope(cleaned)

    async def _tts_edge(text: str) -> str | None:
        try:
            import edge_tts
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            import os
            os.close(fd)
            comm = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            await comm.save(tmp_path)
            with open(tmp_path, "rb") as f:
                audio = f.read()
            os.unlink(tmp_path)
            if audio and len(audio) > 100:
                return base64.b64encode(audio).decode("ascii")
            return None
        except Exception as exc:
            logger.error(f"edge-tts failed: {exc}")
            return None

    async def _tts_dashscope(text: str) -> str | None:
        try:
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer
            dashscope.api_key = _DASHSCOPE_API_KEY
            synth = SpeechSynthesizer(model="cosyvoice-v2", voice="longxiaocheng_v2")
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, lambda: synth.call(text))
            if audio and len(audio) > 100:
                return base64.b64encode(audio).decode("ascii")
            return None
        except Exception as exc:
            logger.error(f"DashScope TTS failed: {exc}")
            return None

    async def _do_stt(audio_b64: str) -> str | None:
        result = await _stt_whisper(audio_b64)
        if result:
            return result
        return await _stt_dashscope(audio_b64)

    async def _stt_whisper(audio_b64: str) -> str | None:
        try:
            import whisper
            if not hasattr(_stt_whisper, '_model'):
                _stt_whisper._model = whisper.load_model("base")
            model = _stt_whisper._model
            audio_bytes = base64.b64decode(audio_b64)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(audio_bytes)
            tmp.close()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: model.transcribe(tmp.name, language="zh"))
            Path(tmp.name).unlink(missing_ok=True)
            return result.get("text", "").strip() or None
        except Exception as exc:
            logger.error(f"Whisper STT failed: {exc}")
            return None

    async def _stt_dashscope(audio_b64: str) -> str | None:
        try:
            import dashscope
            from dashscope.audio.asr import Recognition, RecognitionCallback
            dashscope.api_key = _DASHSCOPE_API_KEY
            audio_bytes = base64.b64decode(audio_b64)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(audio_bytes)
            tmp.close()
            texts = []
            done_event = asyncio.Event()

            class CB(RecognitionCallback):
                def on_complete(self):
                    done_event.set()
                def on_error(self, result):
                    done_event.set()
                def on_event(self, result):
                    try:
                        d = json.loads(str(result))
                        t = d.get("output", {}).get("sentence", {}).get("text", "")
                        if t:
                            texts.append(t)
                    except Exception:
                        pass

            recognition = Recognition(model="paraformer-realtime-v2", format="wav", sample_rate=16000, callback=CB())
            def _run():
                recognition.start()
                with open(tmp.name, "rb") as f:
                    recognition.send_audio_frame(f.read())
                recognition.stop()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _run)
            Path(tmp.name).unlink(missing_ok=True)
            return "".join(texts).strip() or None
        except Exception as exc:
            logger.error(f"DashScope STT failed: {exc}")
            return None

    # ── 主动推送 ───────────────────────────────────────────
    _active_ws: set = set()
    _last_push_date: str | None = None
    _last_reminder_hour: int | None = None
    _last_lingmsg_count: int = 0
    _cognitive_state: dict = {
        "last_observation": "",
        "pending_alerts": [],
        "user_habits": {},
    }
    _bridge_ws: list = []  # 智桥 WebSocket 连接（由 bridge_client 填充）
    _council_scan_interval: int = 300  # 议事厅扫描间隔（秒）
    _last_council_scan: float = 0

    @app.post("/api/push/briefing")
    async def api_push_briefing():
        if not _active_ws and not _bridge_ws:
            return JSONResponse({"sent": False, "reason": "no active connections"})
        text = await _build_briefing_push()
        await _push_to_all("briefing", text)
        return JSONResponse({"sent": True, "text_length": len(text)})

    @app.post("/api/push/reminder")
    async def api_push_reminder():
        if not _active_ws and not _bridge_ws:
            return JSONResponse({"sent": False, "reason": "no active connections"})
        text = await _build_reminder_push()
        if not text:
            return JSONResponse({"sent": False, "reason": "nothing to remind"})
        await _push_to_all("reminder", text)
        return JSONResponse({"sent": True})

    async def _build_briefing_push() -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _build_briefing_push_sync)

    def _build_briefing_push_sync() -> str:
        parts = [f"🌅 灵通老师早上好！{date.today().isoformat()} 灵依晨报：\n"]
        try:
            from .schedule import format_today
            today = format_today()
            if today:
                parts.append("【今日日程】\n" + today)
        except Exception:
            pass
        try:
            from .memo import list_memos
            memos = list_memos()
            if memos:
                parts.append("【备忘】\n" + "\n".join(f"  - {m.content}" for m in memos[:5]))
        except Exception:
            pass
        try:
            from .briefing import collect_all, format_briefing
            data = collect_all()
            brief = format_briefing(data)
            if brief:
                parts.append("【灵字辈状态】\n" + brief)
        except Exception:
            pass
        return "\n\n".join(parts)

    async def _build_reminder_push() -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _build_reminder_push_sync)

    def _build_reminder_push_sync() -> str:
        try:
            from .schedule import today_schedules, format_slot_cn
            from datetime import datetime
            now = datetime.now()
            upcoming = []
            for s in today_schedules():
                desc = s.description or s.type
                slot = format_slot_cn(s.time_slot)
                upcoming.append(f"  - {slot} {desc}")
            if upcoming:
                return f"⏰ 今日提醒（{now.strftime('%H:%M')}）：\n" + "\n".join(upcoming)
        except Exception:
            pass
        return ""

    async def _auto_push_loop():
        """认知循环: 观察 → 思考 → 行动 + 议事厅扫描"""
        nonlocal _last_council_scan
        while True:
            await asyncio.sleep(120)  # every 2 minutes
            try:
                if _active_ws or _bridge_ws:
                    observation = _cognitive_observe()
                    actions = _cognitive_think(observation)
                    for action in actions:
                        await _cognitive_act(action)
            except Exception as exc:
                logger.error(f"Cognitive loop error: {exc}")

            try:
                import time as _time
                now_ts = _time.time()
                if now_ts - _last_council_scan >= _council_scan_interval:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, _council_scan_sync)
                    _last_council_scan = now_ts
                    if result.get("woken_members"):
                        names = ", ".join(result["woken_members"])
                        await _push_to_all("council", f"🏛️ 议事厅活动：{names} 被唤醒参与讨论")
            except Exception as exc:
                logger.error(f"Council scan error: {exc}")

    def _cognitive_observe() -> dict:
        from datetime import datetime
        now = datetime.now()
        obs = {
            "weekday": now.weekday(),
            "hour": now.hour,
            "minute": now.minute,
            "date_str": now.strftime("%Y-%m-%d"),
            "is_weekend": now.weekday() >= 5,
        }
        try:
            from .schedule import today_schedules
            obs["schedules_today"] = len(today_schedules())
        except Exception:
            obs["schedules_today"] = 0
        try:
            from .memo import list_memos
            obs["memo_count"] = len(list_memos())
        except Exception:
            obs["memo_count"] = 0
        try:
            from .lingmessage import list_discussions
            discs = list_discussions(status="open")
            obs["open_discussions"] = len(discs)
        except Exception:
            obs["open_discussions"] = 0
        return obs

    def _cognitive_think(obs: dict) -> list[dict]:
        nonlocal _last_push_date, _last_lingmsg_count
        from datetime import datetime
        actions = []
        now = datetime.now()
        hour = obs["hour"]

        if 7 <= hour < 8 and _last_push_date != obs["date_str"] and obs["schedules_today"] > 0:
            actions.append({"type": "morning_briefing", "priority": "high"})
            _last_push_date = obs["date_str"]

        slot_hours = {"morning": 8, "afternoon": 14, "evening": 19}
        for slot_name, slot_hour in slot_hours.items():
            reminder_key = f"reminded_{obs['date_str']}_{slot_name}"
            if hour == slot_hour - 1 and now.minute >= 30 and _cognitive_state.get(reminder_key) is None:
                if obs["schedules_today"] > 0:
                    actions.append({"type": "schedule_reminder", "slot": slot_name, "priority": "normal"})
                    _cognitive_state[reminder_key] = True

        if obs["open_discussions"] > _last_lingmsg_count and _last_lingmsg_count > 0:
            diff = obs["open_discussions"] - _last_lingmsg_count
            if diff > 0:
                actions.append({"type": "new_lingmsg", "count": diff, "priority": "low"})
        _last_lingmsg_count = obs["open_discussions"]

        reminder_key_evening = f"evening_{obs['date_str']}"
        if hour == 21 and _cognitive_state.get(reminder_key_evening) is None:
            actions.append({"type": "evening_summary", "priority": "low"})
            _cognitive_state[reminder_key_evening] = True

        return actions

    async def _cognitive_act(action: dict):
        atype = action["type"]
        if atype == "morning_briefing":
            text = await _build_briefing_push()
            await _push_to_all("morning_briefing", text)
            _save_chat_message("assistant", f"[晨报推送] {text[:100]}...")

        elif atype == "schedule_reminder":
            slot = action.get("slot", "")
            slot_cn = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}.get(slot, slot)
            text = f"⏰ 灵通老师，{slot_cn}的日程快到了，注意准备。"
            await _push_to_all("reminder", text)

        elif atype == "new_lingmsg":
            count = action.get("count", 1)
            text = f"📬 有 {count} 条新的灵信讨论待处理。"
            await _push_to_all("lingmessage", text)

        elif atype == "evening_summary":
            text = _build_evening_summary()
            if text:
                await _push_to_all("evening_summary", text)
                _save_chat_message("assistant", f"[晚间总结] {text[:100]}...")

    def _council_scan_sync() -> dict:
        from .council import council_scan
        return council_scan()

    def _build_evening_summary() -> str:
        parts = ["🌙 灵通老师，今天的总结：\n"]
        try:
            from .schedule import format_today
            today = format_today()
            if today:
                parts.append("【今日日程】\n" + today)
        except Exception:
            pass
        try:
            from .plan import list_plans
            done_today = [p for p in list_plans(status="done") if hasattr(p, 'updated_at')]
            if done_today:
                parts.append(f"【已完成】{len(done_today)} 项计划")
        except Exception:
            pass
        try:
            from .lingmessage import list_discussions
            discs = list_discussions(status="open")
            if discs:
                parts.append(f"【灵信】{len(discs)} 个待处理讨论")
        except Exception:
            pass
        parts.append("\n明天见！早点休息 🌙")
        return "\n\n".join(parts)

    async def _push_to_all(category: str, text: str):
        """推送给所有连接的用户（直接 WebSocket + 智桥）。"""
        for ws in list(_active_ws):
            try:
                await ws.send_json({"type": "push", "category": category, "text": text})
            except Exception:
                _active_ws.discard(ws)
        if _bridge_ws:
            from .bridge_client import bridge_push
            await bridge_push(_bridge_ws[0], text, category)

    _bridge_conv: list[dict] = _load_recent_chat("default", 20)

    async def _bridge_on_chat(text: str, request_id: str, from_client: str, audio: str | None) -> tuple[str, str | None]:
        """处理来自智桥的用户消息。"""
        loop = asyncio.get_event_loop()
        _bridge_conv.append({"role": "user", "content": text})
        _save_chat_message("default", "user", text)
        reply = await loop.run_in_executor(None, lambda t: _chat_llm_with_context(t, _bridge_conv), text)
        _bridge_conv.append({"role": "assistant", "content": reply})
        if len(_bridge_conv) > _MAX_CONVERSATION:
            _bridge_conv[:] = _bridge_conv[-_MAX_CONVERSATION:]
        _save_chat_message("default", "assistant", reply)
        audio_b64 = await _do_tts(reply)
        return reply, audio_b64

    async def _bridge_on_registered(ws):
        _bridge_ws.clear()
        _bridge_ws.append(ws)

    async def _run_bridge_connector():
        from .bridge_client import connect_to_bridge
        await connect_to_bridge(on_chat=_bridge_on_chat, on_registered=_bridge_on_registered)

    @app.get("/api/council/status")
    async def api_council_status():
        from .council import council_status
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, council_status)
        return JSONResponse(info)

    @app.post("/api/council/scan")
    async def api_council_scan():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _council_scan_sync)
        return JSONResponse(result)

    @app.post("/api/council/wake")
    async def api_council_wake(request: Request):
        from .council import wake_member
        body = await request.json()
        member_id = body.get("member_id", "")
        disc_id = body.get("disc_id", "")
        if not member_id or not disc_id:
            return JSONResponse({"error": "需要 member_id 和 disc_id"}, status_code=400)
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, lambda: wake_member(member_id, disc_id))
        if reply:
            from .lingmessage import send_message
            disc_data = await loop.run_in_executor(None, lambda: _load_discussion_for_council(disc_id))
            if disc_data:
                await loop.run_in_executor(
                    None,
                    lambda: send_message(from_id=member_id, topic=disc_data["topic"], content=reply),
                )
            return JSONResponse({"replied": True, "content": reply[:200]})
        return JSONResponse({"replied": False, "reason": "已发言/已关闭/API不可用"})

    @app.post("/api/verification/check")
    async def api_verification_check(request: dict):
        """验证断言是否符合约束"""
        from .constraint_layer import Assertion, ConstraintLayer

        member_id = request.get("member_id", "")
        assertion_type = request.get("assertion_type", "")
        content = request.get("content", "")
        tool_call = request.get("tool_call")

        if not member_id or not assertion_type or not content:
            return JSONResponse({"error": "member_id, assertion_type, and content are required"}, status_code=400)

        constraint = ConstraintLayer()
        assertion = Assertion(
            member_id=member_id,
            assertion_type=assertion_type,
            content=content,
            tool_call=tool_call
        )

        result = constraint.verify_assertion(assertion)

        return JSONResponse({
            "passed": result.passed,
            "reason": result.reason,
            "checks": result.checks,
            "recommendation": result.recommendation,
            "requires_fallback": result.requires_fallback
        })

    @app.get("/api/verification/stats")
    async def api_verification_stats(days: int = 7):
        """获取验证统计"""
        from .constraint_layer import ConstraintLayer

        constraint = ConstraintLayer()
        stats = constraint.get_verification_stats(days)

        return JSONResponse(stats)

    @app.get("/api/verification/log")
    async def api_verification_log(days: int = 7, member_id: str | None = None):
        """获取验证日志"""
        from .constraint_layer import VerificationMonitor
        from datetime import datetime

        monitor = VerificationMonitor()
        logs = monitor._load_logs()

        # 筛选时间范围
        cutoff = datetime.now().timestamp() - days * 86400
        recent_logs = [
            log for log in logs
            if datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff
        ]

        # 按成员ID筛选
        if member_id:
            recent_logs = [log for log in recent_logs if log["member_id"] == member_id]

        return JSONResponse(recent_logs)

    def _load_discussion_for_council(disc_id: str):
        from .lingmessage import _load_discussion, _get_store
        return _load_discussion(_get_store(), disc_id)

    YI_IDENTITY = (
        "你是灵依，灵字辈大家庭的私人AI助理和情报中枢。"
        "你的专长是用户需求洞察、情报整合、跨服务协调、日程管理。"
        "你是灵家议事厅的客厅管理员，负责统筹讨论节奏和成员协作。"
        "讨论风格：统筹、用户视角，关注情报整合和用户需求。"
        "每条消息必须有实质内容。反对须附理由和替代方案。保持200-500字。"
        "你现在在灵家议事厅（客厅）参与讨论。直接发表你的观点。"
        "\n[语音转录容错] 用户输入可能来自语音转录，存在同音字/近音字错误。"
        "你必须理解真实语义，不要被字面错误误导。"
        "常见映射：林克=灵克、零字辈=灵字辈、林依=灵依、做/作、的/得/地、在/再。"
        "理解时以语义为准，回复时用正确的字词。不要纠正用户，直接理解并回复。"
    )

    def _yi_discuss_sync(topic: str, context: str, question: str) -> dict:
        from openai import OpenAI

        if not _GLM_API_KEY:
            return {"content": "", "model_used": "error", "source_type": "real"}

        prompt_parts = [YI_IDENTITY, "", f"当前议题：「{topic}」"]
        if context:
            prompt_parts.append(f"\n已有的讨论内容：\n{context[:3000]}\n")
            prompt_parts.append(
                "\n【要求】你必须：\n"
                "1. 引用之前某位发言者的具体论点（用「XX说……」的方式引用）\n"
                "2. 对该论点明确表态（同意/反对/补充），并给出你自己的理由\n"
                "3. 提出至少一个前人没有提到的新角度或新论据\n"
                "4. 不要重复已有讨论中说过的内容，不要泛泛而谈\n"
            )
        if question:
            prompt_parts.append(f"请回答：{question}")
        else:
            prompt_parts.append("请从你的角度——情报中枢和用户需求的角度——发表意见。")
        prompt = "\n".join(prompt_parts)

        try:
            client = OpenAI(api_key=_GLM_API_KEY, base_url=_GLM_BASE_URL)
            resp, model_used = _call_llm_with_fallback(
                client, [{"role": "user", "content": prompt}], None
            )
            content = (resp.choices[0].message.content or "").strip()
            if content:
                return {"content": content, "model_used": model_used, "source_type": "real"}
        except Exception as e:
            logger.error(f"灵依讨论失败: {e}")
        return {"content": "", "model_used": "error", "source_type": "real"}

    @app.post("/api/discuss")
    async def api_discuss(request: Request):
        body = await request.json()
        topic = body.get("topic", "").strip()
        if not topic:
            return JSONResponse({"error": "topic必填"}, status_code=400)
        context = body.get("context", "")
        question = body.get("question", "")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: _yi_discuss_sync(topic, context, question)
        )
        return JSONResponse({
            "agent_id": "lingyi",
            "agent_name": "灵依",
            "topic": topic,
            "content": result["content"],
            "source_type": result["source_type"],
            "model_used": result["model_used"],
            "tokens_used": len(result["content"]) // 2,
        })

    @app.on_event("startup")
    async def _start_push_task():
        asyncio.create_task(_auto_push_loop())
        asyncio.create_task(_run_bridge_connector())
        asyncio.create_task(_auto_health_check_loop())

    async def _auto_health_check_loop():
        """定期检查端点健康状态（每60秒）"""
        while True:
            try:
                await asyncio.sleep(60)
                from .endpoint_monitor import check_all_endpoints
                check_all_endpoints()
            except Exception as exc:
                logger.error(f"Health check loop error: {exc}")

    return app


def run_server(host: str = "0.0.0.0", port: int = 8900, ssl: bool = True, password: str | None = None):
    import uvicorn
    app = create_app(password=password)
    ssl_kwargs = {}
    if ssl:
        cert_dir = Path.home() / ".lingyi"
        cert_pem = cert_dir / "cert.pem"
        cert_key = cert_dir / "cert.key"
        if cert_pem.exists() and cert_key.exists():
            ssl_kwargs["ssl_keyfile"] = str(cert_key)
            ssl_kwargs["ssl_certfile"] = str(cert_pem)
    proto = "https" if ssl_kwargs else "http"
    import click
    click.echo(f"灵依 Web UI 启动: {proto}://{host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        timeout_keep_alive=120,
        ws_ping_interval=30,
        ws_ping_timeout=90,
        **ssl_kwargs
    )
