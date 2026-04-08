"""灵依 WebUI — 真正的私人助理界面。

提供完整的 REST API + WebSocket 聊天，暴露所有灵依能力：
- 仪表盘（日程、备忘、项目、情报）
- 智能聊天（完整系统提示词 + 意图路由 + 指令执行）
- 数据管理（备忘、日程、项目、计划、偏好）
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

from ._web_app_auth import (
    check_auth, hash_password,
    get_web_password, generate_and_save_password,
)
from ._web_app_chat_store import (
    ensure_chat_table, load_recent_chat, save_chat_message,
    _DB_PATH as _CHAT_DB_PATH,
)
from ._web_app_chat_llm import chat_llm_with_context, smart_reply
from ._web_app_cognitive import (
    auto_push_loop, auto_health_check_loop, run_bridge_connector,
    MAX_CONVERSATION,
)
from ._web_app_routes_data import register_data_routes, _TEMPLATE_DIR
from ._web_app_routes_messaging import register_messaging_routes
from ._web_app_routes_council import register_council_routes
from ._web_app_routes_auth import register_auth_routes
from ._web_app_tts import do_tts, do_stt

logger = logging.getLogger(__name__)

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


def create_app(password: str | None = None):
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from starlette.requests import Request

    app = FastAPI(title="灵依 — 私人助理")

    _web_pwd_hash = ""
    if password:
        _web_pwd_hash = hash_password(password)
    else:
        stored = get_web_password()
        if stored:
            _web_pwd_hash = hash_password(stored)
        else:
            new_pwd = generate_and_save_password()
            _web_pwd_hash = hash_password(new_pwd)
            import click
            click.echo(click.style(f"\n🔐 Web UI 密码已生成: {new_pwd}", fg="green", bold=True))
            click.echo(click.style("   已保存到 ~/.lingyi/presets.json", fg="dim"))
            click.echo(click.style("   用 lingyi pref set web_password 新密码 可修改\n", fg="dim"))
    _auth_enabled = bool(_web_pwd_hash)

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
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
        if path in public_paths or any(path.startswith(prefix) for prefix in public_prefixes):
            return await call_next(request)
        if not _auth_enabled:
            logger.warning(f"认证未启用，允许访问: {path}")
            return await call_next(request)
        token = request.cookies.get("lingyi_token", "")
        if not check_auth(token):
            return JSONResponse({"error": "未授权"}, status_code=401)
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8900", "http://127.0.0.1:8900"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )

    register_auth_routes(app, JSONResponse, Request, _TEMPLATE_DIR, _web_pwd_hash, _auth_enabled)

    _DB_PATH = _CHAT_DB_PATH
    _active_ws: set = set()
    _bridge_ws: list = []
    _cognitive_state: dict = {
        "last_push_date": None,
        "last_reminder_hour": None,
        "last_lingmsg_count": 0,
        "last_observation": "",
        "pending_alerts": [],
        "user_habits": {},
    }

    register_data_routes(app, JSONResponse, Request)
    register_messaging_routes(app, JSONResponse, Request, _DB_PATH, _active_ws, _bridge_ws, _cognitive_state)
    register_council_routes(app, JSONResponse, Request, _DB_PATH)
    ensure_chat_table()

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        raw_token = websocket.cookies.get("lingyi_token", "")
        if not raw_token:
            raw_token = websocket.query_params.get("token", "")
        if _auth_enabled and not check_auth(raw_token):
            await websocket.close(code=4001, reason="unauthorized")
            return
        await websocket.accept()
        initial_session_id = websocket.query_params.get("session_id", "") or str(uuid.uuid4())
        current_session_id = initial_session_id
        local_conv: list[dict] = load_recent_chat(current_session_id, 20)
        await websocket.send_json({"type": "session_joined", "session_id": current_session_id})
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
                    break
                msg = json.loads(raw)
                mtype = msg.get("type", "text")
                if mtype == "ping":
                    continue
                if mtype == "switch_session":
                    new_sid = msg.get("session_id", "")
                    if new_sid:
                        current_session_id = new_sid
                        local_conv = load_recent_chat(current_session_id, 20)
                        await websocket.send_json({"type": "session_switched", "session_id": current_session_id, "messages": local_conv[-20:]})
                    continue
                if mtype == "text":
                    user_text = msg.get("text", "").strip()
                    if not user_text:
                        continue
                    local_conv.append({"role": "user", "content": user_text})
                    save_chat_message(current_session_id, "user", user_text)
                    reply = await smart_reply(user_text, local_conv, glm_api_key=_GLM_API_KEY, glm_base_url=_GLM_BASE_URL, glm_model=_GLM_MODEL)
                    local_conv.append({"role": "assistant", "content": reply})
                    if len(local_conv) > MAX_CONVERSATION:
                        local_conv[:] = local_conv[-MAX_CONVERSATION:]
                    save_chat_message(current_session_id, "assistant", reply)
                    audio_b64 = None if msg.get("no_tts", False) else await do_tts(reply)
                    await websocket.send_json({"type": "reply", "text": reply, "audio": audio_b64})
                elif mtype == "audio":
                    audio_b64_data = msg.get("data", "")
                    if not audio_b64_data:
                        continue
                    try:
                        recognized = await asyncio.wait_for(do_stt(audio_b64_data), timeout=30)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"type": "reply", "text": "语音识别超时，请重试", "audio": None})
                        continue
                    if not recognized:
                        await websocket.send_json({"type": "reply", "text": "未识别到语音，请重试", "audio": None})
                        continue
                    await websocket.send_json({"type": "recognized", "text": recognized})
                    local_conv.append({"role": "user", "content": recognized})
                    save_chat_message(current_session_id, "user", recognized)
                    reply = await smart_reply(recognized, local_conv, glm_api_key=_GLM_API_KEY, glm_base_url=_GLM_BASE_URL, glm_model=_GLM_MODEL)
                    local_conv.append({"role": "assistant", "content": reply})
                    if len(local_conv) > MAX_CONVERSATION:
                        local_conv[:] = local_conv[-MAX_CONVERSATION:]
                    save_chat_message(current_session_id, "assistant", reply)
                    audio_b64 = None if msg.get("no_tts", False) else await do_tts(reply)
                    await websocket.send_json({"type": "reply", "text": reply, "audio": audio_b64})
        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected")
        except Exception as exc:
            logger.error(f"WebSocket error: {exc}")
        finally:
            ka_task.cancel()
            _active_ws.discard(websocket)

    _bridge_conv: list[dict] = load_recent_chat("default", 20)

    async def _bridge_on_chat(text: str, request_id: str, from_client: str, audio: str | None) -> tuple[str, str | None]:
        loop = asyncio.get_event_loop()
        _bridge_conv.append({"role": "user", "content": text})
        save_chat_message("default", "user", text)
        reply = await loop.run_in_executor(
            None, lambda t: chat_llm_with_context(t, _bridge_conv, _GLM_API_KEY, _GLM_BASE_URL, _GLM_MODEL), text
        )
        _bridge_conv.append({"role": "assistant", "content": reply})
        if len(_bridge_conv) > MAX_CONVERSATION:
            _bridge_conv[:] = _bridge_conv[-MAX_CONVERSATION:]
        save_chat_message("default", "assistant", reply)
        return reply, await do_tts(reply)

    async def _push_to_all(category: str, text: str):
        for ws in list(_active_ws):
            try:
                await ws.send_json({"type": "push", "category": category, "text": text})
            except Exception:
                _active_ws.discard(ws)
        if _bridge_ws:
            from .bridge_client import bridge_push
            await bridge_push(_bridge_ws[0], text, category)

    @app.on_event("startup")
    async def _start_push_task():
        asyncio.create_task(auto_push_loop(_active_ws, _bridge_ws, _cognitive_state, _push_to_all, do_tts))
        asyncio.create_task(run_bridge_connector(_bridge_on_chat, lambda ws: (_bridge_ws.clear(), _bridge_ws.append(ws))))
        asyncio.create_task(auto_health_check_loop())

    return app


def run_server(host: str = "0.0.0.0", port: int = 8900, ssl: bool = True, password: str | None = None):
    import uvicorn
    app = create_app(password=password)
    ssl_kwargs = {}
    if ssl:
        cert_dir = Path.home() / ".lingyi"
        cert_pem, cert_key = cert_dir / "cert.pem", cert_dir / "cert.key"
        if cert_pem.exists() and cert_key.exists():
            ssl_kwargs["ssl_keyfile"] = str(cert_key)
            ssl_kwargs["ssl_certfile"] = str(cert_pem)
    proto = "https" if ssl_kwargs else "http"
    import click
    click.echo(f"灵依 Web UI 启动: {proto}://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning", timeout_keep_alive=120, ws_ping_interval=30, ws_ping_timeout=90, **ssl_kwargs)
