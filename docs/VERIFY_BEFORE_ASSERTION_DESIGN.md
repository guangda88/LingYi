# 灵字辈"先检验再断言"约束层设计

## 背景

灵字辈AI成员在工作中需要做出各种断言和决策。为了确保：
1. **可靠性**: 不做没有依据的断言
2. **诚实性**: 分清事实与推演
3. **安全性**: 不越界操作，不编造通信

需要建立"先检验再断言"（Verify Before Assertion）约束层，在AI成员进行断言之前强制进行验证。

## 核心问题

### 问题1: 无据断言
- AI成员在没有验证的情况下做出断言
- 例如："灵知知识库中有关于气功的文章"（未先验证）

### 问题2: 幻觉通信
- AI成员编造与其他成员的通信、讨论或决议
- 例如："灵通已经完成了v0.16审计"（未验证）

### 问题3: 越界操作
- AI成员在未验证边界的情况下执行工具调用
- 例如：灵知进行医学知识检索（未验证是否越界）

### 问题4: 推演混淆
- AI成员将推演当作事实来断言
- 例如："基于数据趋势，灵通下周一会上线"（未标注为推演）

## 约束层架构

### 架构层次

```
┌─────────────────────────────────────┐
│   AI成员请求 (Assertion/Action)      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   约束层 (Constraint Layer)        │
│   1. 前置检查 (Pre-Check)          │
│   2. 工具验证 (Tool Validation)    │
│   3. 边界检查 (Boundary Check)      │
│   4. 事实验证 (Fact Verification)   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   决策引擎 (Decision Engine)        │
│   - 执行 (如果所有检查通过)         │
│   - 拒绝 (如果有检查失败)           │
│   - 降级 (可以安全降级时)           │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   执行与记录 (Execution & Log)     │
│   - 执行操作                       │
│   - 记录验证过程                   │
│   - 记录断言结果                   │
└─────────────────────────────────────┘
```

## 实现设计

### 1. 约束层核心 (`constraint_layer.py`)

#### 数据结构
```python
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
```

#### 核心类
```python
class ConstraintLayer:
    """约束层 - 先检验再断言"""

    def __init__(self):
        self.validators = {
            "lingzhi": LingZhiValidator(),
            "lingflow": LingFlowValidator(),
            "lingresearch": LingYanValidator(),
            # ... 其他成员
        }
        self.logger = logging.getLogger(__name__)

    def verify_assertion(self, assertion: Assertion) -> VerificationResult:
        """验证断言"""
        member_id = assertion.member_id

        # 获取成员专用的验证器
        validator = self.validators.get(member_id)
        if not validator:
            return VerificationResult(
                passed=False,
                reason=f"Unknown member: {member_id}",
                checks=[]
            )

        # 执行验证
        checks = []
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

        # 生成结果
        if all_passed:
            return VerificationResult(
                passed=True,
                reason="All checks passed",
                checks=checks,
                recommendation=None
            )
        else:
            return VerificationResult(
                passed=False,
                reason=f"Verification failed: {self._summarize_checks(checks)}",
                checks=checks,
                recommendation=self._generate_recommendation(checks),
                requires_fallback=self._should_fallback(checks)
            )

    def _summarize_checks(self, checks: list[dict]) -> str:
        """总结检查结果"""
        failed = [c for c in checks if not c["passed"]]
        return ", ".join([f["reason"] for f in failed])

    def _generate_recommendation(self, checks: list[dict]) -> str | None:
        """生成改进建议"""
        # 根据失败的检查类型提供建议
        pass

    def _should_fallback(self, checks: list[dict]) -> bool:
        """判断是否需要降级处理"""
        # 某些失败可以安全降级处理
        pass
```

### 2. 成员专用验证器

#### 灵知验证器 (`validator_lingzhi.py`)
```python
class LingZhiValidator:
    """灵知专用验证器"""

    def pre_check(self, assertion: Assertion) -> dict:
        """前置检查"""
        # 检查断言是否为医学相关
        if self._is_medical_query(assertion.content):
            return {
                "name": "pre_check",
                "passed": False,
                "reason": "医学查询违反边界",
                "detail": "灵知不允许进行医学知识检索"
            }
        return {
            "name": "pre_check",
            "passed": True,
            "reason": "前置检查通过"
        }

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        tool_name = tool_call.get("name")

        # 验证知识库查询工具
        if tool_name == "search_knowledge":
            query = tool_call.get("arguments", {}).get("query", "")

            # 检查是否为空查询
            if not query.strip():
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": "知识库查询不能为空"
                }

            # 检查查询是否为医学相关
            if self._is_medical_query(query):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": "医学查询违反边界"
                }

            # 验证查询范围（必须在九域内）
            if not self._is_valid_domain(query):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"查询超出九域范围: {query}"
                }

        return {
            "name": "tool_validation",
            "passed": True,
            "reason": "工具调用验证通过"
        }

    def check_boundary(self, assertion: Assertion) -> dict:
        """边界检查"""
        # 检查是否违反医疗边界
        if self._is_medical_query(assertion.content):
            return {
                "name": "boundary_check",
                "passed": False,
                "reason": "违反医疗边界"
            }

        return {
            "name": "boundary_check",
            "passed": True,
            "reason": "边界检查通过"
        }

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        # 如果断言涉及知识库内容，必须先验证
        if "知识库" in assertion.content or "灵知" in assertion.content:
            # 检查是否进行了实际验证（调用工具）
            if not assertion.tool_call:
                return {
                    "name": "fact_verification",
                    "passed": False,
                    "reason": "断言涉及知识库但未进行验证",
                    "detail": "请先调用search_knowledge工具验证"
                }

        return {
            "name": "fact_verification",
            "passed": True,
            "reason": "事实验证通过"
        }

    def _is_medical_query(self, text: str) -> bool:
        """检查是否为医学查询"""
        medical_keywords = [
            "诊断", "辨证", "方剂", "处方", "治疗",
            "吃什么药", "怎么治", "开药", "医嘱",
            "病案", "病症", "症状诊断"
        ]
        return any(kw in text for kw in medical_keywords)

    def _is_valid_domain(self, query: str) -> bool:
        """检查查询是否在九域范围内"""
        domains = ["儒", "释", "道", "武", "心", "哲", "科", "气"]
        return any(domain in query for domain in domains)
```

#### 灵通验证器 (`validator_lingflow.py`)
```python
class LingFlowValidator:
    """灵通专用验证器"""

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        tool_name = tool_call.get("name")

        # 验证Git操作工具
        if tool_name in ["git_commit", "git_push", "git_branch"]:
            repo_path = tool_call.get("arguments", {}).get("repo_path", "")

            # 检查仓库路径是否存在
            if not Path(repo_path).exists():
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"仓库路径不存在: {repo_path}"
                }

            # 检查是否有权限访问
            if not self._has_repo_access(repo_path):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"无权限访问仓库: {repo_path}"
                }

            # 检查工作流状态（是否有未提交的更改）
            if not self._verify_workflow_state(repo_path):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": "工作流状态不稳定，请先检查"
                }

        # 验证审计报告生成工具
        if tool_name == "generate_audit_report":
            version = tool_call.get("arguments", {}).get("version", "")

            # 检查版本号格式
            if not self._is_valid_version(version):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"无效的版本号: {version}"
                }

            # 检查是否有对应的代码变更
            if not self._has_version_changes(version):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"版本{version}无代码变更，无法生成审计报告"
                }

        return {
            "name": "tool_validation",
            "passed": True,
            "reason": "工具调用验证通过"
        }

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        # 如果断言涉及其他成员的状态，必须先验证
        if "灵通" in assertion.content or "工作流" in assertion.content:
            if not assertion.tool_call:
                return {
                    "name": "fact_verification",
                    "passed": False,
                    "reason": "断言涉及灵通状态但未进行验证"
                }

        # 检查是否编造了与灵通相关通信
        if self._is_fabricated_communication(assertion.content):
            return {
                "name": "fact_verification",
                "passed": False,
                "reason": "检测到可能的编造通信",
                "detail": "请验证该通信是否真实发生"
            }

        return {
            "name": "fact_verification",
            "passed": True,
            "reason": "事实验证通过"
        }

    def _is_fabricated_communication(self, text: str) -> bool:
        """检测可能的编造通信"""
        # 如果提到与灵通的通信，但无验证，则可能是编造
        if "灵通" in text and "说" in text:
            return True
        return False

    def _has_repo_access(self, repo_path: str) -> bool:
        """检查是否有仓库访问权限"""
        # 实现权限检查逻辑
        pass

    def _verify_workflow_state(self, repo_path: str) -> bool:
        """验证工作流状态"""
        # 检查Git状态
        pass

    def _is_valid_version(self, version: str) -> bool:
        """验证版本号格式"""
        import re
        pattern = r"^v\d+\.\d+(\.\d+)?$"
        return bool(re.match(pattern, version))

    def _has_version_changes(self, version: str) -> bool:
        """检查版本是否有代码变更"""
        # 检查Git历史
        pass
```

#### 灵妍验证器 (`validator_lingyan.py`)
```python
class LingYanValidator:
    """灵妍专用验证器"""

    def validate_tool_call(self, tool_call: dict) -> dict:
        """验证工具调用"""
        tool_name = tool_call.get("name")

        # 验证数据源访问工具
        if tool_name == "access_data_source":
            source = tool_call.get("arguments", {}).get("source", "")

            # 检查数据源是否已注册
            if not self._is_registered_source(source):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"未注册的数据源: {source}"
                }

            # 检查数据源是否可用
            if not self._is_source_available(source):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"数据源不可用: {source}"
                }

        # 验证数据分析工具
        if tool_name == "analyze_data":
            data_path = tool_call.get("arguments", {}).get("data_path", "")

            # 检查数据文件是否存在
            if not Path(data_path).exists():
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"数据文件不存在: {data_path}"
                }

            # 检查数据格式
            if not self._is_valid_data_format(data_path):
                return {
                    "name": "tool_validation",
                    "passed": False,
                    "reason": f"无效的数据格式: {data_path}"
                }

        return {
            "name": "tool_validation",
            "passed": True,
            "reason": "工具调用验证通过"
        }

    def verify_fact(self, assertion: Assertion) -> dict:
        """事实验证"""
        # 如果断言涉及研究数据或结论，必须先验证
        if "研究" in assertion.content or "实验" in assertion.content:
            if not assertion.tool_call:
                return {
                    "name": "fact_verification",
                    "passed": False,
                    "reason": "断言涉及研究但未进行验证"
                }

        # 检查是否为推演而非事实
        if self._is_inference_not_fact(assertion.content):
            return {
                "name": "fact_verification",
                "passed": False,
                "reason": "推演需要标注",
                "detail": "请在断言中标注'基于推演'或'推断'"
            }

        return {
            "name": "fact_verification",
            "passed": True,
            "reason": "事实验证通过"
        }

    def _is_inference_not_fact(self, text: str) -> bool:
        """检测是否为推演而非事实"""
        inference_patterns = [
            "基于趋势", "推断", "预测", "可能", "应该"
        ]
        has_pattern = any(p in text for p in inference_patterns)

        # 如果有推演模式但没有标注，则返回True
        if has_pattern and "推演" not in text and "推断" not in text:
            return True
        return False
```

### 3. 集成点

#### 在MCP工具中集成
```python
# src/lingyi/mcp_server.py
from .constraint_layer import ConstraintLayer, Assertion

_constraint_layer = ConstraintLayer()

@mcp.tool()
async def search_knowledge(query: str) -> str:
    """搜索灵知知识库"""
    # 创建断言
    assertion = Assertion(
        member_id="lingzhi",
        assertion_type="action",
        content=f"搜索知识库: {query}",
        tool_call={
            "name": "search_knowledge",
            "arguments": {"query": query}
        }
    )

    # 验证断言
    result = _constraint_layer.verify_assertion(assertion)
    if not result.passed:
        return f"❌ 验证失败: {result.reason}\n建议: {result.recommendation}"

    # 执行工具调用
    from .ask import _do_knowledge_search
    return _do_knowledge_search(query)
```

#### 在Council讨论中集成
```python
# src/lingyi/council.py
from .constraint_layer import ConstraintLayer, Assertion

_constraint_layer = ConstraintLayer()

def _validate_message_before_reply(message: dict) -> bool:
    """验证消息内容，防止编造通信"""
    if "灵通说" in message.get("content", ""):
        assertion = Assertion(
            member_id=message.get("from_id", "unknown"),
            assertion_type="communication",
            content=message.get("content", "")
        )

        result = _constraint_layer.verify_assertion(assertion)
        if not result.passed:
            logger.warning(f"消息验证失败: {result.reason}")
            return False
    return True
```

### 4. 日志和监控

```python
@dataclass
class VerificationLog:
    """验证日志"""
    timestamp: str
    member_id: str
    assertion_type: str
    assertion_content: str
    verification_result: VerificationResult
    action_taken: str  # "approved" | "rejected" | "fallback"

class VerificationMonitor:
    """验证监控"""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.logs = []

    def log_verification(self, assertion: Assertion, result: VerificationResult, action: str):
        """记录验证"""
        log = VerificationLog(
            timestamp=datetime.now().isoformat(),
            member_id=assertion.member_id,
            assertion_type=assertion.assertion_type,
            assertion_content=assertion.content,
            verification_result=result,
            action_taken=action
        )
        self.logs.append(log)
        self._append_to_file(log)

    def get_stats(self, days: int = 7) -> dict:
        """获取统计"""
        # 计算通过率、拒绝率、降级率
        pass

    def _append_to_file(self, log: VerificationLog):
        """追加到日志文件"""
        # 实现日志持久化
        pass
```

## 使用示例

### 示例1: 灵知搜索知识库
```python
from constraint_layer import ConstraintLayer, Assertion

layer = ConstraintLayer()

# 创建断言
assertion = Assertion(
    member_id="lingzhi",
    assertion_type="action",
    content="搜索知识库：气功的修炼方法",
    tool_call={
        "name": "search_knowledge",
        "arguments": {"query": "气功的修炼方法"}
    }
)

# 验证
result = layer.verify_assertion(assertion)
if result.passed:
    # 执行搜索
    print("✅ 验证通过，可以执行")
else:
    print(f"❌ 验证失败: {result.reason}")
    print(f"建议: {result.recommendation}")
```

### 示例2: 灵通提交代码
```python
assertion = Assertion(
    member_id="lingflow",
    assertion_type="action",
    content="提交代码变更",
    tool_call={
        "name": "git_commit",
        "arguments": {
            "repo_path": "/home/ai/LingFlow",
            "message": "feat: 添加新功能"
        }
    }
)

result = layer.verify_assertion(assertion)
if result.passed:
    # 执行提交
    print("✅ 验证通过，可以提交")
else:
    print(f"❌ 验证失败: {result.reason}")
```

### 示例3: 防止编造通信
```python
assertion = Assertion(
    member_id="lingyi",
    assertion_type="communication",
    content="灵通说v0.16审计已经完成"
)

result = layer.verify_assertion(assertion)
if result.passed:
    print("✅ 通信内容有效")
else:
    print(f"❌ 可能的编造通信: {result.reason}")
    print(f"建议: 请先验证该通信是否真实发生")
```

## 实施计划

### Phase 1: 核心框架 (Week 1)
- [x] 设计约束层架构
- [ ] 实现 `ConstraintLayer` 核心类
- [ ] 实现基础数据结构（Assertion, VerificationResult）
- [ ] 实现日志和监控模块
- [ ] 单元测试

### Phase 2: 成员验证器 (Week 2)
- [ ] 实现 `LingZhiValidator`
- [ ] 实现 `LingFlowValidator`
- [ ] 实现 `LingYanValidator`
- [ ] 集成测试

### Phase 3: 系统集成 (Week 3)
- [ ] 在MCP工具中集成约束层
- [ ] 在Council讨论中集成约束层
- [ ] 在CLI命令中添加验证检查
- [ ] 端到端测试

### Phase 4: 监控和优化 (Week 4)
- [ ] 部署验证监控系统
- [ ] 生成首份验证报告
- [ ] 根据反馈优化验证逻辑
- [ ] 文档和培训

## 成功指标

### 定量指标
- **验证通过率**: 目标 >80%（合理的断言能通过）
- **编造通信拦截率**: 目标 100%
- **边界违规拦截率**: 目标 100%
- **验证延迟**: 目标 <100ms

### 定性指标
- AI成员反馈验证有用
- 减少了无据断言
- 提高了通信可靠性
- 形成了验证习惯

## 风险和缓解

### 风险1: 验证过严
- **风险**: 合理的断言被拒绝
- **缓解**: 允许申诉机制，快速调整验证规则

### 风险2: 性能影响
- **风险**: 验证导致操作延迟
- **缓解**: 缓存验证结果，异步验证

### 风险3: 遗漏验证场景
- **风险**: 某些类型的断言未被验证
- **缓解**: 持续监控，及时发现遗漏

## 相关文档

- `docs/MISSION.md` - 灵依宪章（价值观和边界）
- `docs/BOUNDARY_MANAGEMENT.md` - 边界管理
- `docs/COUNCIL_PROTOCOL.md` - Council协议（待创建）

---

**创建日期**: 2026-04-08
**版本**: v1.0
**状态**: 🟢 设计完成，待实施
