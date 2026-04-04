"""灵依 → 智桥 后端连接器。

灵依通过 WebSocket 客户端连接到智桥(:8765)，注册为 AI 后端，
接收用户消息，处理后回复。认知循环的推送也通过智桥中继。
"""

import asyncio
import json
import logging
import ssl
from pathlib import Path

logger = logging.getLogger(__name__)

_BRIDGE_HOST = "0.0.0.0"
_BRIDGE_PORT = 8765
_BACKEND_ID = "lingyi"
_BACKEND_NAME = "灵依"
_BACKEND_DESC = "私人助理 — 29工具 + 认知循环"

_reconnect_delay = 2


async def connect_to_bridge(on_chat, on_registered=None):
    """连接智桥，注册为 AI 后端，持续监听并路由消息。

    Args:
        on_chat: async callable(text, request_id, from_client, audio) -> (reply_text, reply_audio_b64)
        on_registered: optional async callable() — 注册成功后回调
    """
    global _reconnect_delay

    cert_dir = Path.home() / ".lingyi"
    cert_pem = cert_dir / "cert.pem"
    cert_key = cert_dir / "cert.key"

    import websockets

    while True:
        try:
            ssl_ctx = None
            if cert_pem.exists() and cert_key.exists():
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_ctx.load_verify_locations(str(cert_pem))
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            proto = "wss" if ssl_ctx else "ws"

            uri = f"{proto}://localhost:{_BRIDGE_PORT}"
            logger.info(f"[智桥] 正在连接 {uri} ...")

            async with websockets.connect(
                uri,
                ssl=ssl_ctx,
                ping_interval=25,
                ping_timeout=60,
                close_timeout=5,
            ) as ws:
                # 注册
                await ws.send(json.dumps({
                    "type": "register_backend",
                    "backend_id": _BACKEND_ID,
                    "name": _BACKEND_NAME,
                    "description": _BACKEND_DESC,
                    "capabilities": ["chat", "tools", "tts", "stt", "push"],
                }))
                logger.info(f"[智桥] 已注册为 {_BACKEND_ID}")

                _reconnect_delay = 2

                if on_registered:
                    await on_registered(ws)

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    mtype = msg.get("type", "")

                    if mtype == "backend_registered":
                        logger.info(f"[智桥] 注册确认: {msg.get('message', '')}")

                    elif mtype == "chat":
                        request_id = msg.get("request_id", "")
                        text = msg.get("text", "")
                        from_client = msg.get("from", "")
                        audio = msg.get("audio")
                        if not text:
                            continue
                        logger.info(f"[智桥] 收到用户消息: {text[:60]}")
                        try:
                            reply_text, reply_audio = await on_chat(text, request_id, from_client, audio)
                        except Exception as exc:
                            logger.error(f"[智桥] 处理消息失败: {exc}")
                            reply_text = f"抱歉，处理出了问题: {exc}"
                            reply_audio = None
                        await ws.send(json.dumps({
                            "type": "reply",
                            "request_id": request_id,
                            "text": reply_text,
                            "audio": reply_audio,
                            "backend": _BACKEND_ID,
                        }))
                        logger.info(f"[智桥] 已回复 {request_id[:8]}")

                    elif mtype == "pong":
                        pass

                    elif mtype == "error":
                        logger.warning(f"[智桥] 服务端错误: {msg.get('message', '')}")

        except (
            ConnectionRefusedError,
            OSError,
            websockets.exceptions.ConnectionClosed,
        ) as exc:
            logger.warning(f"[智桥] 连接断开 ({exc})，{_reconnect_delay}s 后重连...")
            await asyncio.sleep(_reconnect_delay)
            _reconnect_delay = min(_reconnect_delay * 1.5, 30)
        except Exception as exc:
            logger.error(f"[智桥] 异常: {exc}")
            await asyncio.sleep(_reconnect_delay)


async def bridge_push(ws, text: str, category: str = "info"):
    """通过智桥向用户推送通知。"""
    if ws is None:
        return
    try:
        await ws.send(json.dumps({
            "type": "push",
            "backend": _BACKEND_ID,
            "category": category,
            "text": text,
        }))
    except Exception as exc:
        logger.error(f"[智桥] 推送失败: {exc}")
