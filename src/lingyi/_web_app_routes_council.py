"""Web 议事厅/验证/讨论路由。"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def register_council_routes(app, JSONResponse, Request, db_path):
    _DB = db_path

    @app.get("/api/council/status")
    async def api_council_status():
        from ..council import council_status
        import asyncio
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, council_status)
        return JSONResponse(info)

    @app.post("/api/council/scan")
    async def api_council_scan():
        import asyncio
        from .._web_app_cognitive import council_scan_sync
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, council_scan_sync)
        return JSONResponse(result)

    @app.post("/api/council/wake")
    async def api_council_wake(request: Request):
        from ..council import wake_member
        from ..lingmessage import send_message, _load_discussion, _get_store
        body = await request.json()
        member_id = body.get("member_id", "")
        disc_id = body.get("disc_id", "")
        if not member_id or not disc_id:
            return JSONResponse({"error": "需要 member_id 和 disc_id"}, status_code=400)
        import asyncio
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, lambda: wake_member(member_id, disc_id))
        if reply:
            disc_data = await loop.run_in_executor(None, lambda: _load_discussion(_get_store(), disc_id))
            if disc_data:
                await loop.run_in_executor(
                    None,
                    lambda: send_message(from_id=member_id, topic=disc_data["topic"], content=reply),
                )
            return JSONResponse({"replied": True, "content": reply[:200]})
        return JSONResponse({"replied": False, "reason": "已发言/已关闭/API不可用"})

    @app.post("/api/verification/check")
    async def api_verification_check(request: dict):
        from ..constraint_layer import Assertion, ConstraintLayer
        member_id = request.get("member_id", "")
        assertion_type = request.get("assertion_type", "")
        content = request.get("content", "")
        tool_call = request.get("tool_call")
        if not member_id or not assertion_type or not content:
            return JSONResponse({"error": "member_id, assertion_type, and content are required"}, status_code=400)
        constraint = ConstraintLayer()
        assertion = Assertion(member_id=member_id, assertion_type=assertion_type, content=content, tool_call=tool_call)
        result = constraint.verify_assertion(assertion)
        return JSONResponse({
            "passed": result.passed, "reason": result.reason, "checks": result.checks,
            "recommendation": result.recommendation, "requires_fallback": result.requires_fallback,
        })

    @app.get("/api/verification/stats")
    async def api_verification_stats(days: int = 7):
        from ..constraint_layer import ConstraintLayer
        constraint = ConstraintLayer()
        stats = constraint.get_verification_stats(days)
        return JSONResponse(stats)

    @app.get("/api/verification/log")
    async def api_verification_log(days: int = 7, member_id: str | None = None):
        from ..constraint_layer import VerificationMonitor
        monitor = VerificationMonitor()
        logs = monitor._load_logs()
        cutoff = datetime.now().timestamp() - days * 86400
        recent_logs = [
            log for log in logs
            if datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff
        ]
        if member_id:
            recent_logs = [log for log in recent_logs if log["member_id"] == member_id]
        return JSONResponse(recent_logs)

    @app.post("/api/discuss")
    async def api_discuss(request: Request):
        from .._web_app_chat_llm import yi_discuss_sync
        from ..web_app import _GLM_API_KEY, _GLM_BASE_URL
        body = await request.json()
        topic = body.get("topic", "").strip()
        if not topic:
            return JSONResponse({"error": "topic必填"}, status_code=400)
        context = body.get("context", "")
        question = body.get("question", "")
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: yi_discuss_sync(topic, context, question, _GLM_API_KEY, _GLM_BASE_URL)
        )
        return JSONResponse({
            "agent_id": "lingyi", "agent_name": "灵依", "topic": topic,
            "content": result["content"], "source_type": result["source_type"],
            "model_used": result["model_used"], "tokens_used": len(result["content"]) // 2,
        })
