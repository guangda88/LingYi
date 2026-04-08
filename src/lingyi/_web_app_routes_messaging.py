"""Web 消息路由：会话管理、灵信、统一通信、健康。"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def register_messaging_routes(app, JSONResponse, Request, db_path: Path, active_ws: set, bridge_ws: list, cognitive_state: dict):
    _DB = db_path
    @app.get("/api/sessions")
    async def api_list_sessions():
        try:
            conn = sqlite3.connect(str(_DB))
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
        title = request.get("title", "新对话").strip() or "新对话"
        session_id = str(uuid.uuid4())
        try:
            conn = sqlite3.connect(str(_DB))
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
        if session_id == "default":
            return JSONResponse({"error": "默认会话不能删除"}, status_code=403)
        try:
            conn = sqlite3.connect(str(_DB))
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
            return JSONResponse({"ok": True})
        except Exception as exc:
            logger.error(f"Failed to delete session: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)
    @app.put("/api/sessions/{session_id}/title")
    async def api_update_session_title(session_id: str, request: dict):
        title = request.get("title", "").strip()
        if not title:
            return JSONResponse({"error": "标题不能为空"}, status_code=400)
        try:
            conn = sqlite3.connect(str(_DB))
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
        try:
            conn = sqlite3.connect(str(_DB))
            row = conn.execute(
                "SELECT session_id FROM chat_messages WHERE id = ?",
                (message_id,)
            ).fetchone()
            if not row:
                conn.close()
                return JSONResponse({"error": "消息不存在"}, status_code=404)

            session_id = row[0]
            conn.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))
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

    @app.get("/api/briefing")
    async def api_briefing():
        from ..briefing import collect_all, format_briefing
        data = collect_all()
        return JSONResponse({"raw": data, "formatted": format_briefing(data)})
    @app.get("/api/status")
    async def api_status():
        from ..llm_utils import get_model_status
        return JSONResponse({
            "service": "灵依",
            "uptime_port": 8900,
            "bridge_connected": bool(bridge_ws),
            "direct_ws_clients": len(active_ws),
            "tools_count": 29,
            "cognitive_state": {
                "last_push_date": cognitive_state.get("last_push_date"),
                "last_reminder_hour": cognitive_state.get("last_reminder_hour"),
                "last_lingmsg_count": cognitive_state.get("last_lingmsg_count", 0),
            },
            "models": get_model_status(),
            "timestamp": datetime.now().isoformat(),
        })
    @app.get("/api/models")
    async def api_models():
        from ..llm_utils import get_model_status
        return JSONResponse(get_model_status())
    @app.get("/api/usage")
    async def api_usage():
        from ..llm_utils import get_usage_stats
        return JSONResponse(get_usage_stats())
    @app.post("/api/models")
    async def api_models_probe(request: Request):
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        action = body.get("action", "") or request.query_params.get("action", "")
        if action == "probe":
            from ..llm_utils import probe_premium_models, get_model_status
            probe = probe_premium_models()
            results = []
            for model, st in probe.items():
                results.append({"model": model, "available": st == "available", "reason": "" if st == "available" else st})
            return JSONResponse({"results": results, "status": get_model_status()})
        return JSONResponse({"error": "unknown action"}, status_code=400)

    @app.get("/api/lingmessage")
    async def api_lingmessage(status: str | None = "open"):
        from ..lingmessage import list_discussions
        return JSONResponse(list_discussions(status=status))

    @app.get("/api/lingmessage/{disc_id}")
    async def api_lingmessage_detail(disc_id: str):
        from ..lingmessage import _load_discussion, _get_store
        disc = _load_discussion(_get_store(), disc_id)
        if not disc:
            return JSONResponse({"error": "讨论不存在"}, status_code=404)
        return JSONResponse(disc)

    @app.post("/api/lingmessage/send")
    async def api_lingmessage_send(request: dict):
        from ..lingmessage import send_message
        topic = request.get("topic", "").strip()
        content = request.get("content", "").strip()
        from_id = request.get("from_id", "guangda").strip() or "guangda"
        if not topic or not content:
            return JSONResponse({"error": "topic和content必填"}, status_code=400)
        msg = send_message(from_id, topic, content)
        return JSONResponse(asdict(msg) if hasattr(msg, '__dataclass_fields__') else msg)

    @app.post("/api/lingmessage/notify")
    async def api_lingmessage_notify(request: Request):
        client_host = request.client.host if request.client else ""
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        body = await request.json()
        from_id = body.get("from", "?")
        topic = body.get("topic", "?")
        logger.info(f"灵信通知: {from_id} 在 [{topic}] 发了新消息")
        return JSONResponse({"received": True})

    @app.get("/api/lingmessage/inbox/{member_id}")
    async def api_inbox_get(member_id: str):
        from ..lingmessage import get_inbox
        messages = get_inbox(member_id)
        return JSONResponse({"member_id": member_id, "unread_count": len(messages), "messages": messages})

    @app.post("/api/lingmessage/inbox/{member_id}/read")
    async def api_inbox_mark_read(member_id: str, request: dict):
        body = await request.json()
        message_id = body.get("message_id", "")
        if not message_id:
            return JSONResponse({"error": "message_id必填"}, status_code=400)
        from ..lingmessage import mark_inbox_read
        success = mark_inbox_read(member_id, message_id)
        return JSONResponse({"success": success})

    @app.post("/api/lingmessage/inbox/{member_id}/clean")
    async def api_inbox_clean(member_id: str, request: dict):
        body = await request.json()
        days = body.get("days", 7)
        from ..lingmessage import clean_read_inbox
        deleted = clean_read_inbox(member_id, days)
        return JSONResponse({"deleted": deleted})

    @app.get("/api/lingmessage/delivery/{message_id}")
    async def api_delivery_status(message_id: str):
        from ..lingmessage import get_delivery_status
        status = get_delivery_status(message_id)
        return JSONResponse(status)

    @app.get("/api/health/endpoints")
    async def api_health_endpoints():
        from ..endpoint_monitor import get_health_summary
        return JSONResponse(get_health_summary())

    @app.post("/api/health/check")
    async def api_health_check():
        from ..endpoint_monitor import check_all_endpoints, get_health_summary
        check_all_endpoints()
        return JSONResponse(get_health_summary())

    @app.get("/api/health/summary")
    async def api_health_summary():
        from ..endpoint_monitor import get_health_summary, format_health_summary
        summary = get_health_summary()
        text = format_health_summary(summary)
        return JSONResponse({"summary": text, "data": summary})

    @app.get("/api/unified/online")
    async def api_unified_online():
        from ..unified_comm import UnifiedOnlineDetector, UNIFIED_MEMBERS
        detector = UnifiedOnlineDetector()
        online_status = detector.check_all_online()
        result = {}
        for member_id, online in online_status.items():
            member = UNIFIED_MEMBERS.get(member_id)
            if member:
                result[member_id] = {"name": member.name, "online": online}
        return JSONResponse(result)

    @app.post("/api/unified/send")
    async def api_unified_send(request: Request):
        body = await request.json()
        sender_id = body.get("sender_id", "lingyi")
        recipient_id = body.get("recipient_id")
        topic = body.get("topic")
        content = body.get("content")
        message_type = body.get("message_type", "discussion")
        if not recipient_id or not topic or not content:
            return JSONResponse({"error": "recipient_id, topic, and content are required"}, status_code=400)
        from ..unified_comm import UnifiedOnlineDetector, UnifiedMessageRouter, UNIFIED_MEMBERS
        if sender_id not in UNIFIED_MEMBERS:
            return JSONResponse({"error": f"Unknown sender: {sender_id}"}, status_code=400)
        if recipient_id not in UNIFIED_MEMBERS:
            return JSONResponse({"error": f"Unknown recipient: {recipient_id}"}, status_code=400)
        detector = UnifiedOnlineDetector()
        router = UnifiedMessageRouter(detector)
        result = router.send_message(sender_id, recipient_id, topic, content, message_type)
        return JSONResponse({
            "success": result.success, "message_id": result.message_id,
            "channel": result.channel, "error": result.error,
            "response_time_ms": result.response_time_ms,
        })

    @app.get("/api/unified/queue/{recipient_id}")
    async def api_unified_queue(recipient_id: str):
        from ..unified_comm import OfflineMessageQueue, UNIFIED_MEMBERS
        if recipient_id not in UNIFIED_MEMBERS:
            return JSONResponse({"error": f"Unknown recipient: {recipient_id}"}, status_code=400)
        queue = OfflineMessageQueue()
        messages = queue.dequeue(recipient_id)
        return JSONResponse({
            "recipient_id": recipient_id, "queued_count": len(messages),
            "messages": [asdict(msg) for msg in messages],
        })

    @app.get("/api/unified/queue-stats")
    async def api_unified_queue_stats():
        from ..unified_comm import OfflineMessageQueue
        queue = OfflineMessageQueue()
        stats = queue.get_queue_stats()
        return JSONResponse({"total_queued": sum(stats.values()), "by_recipient": stats})

    @app.post("/api/unified/retry")
    async def api_unified_retry():
        from ..unified_comm import OfflineMessageQueue, UnifiedOnlineDetector, UnifiedMessageRouter
        queue = OfflineMessageQueue()
        detector = UnifiedOnlineDetector()
        router = UnifiedMessageRouter(detector)
        stats = queue.retry_send(router, detector)
        return JSONResponse({"success": True, "stats": stats})
