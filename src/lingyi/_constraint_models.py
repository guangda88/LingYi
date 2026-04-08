"""约束层数据模型 — Assertion, VerificationResult, VerificationLog。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Assertion:
    """断言请求"""
    member_id: str
    assertion_type: str  # "fact" | "action" | "communication"
    content: str
    tool_call: dict | None = None
    context: dict | None = None


@dataclass
class VerificationResult:
    """验证结果"""
    passed: bool
    reason: str
    checks: list[dict]
    recommendation: str | None = None
    requires_fallback: bool = False


@dataclass
class VerificationLog:
    """验证日志"""
    timestamp: str
    member_id: str
    assertion_type: str
    assertion_content: str
    verification_result: dict
    action_taken: str  # "approved" | "rejected" | "fallback"
