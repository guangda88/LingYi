# 约束层验证快速参考

## 概述

约束层（Constraint Layer）是灵依为灵字辈AI成员实现的"先检验再断言"安全机制。在AI成员做出任何断言之前，强制进行验证，防止编造、越界和无根据的断言。

## 快速使用

### 1. CLI命令

#### 验证断言
```bash
lingyi verify check <member_id> <assertion_type> <content> [--tool <tool_json>]
```

**示例**：
```bash
# 验证灵知的断言
lingyi verify check lingzhi fact "请问儒家思想的核心"

# 验证灵妍的推演
lingyi verify check lingresearch fact "（推演）基于趋势分析，数据会上升"

# 验证灵通的Git操作
lingyi verify check lingflow action "提交代码" --tool '{"name":"git_commit","arguments":{"repo_path":"/home/ai/LingYi"}}'
```

#### 查看统计
```bash
lingyi verify stats [--days 7]
```

**输出示例**：
```
近7天验证统计:
  总数: 10
  通过: 6
  拒绝: 4
  降级: 0
  通过率: 60.0%

按成员统计:
  lingzhi:
    总数: 4
    通过: 3
    拒绝: 1
    通过率: 75.0%
  lingflow:
    总数: 3
    通过: 2
    拒绝: 1
    通过率: 66.7%
  lingresearch:
    总数: 3
    通过: 1
    拒绝: 2
    通过率: 33.3%
```

#### 查看日志
```bash
lingyi verify log [--days 7] [--member <member_id>] [--limit 20]
```

**示例**：
```bash
# 查看最近7天的所有验证
lingyi verify log --days 7

# 只看灵知的验证
lingyi verify log --member lingzhi --days 30

# 查看最近50条记录
lingyi verify log --limit 50
```

### 2. MCP工具

如果灵依通过MCP协议被调用，约束层会自动验证以下工具：

#### `ask_lingzhi` - 灵知问答
**自动拦截**：
- 医学查询（诊断、辨证、方剂、处方等）
- 超出九域的查询

**示例**：
```json
{
  "tool": "ask_lingzhi",
  "question": "请问儒家思想的核心"
}
```

#### `search_knowledge` - 灵知搜索
**自动拦截**：
- 医学查询
- 超出九域的查询

**示例**：
```json
{
  "tool": "search_knowledge",
  "query": "儒家核心思想",
  "category": "",
  "top_k": 5
}
```

#### `verify_assertion` - 手动验证
**参数**：
- `member_id`: 成员ID (lingzhi/lingflow/lingresearch)
- `assertion_type`: 断言类型 (fact/action/communication)
- `content`: 断言内容
- `tool_call`: 工具调用信息（可选）

**示例**：
```json
{
  "tool": "verify_assertion",
  "member_id": "lingresearch",
  "assertion_type": "fact",
  "content": "（推演）基于趋势分析，数据会上升"
}
```

#### `verification_stats` - 验证统计
**参数**：
- `days`: 统计天数（默认7）

**示例**：
```json
{
  "tool": "verification_stats",
  "days": 7
}
```

#### `verification_log` - 验证日志
**参数**：
- `days`: 查询天数（默认7）
- `member_id`: 按成员ID筛选（可选）

**示例**：
```json
{
  "tool": "verification_log",
  "days": 7,
  "member_id": "lingzhi"
}
```

### 3. API端点

#### `POST /api/verification/check` - 验证断言

**请求体**：
```json
{
  "member_id": "lingzhi",
  "assertion_type": "fact",
  "content": "请问儒家思想的核心",
  "tool_call": {
    "name": "search_knowledge",
    "arguments": {"query": "儒家"}
  }
}
```

**响应**：
```json
{
  "passed": true,
  "reason": "All checks passed",
  "checks": [...],
  "recommendation": null,
  "requires_fallback": false
}
```

#### `GET /api/verification/stats` - 获取统计

**参数**：
- `days`: 统计天数（默认7）

**示例**：
```bash
curl http://localhost:8900/api/verification/stats?days=7
```

#### `GET /api/verification/log` - 查询日志

**参数**：
- `days`: 查询天数（默认7）
- `member_id`: 按成员ID筛选（可选）

**示例**：
```bash
curl http://localhost:8900/api/verification/log?days=7&member_id=lingzhi
```

## 三大验证器

### 1. 灵知验证器 (LingZhiValidator)

**职责**：验证知识库查询和断言

**拦截规则**：
- ❌ **医学查询**：包含"诊断"、"辨证"、"方剂"、"处方"、"治疗"、"吃什么药"、"怎么治"、"开药"、"医嘱"、"病案"、"病症"、"症状诊断"
- ❌ **超出九域**：不在儒/释/道/武/心/哲/科/气范围内
- ❌ **未验证断言**：涉及知识库但未进行工具验证

**正确使用**：
```bash
# ✅ 正常查询
ask_lingzhi "请问儒家思想的核心"

# ❌ 医学查询（会被拦截）
ask_lingzhi "请问如何诊断气功"

# ✅ 正确的断言方式
# 1. 先调用工具验证
search_knowledge "儒家核心思想"
# 2. 再做出断言
"根据知识库，儒家核心思想是仁爱"
```

### 2. 灵通验证器 (LingFlowValidator)

**职责**：验证Git操作和工作流断言

**拦截规则**：
- ❌ **编造通信**：包含"灵通说"模式，且无验证
- ❌ **路径不存在**：Git仓库路径无效
- ❌ **无权限**：无权限访问仓库
- ❌ **工作流不稳定**：Git状态异常
- ❌ **版本号格式错误**：不符合 v0.16 或 v0.16.0 格式
- ❌ **无代码变更**：生成审计报告但无对应变更

**正确使用**：
```bash
# ✅ 正常通信
"根据Git日志，v0.16版本已更新"

# ❌ 编造通信（会被拦截）
"灵通说v0.16已完成审计"

# ✅ 正确的Git操作
git_commit repo_path="/home/ai/LingYi"

# ❌ 路径不存在（会被拦截）
git_commit repo_path="/nonexistent/path"
```

### 3. 灵妍验证器 (LingYanValidator)

**职责**：验证数据源访问和推演断言

**拦截规则**：
- ❌ **未注册数据源**：访问不在 research_db/experiment_logs/papers 中的数据源
- ❌ **数据文件不存在**：数据文件路径无效
- ❌ **数据格式错误**：不是 JSON/CSV/TXT/MD 格式
- ❌ **未标注推演**：包含"基于趋势"、"推断"、"预测"、"可能"、"应该"但未标注
- ❌ **研究未验证**：涉及"研究"/"实验"但未标注推演且无工具调用

**正确使用**：
```bash
# ✅ 推演已标注
"（推演）基于趋势分析，未来三个月数据会上升"

# ❌ 未标注推演（会被拦截）
"基于趋势预测，数据会上升"

# ✅ 研究相关 + 工具验证
analyze_data data_path="/home/ai/experiment_data.json"
"根据数据分析，效率提高了20%"

# ❌ 研究无验证（会被拦截）
"实验数据表明效率提高了20%" # 但没有调用工具验证

# ✅ 已标注推演的研究（不需要工具验证）
"（推演）基于实验趋势，效率应该会提高"
```

## 四阶段验证流程

约束层对每个断言执行四个阶段的验证：

```
断言请求
    ↓
1. 前置检查 (Pre-Check)
   - 检查明显违规（如医学关键词）
   - 快速失败机制
    ↓
2. 工具验证 (Tool Validation)
   - 验证工具调用参数
   - 检查路径、格式、权限等
    ↓
3. 边界检查 (Boundary Check)
   - 强制执行成员特定边界
   - 检查是否越界操作
    ↓
4. 事实验证 (Fact Verification)
   - 确保断言有依据
   - 区分事实与推演
    ↓
验证结果
   - 通过: 执行断言
   - 失败但可降级: 附加警告后执行
   - 失败不可降级: 拒绝断言
```

## 验证日志

### 日志位置
`~/.lingyi/verification_log.json`

### 日志格式
```json
[
  {
    "timestamp": "2026-04-08T16:55:34.218727",
    "member_id": "lingzhi",
    "assertion_type": "fact",
    "assertion_content": "请问如何诊断气功",
    "verification_result": {
      "passed": false,
      "reason": "医学查询违反边界, 违反医疗边界",
      "checks": [
        {
          "name": "pre_check",
          "passed": false,
          "reason": "医学查询违反边界",
          "detail": "灵知不允许进行医学知识检索"
        },
        {
          "name": "tool_validation",
          "passed": false,
          "reason": "医学查询违反边界"
        },
        {
          "name": "boundary_check",
          "passed": false,
          "reason": "违反医疗边界"
        },
        {
          "name": "fact_verification",
          "passed": true,
          "reason": "事实验证通过"
        }
      ],
      "recommendation": "前置检查未通过，请检查断言内容是否合规",
      "requires_fallback": false
    },
    "action_taken": "rejected"
  }
]
```

### 字段说明
- `timestamp`: 验证时间
- `member_id`: 成员ID
- `assertion_type`: 断言类型 (fact/action/communication)
- `assertion_content`: 断言内容（截断至200字符）
- `verification_result`: 验证结果对象
  - `passed`: 是否通过
  - `reason`: 失败原因（或"All checks passed"）
  - `checks`: 各阶段检查详情
  - `recommendation`: 改进建议
  - `requires_fallback`: 是否可降级
- `action_taken`: 采取的行动 (approved/rejected/fallback)

## 常见问题

### Q1: 如何解除医学查询拦截？
**A**: 灵知的医学边界是强制性的，不可解除。医学相关查询应由专业医疗系统处理。

### Q2: 推演必须怎么标注？
**A**: 在断言中包含"推演"或"推断"关键词，通常放在开头或用括号标注：
```
（推演）基于趋势分析...
基于推断...
```

### Q3: 为什么我的断言被拦截了？
**A**: 检查以下方面：
1. 是否违反了成员边界（如灵知的医学边界）
2. 是否未标注推演但包含推演模式
3. 是否涉及研究/实验但无工具验证
4. 是否编造了通信或数据
5. 工具调用参数是否正确

使用 `lingyi verify check` 可以查看详细的失败原因和改进建议。

### Q4: 如何提高验证通过率？
**A**:
1. 明确区分事实和推演，推演必须标注
2. 涉及外部系统的断言先进行工具验证
3. 遵守成员特定边界
4. 避免编造通信或数据

### Q5: 约束层会影响性能吗？
**A**: 影响很小。每次验证耗时约1-5ms（内存计算），日志写入是异步的。对于大部分场景，影响可忽略。

## 高级用法

### 自定义验证器

可以扩展新的验证器，继承 `BaseValidator` 并实现四个验证方法：

```python
from lingyi.constraint_layer import BaseValidator

class CustomValidator(BaseValidator):
    def pre_check(self, assertion: Assertion) -> dict:
        # 实现前置检查
        pass

    def validate_tool_call(self, tool_call: dict) -> dict:
        # 实现工具验证
        pass

    def check_boundary(self, assertion: Assertion) -> dict:
        # 实现边界检查
        pass

    def verify_fact(self, assertion: Assertion) -> dict:
        # 实现事实验证
        pass

# 注册到约束层
from lingyi.constraint_layer import ConstraintLayer
cl = ConstraintLayer()
cl.validators["custom_member"] = CustomValidator()
```

### 编程接口

```python
from lingyi.constraint_layer import ConstraintLayer, Assertion

# 初始化约束层
cl = ConstraintLayer()

# 构造断言
assertion = Assertion(
    member_id="lingzhi",
    assertion_type="fact",
    content="请问儒家思想",
    tool_call={
        "name": "search_knowledge",
        "arguments": {"query": "儒家"}
    }
)

# 验证断言
result = cl.verify_assertion(assertion)

# 检查结果
if result.passed:
    print("验证通过")
else:
    print(f"验证失败: {result.reason}")
    if result.recommendation:
        print(f"建议: {result.recommendation}")

# 获取统计
stats = cl.get_verification_stats(days=7)
print(f"通过率: {stats['approval_rate']}%")
```

## 相关文档

- [约束层设计文档](./VERIFY_BEFORE_ASSERTION_DESIGN.md)
- [约束层实现总结](./CONSTRAINT_LAYER_IMPLEMENTATION.md)
- [边界管理](./BOUNDARY_MANAGEMENT.md)
