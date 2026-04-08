"""先检验再断言约束层 - Verify Before Assertion.

在AI成员进行断言之前强制进行验证，确保：
- 不做没有依据的断言
- 不编造通信、讨论或决议
- 不越界操作
- 推演必须标注

约束层架构：
1. 前置检查 (Pre-Check)
2. 工具验证 (Tool Validation)
3. 边界检查 (Boundary Check)
4. 事实验证 (Fact Verification)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ._constraint_models import Assertion, VerificationResult, VerificationLog  # noqa: F401
from ._constraint_validators_base import BaseValidator, LingZhiValidator
from ._constraint_validators_ext import LingFlowValidator, LingYanValidator

logger = logging.getLogger(__name__)

_VERIFICATION_LOG_PATH = Path.home() / ".lingyi" / "verification_log.json"

__all__ = ["Assertion", "ConstraintLayer"]


class VerificationMonitor:
    """验证监控"""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path or _VERIFICATION_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_verification(
        self,
        assertion: Assertion,
        result: VerificationResult,
        action: str
    ) -> None:
        """记录验证"""
        log = VerificationLog(
            timestamp=datetime.now().isoformat(),
            member_id=assertion.member_id,
            assertion_type=assertion.assertion_type,
            assertion_content=assertion.content[:200],
            verification_result=asdict(result),
            action_taken=action
        )

        self._append_to_file(log)

    def get_stats(self, days: int = 7) -> dict:
        """获取统计"""
        if not self.log_path.exists():
            return {}

        logs = self._load_logs()
        cutoff = datetime.now().timestamp() - days * 86400

        recent_logs = [
            log for log in logs
            if datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff
        ]

        total = len(recent_logs)
        approved = sum(1 for log in recent_logs if log["action_taken"] == "approved")
        rejected = sum(1 for log in recent_logs if log["action_taken"] == "rejected")
        fallback = sum(1 for log in recent_logs if log["action_taken"] == "fallback")

        by_member: dict[str, dict] = {}
        for log in recent_logs:
            member_id = log["member_id"]
            if member_id not in by_member:
                by_member[member_id] = {"total": 0, "approved": 0, "rejected": 0}
            by_member[member_id]["total"] += 1
            if log["action_taken"] == "approved":
                by_member[member_id]["approved"] += 1
            elif log["action_taken"] == "rejected":
                by_member[member_id]["rejected"] += 1

        return {
            "period_days": days,
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "fallback": fallback,
            "approval_rate": round(approved / total * 100, 1) if total > 0 else 0,
            "by_member": by_member,
        }

    def _load_logs(self) -> list[dict]:
        """加载日志"""
        if not self.log_path.exists():
            return []

        try:
            data = self.log_path.read_text(encoding="utf-8")
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to load verification log: {e}")
            return []

    def _append_to_file(self, log: VerificationLog) -> None:
        """追加到日志文件"""
        try:
            logs = self._load_logs()
            logs.append(asdict(log))

            self.log_path.write_text(
                json.dumps(logs, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to write verification log: {e}")


class ConstraintLayer:
    """约束层 - 先检验再断言"""

    def __init__(self):
        self.validators = {
            "lingzhi": LingZhiValidator(),
            "lingflow": LingFlowValidator(),
            "lingresearch": LingYanValidator(),
        }
        self.monitor = VerificationMonitor()

    def verify_assertion(self, assertion: Assertion) -> VerificationResult:
        """验证断言"""
        member_id = assertion.member_id
        validator = self.validators.get(member_id, BaseValidator())

        checks: list[dict] = []
        all_passed = True

        # 1. 前置检查
        pre_check = validator.pre_check(assertion)
        checks.append(pre_check)
        if not pre_check["passed"]:
            all_passed = False

        # 2. 工具验证
        if assertion.tool_call:
            tool_check = validator.validate_tool_call(assertion.tool_call)
            checks.append(tool_check)
            if not tool_check["passed"]:
                all_passed = False

        # 3. 边界检查
        boundary_check = validator.check_boundary(assertion)
        checks.append(boundary_check)
        if not boundary_check["passed"]:
            all_passed = False

        # 4. 事实验证
        fact_check = validator.verify_fact(assertion)
        checks.append(fact_check)
        if not fact_check["passed"]:
            all_passed = False

        if all_passed:
            result = VerificationResult(
                passed=True,
                reason="All checks passed",
                checks=checks,
                recommendation=None
            )
            self.monitor.log_verification(assertion, result, "approved")
        else:
            result = VerificationResult(
                passed=False,
                reason=self._summarize_checks(checks),
                checks=checks,
                recommendation=self._generate_recommendation(checks),
                requires_fallback=self._should_fallback(checks)
            )
            action = "fallback" if result.requires_fallback else "rejected"
            self.monitor.log_verification(assertion, result, action)

        return result

    def get_verification_stats(self, days: int = 7) -> dict:
        """获取验证统计"""
        return self.monitor.get_stats(days)

    def _summarize_checks(self, checks: list[dict]) -> str:
        """总结检查结果"""
        failed = [c for c in checks if not c["passed"]]
        return ", ".join([f["reason"] for f in failed])

    def _generate_recommendation(self, checks: list[dict]) -> str | None:
        """生成改进建议"""
        failed = [c for c in checks if not c["passed"]]

        for check in failed:
            name = check["name"]
            if name == "fact_verification":
                return "请先进行事实验证，调用相应工具查询或检查"
            elif name == "boundary_check":
                return "请检查是否违反了安全边界，确认操作在允许范围内"
            elif name == "tool_validation":
                detail = check.get("detail", "")
                return f"工具调用验证失败: {detail}"
            elif name == "pre_check":
                return "前置检查未通过，请检查断言内容是否合规"

        return None

    def _should_fallback(self, checks: list[dict]) -> bool:
        """判断是否需要降级处理"""
        failed = [c for c in checks if not c["passed"]]

        for check in failed:
            if check["name"] == "fact_verification":
                return False

        return len(failed) == 1
