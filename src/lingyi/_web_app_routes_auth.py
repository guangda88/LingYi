"""Web 认证路由：登录、登出、会话验证。"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from ._web_app_auth import (
    check_auth, check_login_rate, record_login_attempt,
    add_persistent_token, remove_persistent_token,
    cleanup_sessions, check_password,
    SESSIONS as _SESSIONS,
)

logger = logging.getLogger(__name__)


def register_auth_routes(app, JSONResponse, Request, _TEMPLATE_DIR, web_pwd_hash, auth_enabled):
    @app.get("/login")
    async def login_page():
        from fastapi.responses import HTMLResponse
        if not auth_enabled:
            return HTMLResponse('<script>location.href="/"</script>')
        return HTMLResponse((_TEMPLATE_DIR / "login.html").read_text("utf-8"))

    @app.post("/api/login")
    async def api_login(request: Request):
        from fastapi.responses import HTMLResponse  # noqa: F401
        ip = request.client.host if request.client else "unknown"
        if not check_login_rate(ip):
            return JSONResponse({"error": "登录尝试过多，请5分钟后重试"}, status_code=429)
        body = await request.json()
        pwd = body.get("password", "")
        remember = body.get("remember", False)
        if check_password(pwd, web_pwd_hash):
            token = secrets.token_hex(32)
            cleanup_sessions()
            if remember:
                expires = datetime.now() + timedelta(days=30)
                _SESSIONS[token] = expires
                add_persistent_token(token, expires)
                resp = JSONResponse({"ok": True})
                resp.set_cookie("lingyi_token", token, max_age=2592000, samesite="lax")
            else:
                _SESSIONS[token] = datetime.now() + timedelta(hours=24)
                resp = JSONResponse({"ok": True})
                resp.set_cookie("lingyi_token", token, max_age=86400, samesite="lax")
            return resp
        record_login_attempt(ip)
        return JSONResponse({"error": "密码错误"}, status_code=403)

    @app.post("/api/logout")
    async def api_logout(request: Request):
        token = request.cookies.get("lingyi_token", "")
        if token:
            _SESSIONS.pop(token, None)
            remove_persistent_token(token)
        resp = JSONResponse({"ok": True})
        resp.set_cookie("lingyi_token", "", max_age=0)
        return resp

    @app.get("/")
    async def index(request: Request):
        from fastapi.responses import HTMLResponse
        if auth_enabled:
            token = request.cookies.get("lingyi_token", "")
            if not check_auth(token):
                return HTMLResponse('<script>location.href="/login"</script>')
        return HTMLResponse((_TEMPLATE_DIR / "index.html").read_text("utf-8"))
