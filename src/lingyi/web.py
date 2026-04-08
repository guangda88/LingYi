"""灵依 Web UI - 浏览器语音聊天界面。"""

import asyncio
import json
import logging
from pathlib import Path

from ._web_audio import _do_tts, _do_stt  # noqa: F401

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_MAX_HISTORY = 40


def _load_session(session_key: str) -> list[dict]:
    """从 SQLite 加载会话历史。"""
    from .db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT messages FROM web_sessions WHERE session_key = ?", (session_key,)
    ).fetchone()
    conn.close()
    if row:
        try:
            msgs = json.loads(row["messages"])
            return msgs[-_MAX_HISTORY:]
        except Exception:
            pass
    return []


def _save_session(session_key: str, messages: list[dict]) -> None:
    """保存会话历史到 SQLite。"""
    from .db import get_db
    conn = get_db()
    trimmed = messages[-_MAX_HISTORY:]
    row = conn.execute(
        "SELECT id FROM web_sessions WHERE session_key = ?", (session_key,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE web_sessions SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE session_key = ?",
            (json.dumps(trimmed, ensure_ascii=False), session_key),
        )
    else:
        conn.execute(
            "INSERT INTO web_sessions (session_key, messages) VALUES (?, ?)",
            (session_key, json.dumps(trimmed, ensure_ascii=False)),
        )
    conn.commit()
    conn.close()


def create_app():
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="灵依 Web UI")

    @app.get("/")
    async def index():
        return HTMLResponse((_TEMPLATE_DIR / "chat.html").read_text("utf-8"))

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        await websocket.accept()
        from .voicecall import _generate_reply
        session_key = websocket.client.host if websocket.client else "default"
        conversation = _load_session(session_key)

        async def _keepalive():
            try:
                while True:
                    await asyncio.sleep(20)
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break
            except asyncio.CancelledError:
                pass

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
                    conversation.append({"role": "user", "content": user_text})
                    reply = _generate_reply(user_text, conversation)
                    conversation.append({"role": "assistant", "content": reply})
                    _save_session(session_key, conversation)
                    audio_b64 = await _do_tts(reply)
                    await websocket.send_json({
                        "type": "reply",
                        "text": reply,
                        "audio": audio_b64,
                    })

                elif mtype == "audio":
                    audio_b64_data = msg.get("data", "")
                    if not audio_b64_data:
                        continue
                    logger.info(f"[STT] 收到音频, base64长度={len(audio_b64_data)}")
                    try:
                        recognized = await asyncio.wait_for(_do_stt(audio_b64_data), timeout=30)
                    except asyncio.TimeoutError:
                        logger.error("[STT] 超时30秒")
                        await websocket.send_json({
                            "type": "reply",
                            "text": "⚠ 语音识别超时，请重试",
                            "audio": None,
                        })
                        continue
                    if not recognized:
                        logger.warning("[STT] 识别结果为空")
                        await websocket.send_json({
                            "type": "reply",
                            "text": "⚠ 未识别到语音，请重试",
                            "audio": None,
                        })
                        continue
                    logger.info(f"[STT] 识别结果: {recognized}")
                    await websocket.send_json({
                        "type": "recognized",
                        "text": recognized,
                    })
                    conversation.append({"role": "user", "content": recognized})
                    reply = _generate_reply(recognized, conversation)
                    conversation.append({"role": "assistant", "content": reply})
                    _save_session(session_key, conversation)
                    logger.info(f"[REPLY] 回复: {reply[:50]}")
                    audio_b64 = await _do_tts(reply)
                    await websocket.send_json({
                        "type": "reply",
                        "text": reply,
                        "audio": audio_b64,
                    })

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected")
        except Exception as exc:
            logger.error(f"WebSocket error: {exc}")
        finally:
            ka_task.cancel()

    return app


def run_server(host: str = "0.0.0.0", port: int = 8900, ssl: bool = True):
    import uvicorn
    app = create_app()

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
    click.echo(f"🌐 灵依 Web UI 启动: {proto}://{host}:{port}")
    click.echo("  按 Ctrl+C 退出")

    uvicorn.run(
        app, host=host, port=port, log_level="info",
        timeout_keep_alive=120, ws_ping_interval=30, ws_ping_timeout=60,
        **ssl_kwargs,
    )
