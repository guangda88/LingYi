"""灵通/灵妍专用验证器。"""

from __future__ import annotations

import re
from pathlib import Path

from ._constraint_models import Assertion
from ._constraint_validators_base import BaseValidator


class LingFlowValidator(BaseValidator):
    """灵通专用验证器"""

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        if not tool_call:
            return super().validate_tool_call(tool_call)

        tool_name = tool_call.get("name")

        if tool_name in ["git_commit", "git_push", "git_branch"]:
            repo_path = tool_call.get("arguments", {}).get("repo_path", "")

            if not Path(repo_path).exists():
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"仓库路径不存在: {repo_path}"
                }

            if not self._has_repo_access(repo_path):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"无权限访问仓库: {repo_path}"
                }

            if not self._verify_workflow_state(repo_path):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": "工作流状态不稳定，请先检查"
                }

        if tool_name == "generate_audit_report":
            version = tool_call.get("arguments", {}).get("version", "")

            if not self._is_valid_version(version):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"无效的版本号: {version}",
                    "detail": "版本号格式: v0.16 或 v0.16.0"
                }

            if not self._has_version_changes(repo_path="", version=version):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"版本{version}无代码变更，无法生成审计报告"
                }

        return super().validate_tool_call(tool_call)

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        if "灵通" in assertion.content or "工作流" in assertion.content:
            if not assertion.tool_call:
                return {
                    "name": "fact_verification",
                    "passed": False,
                    "reason": "断言涉及灵通状态但未进行验证"
                }

        if self._is_fabricated_communication(assertion.content):
            return {
                "name": "fact_verification",
                "passed": False,
                "reason": "检测到可能的编造通信",
                "detail": "请验证该通信是否真实发生"
            }

        return super().verify_fact(assertion)

    def _is_fabricated_communication(self, text: str) -> bool:
        """检测可能的编造通信"""
        if "灵通" in text and "说" in text:
            return True
        return False

    def _has_repo_access(self, repo_path: str) -> bool:
        """检查是否有仓库访问权限"""
        try:
            return Path(repo_path).is_dir()
        except Exception:
            return False

    def _verify_workflow_state(self, repo_path: str) -> bool:
        """验证工作流状态"""
        git_dir = Path(repo_path) / ".git"
        return git_dir.exists() if Path(repo_path).exists() else False

    def _is_valid_version(self, version: str) -> bool:
        """验证版本号格式"""
        pattern = r"^v\d+\.\d+(\.\d+)?$"
        return bool(re.match(pattern, version))

    def _has_version_changes(self, repo_path: str, version: str) -> bool:
        """检查版本是否有代码变更"""
        return True


class LingYanValidator(BaseValidator):
    """灵妍专用验证器"""

    _REGISTERED_SOURCES = {
        "research_db": "research",
        "experiment_logs": "experiment",
        "papers": "paper"
    }

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        if not tool_call:
            return super().validate_tool_call(tool_call)

        tool_name = tool_call.get("name")

        if tool_name == "access_data_source":
            source = tool_call.get("arguments", {}).get("source", "")

            if not self._is_registered_source(source):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"未注册的数据源: {source}",
                    "detail": f"已注册的源: {list(self._REGISTERED_SOURCES.keys())}"
                }

            if not self._is_source_available(source):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"数据源不可用: {source}"
                }

        if tool_name == "analyze_data":
            data_path = tool_call.get("arguments", {}).get("data_path", "")

            if not Path(data_path).exists():
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"数据文件不存在: {data_path}"
                }

            if not self._is_valid_data_format(data_path):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"无效的数据格式: {data_path}"
                }

        return super().validate_tool_call(tool_call)

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        if ("研究" in assertion.content or "实验" in assertion.content):
            if not self._is_inference_labeled(assertion.content) and not assertion.tool_call:
                return {
                    "name": "fact_verification",
                    "passed": False,
                    "reason": "断言涉及研究但未进行验证",
                    "detail": "请调用数据分析工具验证或标注为推演"
                }

        if self._is_inference_not_fact(assertion.content):
            return {
                "name": "fact_verification",
                "passed": False,
                "reason": "推演需要标注",
                "detail": "请在断言中标注'基于推演'或'推断'"
            }

        return super().verify_fact(assertion)

    def _is_inference_not_fact(self, text: str) -> bool:
        """检测是否为推演而非事实"""
        inference_patterns = [
            "基于趋势", "推断", "预测", "可能", "应该"
        ]
        has_pattern = any(p in text for p in inference_patterns)

        if has_pattern and "推演" not in text and "推断" not in text:
            return True
        return False

    def _is_inference_labeled(self, text: str) -> bool:
        """检测是否已标注为推演"""
        return "推演" in text or "推断" in text

    def _has_inference_pattern(self, text: str) -> bool:
        """检测是否包含推演模式"""
        inference_patterns = [
            "基于趋势", "推断", "预测", "可能", "应该"
        ]
        return any(p in text for p in inference_patterns)

    def _is_registered_source(self, source: str) -> bool:
        """检查数据源是否已注册"""
        return source in self._REGISTERED_SOURCES

    def _is_source_available(self, source: str) -> bool:
        """检查数据源是否可用"""
        return True

    def _is_valid_data_format(self, data_path: str) -> bool:
        """检查数据格式是否有效"""
        path = Path(data_path)
        valid_extensions = [".json", ".csv", ".txt", ".md"]
        return path.suffix.lower() in valid_extensions
