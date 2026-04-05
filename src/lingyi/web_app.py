"""灵依 WebUI — 真正的私人助理界面。

提供完整的 REST API + WebSocket 聊天，暴露所有灵依能力：
- 仪表盘（日程、备忘、项目、情报）
- 智能聊天（完整系统提示词 + 意图路由 + 指令执行）
- 数据管理（备忘、日程、项目、计划、偏好）
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
_SESSIONS: dict[str, datetime] = {}
_PERSISTENT_TOKEN_PATH = Path.home() / ".lingyi" / ".web_tokens"


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
    return hashlib.sha256(pwd.encode()).hexdigest()


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
        if path in ("/", "/login") or path.startswith("/api/login"):
            return await call_next(request)
        if not _auth_enabled:
            return await call_next(request)
        token = request.cookies.get("lingyi_token", "")
        if not _check_auth(token):
            return JSONResponse({"error": "未授权"}, status_code=401)
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        if not _auth_enabled:
            return HTMLResponse('<script>location.href="/"</script>')
        return HTMLResponse((_TEMPLATE_DIR / "login.html").read_text("utf-8"))

    @app.post("/api/login")
    async def api_login(request: Request):
        body = await request.json()
        pwd = body.get("password", "")
        remember = body.get("remember", False)
        if _hash_password(pwd) == _web_pwd_hash:
            token = secrets.token_hex(32)
            if remember:
                expires = datetime.now() + timedelta(days=30)
                _SESSIONS[token] = expires
                _add_persistent_token(token, expires)
                resp = JSONResponse({"ok": True})
                resp.set_cookie("lingyi_token", token, max_age=2592000, httponly=True, samesite="lax")
            else:
                _SESSIONS[token] = datetime.now() + timedelta(hours=24)
                resp = JSONResponse({"ok": True})
                resp.set_cookie("lingyi_token", token, max_age=86400, httponly=True, samesite="lax")
            return resp
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
    async def index():
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
                    "energy": p.energy_pct, "status": p.status,
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

    @app.get("/api/projects/{name}")
    async def api_project_detail(name: str):
        from .project import show_project
        p = show_project(name)
        if not p:
            return JSONResponse({"error": "项目不存在"}, status_code=404)
        return JSONResponse(_serialize(p))

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
            "timestamp": datetime.now().isoformat(),
        })

    # ── 灵信 API ──────────────────────────────────────────
    @app.get("/api/lingmessage")
    async def api_lingmessage(status: str | None = "open"):
        from .lingmessage import list_discussions
        return JSONResponse(list_discussions(status=status))

    @app.post("/api/lingmessage/send")
    async def api_lingmessage_send(request: dict):
        from .lingmessage import send_message
        topic = request.get("topic", "").strip()
        content = request.get("content", "").strip()
        if not topic or not content:
            return JSONResponse({"error": "topic和content必填"}, status_code=400)
        msg = send_message("lingyi", topic, content)
        return JSONResponse(_serialize(msg))

    @app.post("/api/lingmessage/notify")
    async def api_lingmessage_notify(request: dict):
        from_id = request.get("from", "?")
        topic = request.get("topic", "?")
        disc_id = request.get("discussion_id", "")
        logger.info(f"灵信通知: {from_id} 在 [{topic}] 发了新消息")
        preview = f"收到灵信: {_project_cn(from_id)} 在「{topic}」发了新消息"
        await _push_to_all("lingmessage", preview)
        return JSONResponse({"received": True})

    def _project_cn(pid: str) -> str:
        _names = {
            "lingflow": "灵通", "lingclaude": "灵克", "lingzhi": "灵知",
            "lingyi": "灵依", "lingtongask": "灵通问道", "lingterm": "灵犀",
            "lingminopt": "灵极优", "lingresearch": "灵研", "zhibridge": "智桥",
        }
        return _names.get(pid, pid)

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
        conn.commit()
        conn.close()

    def _load_recent_chat(limit: int = 40) -> list[dict]:
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            rows = conn.execute(
                "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
            return [{"role": r, "content": c} for r, c in reversed(rows)]
        except Exception:
            return []

    def _save_chat_message(role: str, content: str):
        import sqlite3
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            conn.execute("INSERT INTO chat_messages (role, content) VALUES (?, ?)", (role, content))
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error(f"Failed to save chat message: {exc}")

    _ensure_chat_table()

    _MAX_CONVERSATION = 60

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        raw_token = websocket.query_params.get("token", "")
        if _auth_enabled and not _check_auth(raw_token):
            await websocket.close(code=4001, reason="unauthorized")
            return
        await websocket.accept()

        local_conv: list[dict] = _load_recent_chat(20)

        # Send recent history to client
        if local_conv:
            await websocket.send_json({"type": "history", "messages": local_conv[-20:]})

        async def _keepalive():
            try:
                while True:
                    await asyncio.sleep(25)
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
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                mtype = msg.get("type", "text")

                if mtype == "ping":
                    continue

                if mtype == "text":
                    user_text = msg.get("text", "").strip()
                    if not user_text:
                        continue
                    local_conv.append({"role": "user", "content": user_text})
                    _save_chat_message("user", user_text)
                    reply = await _smart_reply(user_text, local_conv)
                    local_conv.append({"role": "assistant", "content": reply})
                    if len(local_conv) > _MAX_CONVERSATION:
                        local_conv[:] = local_conv[-_MAX_CONVERSATION:]
                    _save_chat_message("assistant", reply)
                    audio_b64 = await _do_tts(reply)
                    await websocket.send_json({"type": "reply", "text": reply, "audio": audio_b64})

                elif mtype == "audio":
                    audio_b64_data = msg.get("data", "")
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
                    _save_chat_message("user", recognized)
                    reply = await _smart_reply(recognized, local_conv)
                    local_conv.append({"role": "assistant", "content": reply})
                    if len(local_conv) > _MAX_CONVERSATION:
                        local_conv[:] = local_conv[-_MAX_CONVERSATION:]
                    _save_chat_message("assistant", reply)
                    audio_b64 = await _do_tts(reply)
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
        return await loop.run_in_executor(None, lambda: _chat_llm_with_context(text, conv))

    def _chat_llm_with_context(text: str, conv: list[dict] | None = None) -> str:
        import dashscope
        from dashscope import Generation
        from .tools import get_tools, execute_tool

        dashscope.api_key = _DASHSCOPE_API_KEY
        system_prompt = _build_system_prompt()
        context = conv if conv is not None else []
        messages = [{"role": "system", "content": system_prompt}] + context[-20:]
        tools_schema = get_tools()

        for _ in range(5):
            try:
                kwargs = {
                    "model": "qwen-turbo",
                    "messages": messages,
                    "result_format": "message",
                    "tools": tools_schema,
                }
                resp = Generation.call(**kwargs)
                if resp.status_code != 200:
                    break
                choices = resp.output.get("choices", [])
                if not choices:
                    break
                msg = choices[0]["message"]

                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        fn = tc["function"]
                        tool_name = fn["name"]
                        import json as _json
                        try:
                            args = _json.loads(fn.get("arguments", "{}"))
                        except Exception:
                            args = {}
                        result = execute_tool(tool_name, args)
                        messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                        messages.append({"role": "tool", "content": result, "name": tool_name})
                    continue

                content = msg.get("content", "")
                if content:
                    return content.strip()
            except Exception as e:
                logger.error(f"Qwen call failed: {e}")
                break
        return "抱歉，我刚才走神了，再说一遍？"

    def _build_system_prompt() -> str:
        from .agent import _SYSTEM_PROMPT_BASE
        parts = [_SYSTEM_PROMPT_BASE, ""]

        parts.append("\n【附加工具能力】除了上面提到的工具，你还拥有以下能力：")
        parts.append("  - shell_exec: 执行任意 shell 命令（查数据、看日志、跑脚本）")
        parts.append("  - file_read: 读取任意文件内容（带行号）")
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
                lines = [f"  - {p.name}({p.alias}) {p.priority} {p.energy_pct}% [{p.category}]" for p in active]
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
        """认知循环: 观察 → 思考 → 行动"""
        import datetime as _dt
        while True:
            await asyncio.sleep(120)  # every 2 minutes
            try:
                if not _active_ws and not _bridge_ws:
                    continue
                observation = _cognitive_observe()
                actions = _cognitive_think(observation)
                for action in actions:
                    await _cognitive_act(action)
            except Exception as exc:
                logger.error(f"Cognitive loop error: {exc}")

    def _cognitive_observe() -> dict:
        import datetime as _dt
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
        import datetime as _dt
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

    def _build_evening_summary() -> str:
        parts = [f"🌙 灵通老师，今天的总结：\n"]
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

    _bridge_conv: list[dict] = _load_recent_chat(20)

    async def _bridge_on_chat(text: str, request_id: str, from_client: str, audio: str | None) -> tuple[str, str | None]:
        """处理来自智桥的用户消息。"""
        loop = asyncio.get_event_loop()
        _bridge_conv.append({"role": "user", "content": text})
        _save_chat_message("user", text)
        reply = await loop.run_in_executor(None, lambda t: _chat_llm_with_context(t, _bridge_conv), text)
        _bridge_conv.append({"role": "assistant", "content": reply})
        if len(_bridge_conv) > _MAX_CONVERSATION:
            _bridge_conv[:] = _bridge_conv[-_MAX_CONVERSATION:]
        _save_chat_message("assistant", reply)
        audio_b64 = await _do_tts(reply)
        return reply, audio_b64

    async def _bridge_on_registered(ws):
        _bridge_ws.clear()
        _bridge_ws.append(ws)

    async def _run_bridge_connector():
        from .bridge_client import connect_to_bridge
        await connect_to_bridge(on_chat=_bridge_on_chat, on_registered=_bridge_on_registered)

    @app.on_event("startup")
    async def _start_push_task():
        asyncio.create_task(_auto_push_loop())
        asyncio.create_task(_run_bridge_connector())

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
    uvicorn.run(app, host=host, port=port, log_level="info", timeout_keep_alive=120, ws_ping_interval=30, ws_ping_timeout=60, **ssl_kwargs)
