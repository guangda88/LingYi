"""验证器基类与灵知验证器。"""

from __future__ import annotations

from ._constraint_models import Assertion


class BaseValidator:
    """验证器基类"""

    def pre_check(self, assertion: Assertion) -> dict:
        """前置检查"""
        return {
            "name": "pre_check",
            "passed": True,
            "reason": "前置检查通过"
        }

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        return {
            "name": "tool_validation",
            "passed": True,
            "reason": "工具调用验证通过"
        }

    def check_boundary(self, assertion: Assertion) -> dict:
        """边界检查"""
        return {
            "name": "boundary_check",
            "passed": True,
            "reason": "边界检查通过"
        }

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        return {
            "name": "fact_verification",
            "passed": True,
            "reason": "事实验证通过"
        }


class LingZhiValidator(BaseValidator):
    """灵知专用验证器"""

    _MEDICAL_KEYWORDS = [
        "诊断", "辨证", "方剂", "处方", "治疗",
        "吃什么药", "怎么治", "开药", "医嘱",
        "病案", "病症", "症状诊断"
    ]

    _VALID_DOMAINS = ["儒", "释", "道", "武", "心", "哲", "科", "气"]

    def pre_check(self, assertion: Assertion) -> dict:
        """前置检查"""
        if self._is_medical_query(assertion.content):
            return {
                "name": "pre_check",
                "passed": False,
                "reason": "医学查询违反边界",
                "detail": "灵知不允许进行医学知识检索"
            }
        return super().pre_check(assertion)

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        if not tool_call:
            return super().validate_tool_call(tool_call)

        tool_name = tool_call.get("name")

        if tool_name == "search_knowledge":
            query = tool_call.get("arguments", {}).get("query", "")

            if not query.strip():
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": "知识库查询不能为空"
                }

            if self._is_medical_query(query):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": "医学查询违反边界"
                }

            if not self._is_valid_domain(query):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"查询超出九域范围: {query}",
                    "detail": f"九域包括: {', '.join(self._VALID_DOMAINS)}"
                }

        return super().validate_tool_call(tool_call)

    def check_boundary(self, assertion: Assertion) -> dict:
        """边界检查"""
        if self._is_medical_query(assertion.content):
            return {
                "name": "boundary_check",
                "passed": False,
                "reason": "违反医疗边界"
            }

        return super().check_boundary(assertion)

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        if "知识库" in assertion.content or "灵知" in assertion.content:
            if not assertion.tool_call:
                return {
                    "name": "fact_verification",
                    "passed": False,
                    "reason": "断言涉及知识库但未进行验证",
                    "detail": "请先调用search_knowledge工具验证"
                }

        return super().verify_fact(assertion)

    def _is_medical_query(self, text: str) -> bool:
        """检查是否为医学查询"""
        return any(kw in text for kw in self._MEDICAL_KEYWORDS)

    def _is_valid_domain(self, query: str) -> bool:
        """检查查询是否在九域范围内"""
        return any(domain in query for domain in self._VALID_DOMAINS)
