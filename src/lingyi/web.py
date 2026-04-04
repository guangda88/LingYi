"""灵依 Web UI - 浏览器语音聊天界面。"""

import asyncio
import base64
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY", "sk-87b60796471c4596bcd7278d4ac12dfe"
)

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
        import tempfile
        import os
        import edge_tts
        fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
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
    logger.warning("Whisper STT failed, falling back to DashScope")
    return await _stt_dashscope(audio_b64)


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
                logger.error(f"Recognition error: {result}")
                done_event.set()

            def on_event(self, result):
                try:
                    d = json.loads(str(result))
                    t = d.get("output", {}).get("sentence", {}).get("text", "")
                    if t:
                        texts.append(t)
                except Exception:
                    pass

        recognition = Recognition(
            model="paraformer-realtime-v2",
            format="wav",
            sample_rate=16000,
            callback=CB(),
        )

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
        result = await loop.run_in_executor(
            None, lambda: model.transcribe(tmp.name, language="zh")
        )
        Path(tmp.name).unlink(missing_ok=True)
        return result.get("text", "").strip() or None
    except Exception as exc:
        logger.error(f"Whisper STT failed: {exc}")
        return None


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
