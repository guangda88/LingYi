# 灵依 LingYi — 宪章原则规范规划审计报告

> **审计日期**: 2026-04-03  
> **审计版本**: v0.13.0  
> **审计范围**: 代码库、文档、宪章对齐、原则合规、安全规范、规划一致性  
> **审计依据**: `docs/MISSION.md`（宪章）、`docs/DEVELOPMENT_PRINCIPLES.md`（开发原则）、`docs/DEVELOPMENT_PLAN.md`（规划）

---

## 总评

| 维度 | 评分 | 说明 |
|------|:----:|------|
| 宪章对齐 | **B+** | 核心价值观执行良好，但 ask.py 缺医疗查询护栏 |
| 原则合规 | **A-** | 10条原则大体遵守，schedule.py 微超限 |
| 代码规范 | **B+** | 命名/格式/安全良好，部分异常处理缺失 |
| 规划一致性 | **B** | 核心版本号一致，但 AGENTS.md/README 严重滞后 |
| 测试覆盖 | **A** | 207 测试覆盖所有业务模块，仅 db.py/models.py 无直接测试 |

**总评: B+** — 项目健康，v0.1–v0.13 渐进交付节奏良好。主要问题集中在文档陈旧和 ask.py 边界护栏。

---

## 一、宪章对齐审计

### 1.1 价值观优先级执行

| # | 价值观 | 评估 | 证据 |
|:-:|--------|:----:|------|
| 1 | **守界** | ⚠️ | 见下文边界审计 |
| 2 | **惜时** | ✅ | CLI 输出简洁，`--short` 模式一行摘要，无冗余寒暄 |
| 3 | **节约** | ✅ | 零额外依赖（urllib/json/pathlib），所有外部调用有超时限制 |
| 4 | **知己** | ✅ | pref.py 持久化偏好，session.py 跨会话记忆，digest.py 自动提取偏好 |
| 5 | **可靠** | ✅ | 所有 collect_* 函数 graceful degradation，不存在时返回 `{"available": False}` |

### 1.2 边界合规

| 领域 | 宪章规定 | 实际执行 | 状态 |
|------|---------|---------|:----:|
| 医疗·日程 | ✅ 做：门诊日程安排、上诊提醒 | schedule.py init_clinic()、check_remind() | ✅ |
| 医疗·诊疗 | ❌ 不做：不碰诊疗、方剂、辨证 | 无诊断/处方/辨证代码 | ✅ |
| 医疗·知识检索 | ❌ 不做：医学知识检索 | ask.py 允许 `--category 中医` 无过滤地转发查询 | **🔴 违规** |
| 编程·辅助 | ✅ 做：辅助学习、调试、答疑 | code.py review/deps/refactor + ask.py | ✅ |
| 编程·决策 | ❌ 不做：不替做架构决策 | suggest_refactor() 仅提建议，不自动执行 | ✅ |
| 研究 | ✅ 做：论文管理、学术日程 | plan.py 五大领域含研究/论文/学术 | ✅ |
| 研究·代写 | ❌ 不做：不替写论文 | 无论文生成代码 | ✅ |
| 日常 | ✅ 做：备忘、提醒、信息整理 | memo/digest/briefing 模块 | ✅ |
| 日常·社交 | ❌ 不做：不做社交娱乐 | chat.py 仅关键词匹配，非社交 | ✅ |

### 🔴 发现：ask.py 医疗查询无护栏

**问题**: `ask.py:33-62` 的 `ask_knowledge()` 对用户输入零过滤，会原样转发任何查询到灵知后端，包括诊断、方剂、辨证等医疗查询。宪章明确"不碰医学知识检索"。

**涉及文件**:
- `src/lingyi/ask.py:33-62` — 无输入验证
- `src/lingyi/commands/connect.py:13` — `--category` 选项包含 `中医`

**建议修复**:
```python
# ask.py 中添加护栏
_MEDICAL_KEYWORDS = ["诊断", "辨证", "方剂", "处方", "症状", "治疗", "怎么治", "吃什么药"]

def _is_medical_query(query: str) -> bool:
    return any(kw in query for kw in _MEDICAL_KEYWORDS)

def ask_knowledge(query, category=None, ...):
    if _is_medical_query(query) or category == "中医":
        return {"available": False, "answer": "⚠ 灵依不做医学知识检索，请咨询专业医师。"}
    ...
```

### ⚠️ 发现：排班描述含敏感信息

**问题**: schedule.py 的 `description` 字段为自由文本，用户可能填入医院名称、地址等。这些信息会：
- 明文存储在 SQLite 和 presets.json
- 通过 `--speak` TTS 朗读出来
- 无任何脱敏处理

**建议**: 在 `format_schedule()` 和 TTS 输出前添加脱敏提醒，或在 preset 模板中标注"请勿填写患者信息"。

---

## 二、开发原则审计

### 2.1 十条原则逐条检查

| # | 原则 | 评估 | 证据 |
|:-:|------|:----:|------|
| 1 | 需求驱动 | ✅ | 每个版本对应明确需求（日程/记忆/语音/情报） |
| 2 | 最小可用 | ✅ | 每版只做一件事，v0.1 仅备忘录就上线 |
| 3 | 复用优先 | ✅ | urllib 不用 requests，lingclaude SDK 复用而非自建 |
| 4 | 节约 token | ✅ | 本地优先，HTTP 调用仅 briefing/ask，无多余 API |
| 5 | 中文为主/代码英文 | ✅ | 全部 CLI 输出中文，变量/函数名英文，commit `feat: 中文` |
| 6 | 安全底线 | ⚠️ | 见下文安全审计 |
| 7 | 代码简洁 | ⚠️ | schedule.py 301行（微超300限制）|
| 8 | 核心路径有测试 | ✅ | 207测试覆盖全部业务模块 |
| 9 | 小步提交 | ✅ | 22个commit，每版本独立提交 |
| 10 | 每天能用上 | ✅ | 日程/备忘/提醒/巡逻每天都在用 |

### 2.2 代码简洁性

**⚠️ 超限文件**: `src/lingyi/schedule.py` — **301行**（原则规定≤300行）

这是系统中功能最密集的模块（排班 CRUD + 今日/本周视图 + 5种预设 + 智能提醒 + 练功/日记/问道提醒）。超限1行，实际可接受。

**建议**: 若继续增长，考虑将预设初始化（init_clinic/practice/ask/journal）拆到 `schedule_presets.py`。

### 2.3 代码质量问题

| 问题 | 严重度 | 位置 | 说明 |
|------|:------:|------|------|
| 未使用的 import | 低 | `commands/chat.py:3` | `import sys` 未使用 |
| 重复 import | 低 | `commands/schedule.py:126-128` | 函数内重复导入已在模块级导入的符号 |
| 文件句柄未关闭 | 中 | `commands/digest.py:21` | `open(file_path).read()` 无 `with` |
| DB 连接无上下文管理 | 中 | 6个模块约20处 | `conn = get_db()` 无 `try/finally` |
| STT 重复导入逻辑 | 低 | `stt.py:21-29` | sherpa_onnx 的 fallback 逻辑冗余 |
| SQL f-string | 低 | `schedule.py:100`, `project.py:100` | 列名通过 f-string 拼接（当前安全但脆弱）|

---

## 三、安全审计

### 3.1 安全检查清单

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 硬编码密码/密钥 | ✅ | 未发现 |
| .gitignore 完整性 | ⚠️ | 缺 `.lingflow/`、`.benchmarks/`、`.DS_Store`、`*.swp` |
| presets.json 不入库 | ✅ | 已在 .gitignore |
| *.db 不入库 | ✅ | 已在 .gitignore |
| .env 不入库 | ✅ | 已在 .gitignore |
| *.key 不入库 | ✅ | 已在 .gitignore |

### 🔴 发现：测试数据含真实私人信息

**文件**: `tests/test_presets.json` — 包含：
- 真实医院名称（泰安八十八医院、禾康中医医院等）
- 14个项目的真实名称、仓库地址、版本号
- 真实本地路径（`/home/ai/LingYi`）

**风险**: 若仓库公开，这些信息直接暴露。

**建议**: 使用匿名化数据替换真实医院名，或对此文件加 .gitignore。

### 🔴 发现：docs/ 含个人身份信息

| 文件 | 内容 | 风险 |
|------|------|------|
| `docs/USER_PROFILE.md` | GitHub用户名、域名、硬件信息、医疗执业详情 | 高 |
| `docs/DOUBAN_CONVERSATION_SUMMARY.md` | 真实身份（退休主任中医师）、项目策略、token用量 | 高 |
| `docs/JOURNEY.md` | 项目发展历程含个人信息 | 中 |
| `docs/PROJECT_EVALUATION.md` | 项目评估含战略信息 | 中 |

**建议**: 若仓库会公开，这些文件需移除或加入 .gitignore。当前为私人仓库，风险可控但仍建议标注。

### 3.2 .gitignore 补充建议

```gitignore
# 建议添加：
.lingflow/
.benchmarks/
.DS_Store
*.swp
*.swo
*~

# 建议评估是否需要忽略：
docs/USER_PROFILE.md
docs/DOUBAN_CONVERSATION_SUMMARY.md
tests/test_presets.json
```

---

## 四、规划一致性审计

### 4.1 版本号一致性

| 来源 | 版本号 | 状态 |
|------|--------|:----:|
| `src/lingyi/__init__.py` | 0.13.0 | ✅ |
| `pyproject.toml` | 0.13.0 | ✅ |
| `AGENTS.md` | **0.7.0** | **🔴 滞后6版本** |
| `README.md` | **v0.4** | **🔴 滞后9版本** |
| `DEVELOPMENT_PLAN.md` | v0.1–v0.13 ✅标记 | ✅ |
| `PRD.md` | 0.1.0 | **🔴 滞后** |
| Git tags | **无** | **⚠️ 缺失** |

### 4.2 严重滞后文档

#### AGENTS.md（滞后 v0.7→v0.13）

| 过时内容 | 当前实际 |
|---------|---------|
| 版本 `0.7.0` | `0.13.0` |
| 129 测试 | 207 测试 |
| 版本表止于 v0.7 | 已到 v0.13 |
| 项目结构缺少 10 个模块 | 缺 digest/stt/mobile/briefing/ask/code/commands(digest,voice,mobile,briefing) |
| "129 tests" | "207 tests" |

#### README.md（滞后 v0.4→v0.13）

README 仅记录 v0.1–v0.4 功能，缺少 v0.5（记忆）至 v0.13（情报汇总）的全部功能说明。

#### PRD.md

版本号标注 `0.1.0`，版本规划仅到 v0.7+，未更新实际交付状态。

### 4.3 Git Tags 缺失

尽管已交付 v0.1–v0.13，**无任何 git tag**。开发原则明确要求：

> 重要里程碑打 tag：`git tag v0.x.0`

**建议**: 为已完成版本补打标签：
```bash
git tag v0.13.0  # 当前
```

### 4.4 DEVELOPMENT_PLAN.md 重复行

文件末尾有 v0.12 重复三行（已在新版本中修复）。

---

## 五、测试覆盖审计

### 5.1 覆盖总览

| 指标 | 数值 |
|------|------|
| 总测试数 | **207** |
| 测试类 | 33 |
| 测试文件 | 1 (`tests/test_basic.py`) |
| 版本演进 | v0.1: 基础 → v0.13: 207 测试 |

### 5.2 模块覆盖矩阵

| 模块 | 测试数 | 状态 |
|------|:------:|:----:|
| memo.py | 7 | ✅ |
| schedule.py | 29 | ✅ |
| project.py | 15 | ✅ |
| plan.py | 25 | ✅ |
| config.py | 6 | ✅ |
| patrol.py | 4 | ✅ |
| session.py | 14 | ✅ |
| pref.py | 11 | ✅ |
| report.py | 5 | ✅ |
| tts.py | 4 | ✅ |
| ask.py | 12 | ✅ |
| code.py | 18 | ✅ |
| digest.py | 14 | ✅ |
| stt.py | 11 | ✅ |
| mobile.py | 11 | ✅ |
| briefing.py | 12 | ✅ |
| cli.py | 间接覆盖 | ✅ |
| **db.py** | **0** | **⚠️ 无直接测试** |
| **models.py** | **0** | **⚠️ 无直接测试** |
| **commands/voice.py** | **0** | **⚠️ 无直接测试** |

### 5.3 关键模块缺失

- **db.py**: 原则要求"数据存取→必须测"。虽然所有测试通过 `tmp_db` fixture 间接使用了 db.py，但 schema 初始化、连接异常、错误路径未被直接测试。
- **models.py**: 纯 dataclass，风险极低，但字段验证未测试。
- **commands/voice.py**: `lingyi stt` 命令有 `stt-status` CLI 测试但 `stt` 录音命令未直接测试。

---

## 六、架构与设计审计

### 6.1 两层架构一致性

全部模块严格遵循 Logic + Commands 分层：

```
src/lingyi/briefing.py     → commands/briefing.py    ✅
src/lingyi/digest.py       → commands/digest.py      ✅
src/lingyi/stt.py          → commands/voice.py       ✅
src/lingyi/mobile.py       → commands/mobile.py      ✅
src/lingyi/ask.py          → commands/connect.py     ✅
src/lingyi/code.py         → commands/connect.py     ✅
...全部17个模块均遵循
```

### 6.2 依赖管理

| 依赖 | 用途 | 必要性 |
|------|------|--------|
| click | CLI 框架 | ✅ 必要 |
| edge-tts | TTS 语音 | ✅ 必要 |
| stdlib (urllib/json/pathlib/sqlite3) | 基础 | ✅ 零额外依赖 |

**未引入 lingflow**: 原则要求"灵通有→import lingflow"，但当前灵依功能不依赖灵通。`import lingclaude` 仅在 code.py 中动态尝试导入（SDK可能不存在）。✅ 合理。

### 6.3 数据库设计

6 张表结构清晰，关系合理：
- memos / schedules / projects / plans / sessions / preferences
- 所有查询使用参数化（`?`），无 SQL 注入风险
- WAL 模式 + Foreign Keys 启用

---

## 七、问题汇总与优先级

### 🔴 严重（3）

| # | 问题 | 修复建议 |
|:-:|------|---------|
| S1 | ask.py 无医疗查询护栏，违反宪章"不碰医学知识检索" | 添加关键词过滤 + 中医类别拦截 |
| S2 | AGENTS.md 版本/结构严重滞后（v0.7 vs v0.13） | 全面更新至 v0.13 |
| S3 | README.md 版本严重滞后（v0.4 vs v0.13） | 全面重写 |

### 🟡 中等（5）

| # | 问题 | 修复建议 |
|:-:|------|---------|
| M1 | test_presets.json 含真实医院名称 | 匿名化处理 |
| M2 | docs/ 含个人身份信息 | 加 .gitignore 或脱敏 |
| M3 | db.py 无直接测试 | 添加 schema/init 测试 |
| M4 | commands/digest.py 文件句柄未关闭 | 改用 `with open()` |
| M5 | .gitignore 缺 `.lingflow/`、`.benchmarks/` | 补充 |

### 🟢 轻微（5）

| # | 问题 | 修复建议 |
|:-:|------|---------|
| L1 | schedule.py 301行（超限1行） | 可接受，继续增长时拆分 |
| L2 | commands/chat.py 未使用的 `import sys` | 删除 |
| L3 | 无 git tags | 补打 v0.13.0 tag |
| L4 | PRD.md 版本号过时 | 更新 |
| L5 | commands/schedule.py 重复 import | 清理 |

---

## 八、改进建议路线

### 立即修复（本轮）

1. **S1** — ask.py 添加医疗查询护栏
2. **S2** — 更新 AGENTS.md 至 v0.13
3. **S3** — 更新 README.md 至 v0.13
4. **M5** — 补充 .gitignore
5. **L2/L5** — 清理无用代码

### 下一版本（v0.14）

6. **M1** — 匿名化 test_presets.json
7. **M3** — 添加 db.py 直接测试
8. **M4** — 修复文件句柄问题
9. **L3** — 补打 git tag

### 评估后决定

10. **M2** — docs/ 脱敏（取决于仓库是否公开）
11. **L4** — PRD.md 更新（取决于是否继续维护此文档）

---

## 九、宪章核心价值观再对齐

```
守界 ── 惜时 ── 节约 ── 知己 ── 可靠
  │      │      │      │      │
  ⚠️     ✅     ✅     ✅     ✅
  │
  └─→ ask.py 医疗查询护栏是唯一的守界缺口
       修复后五个价值观全部达标
```

---

*审计完成。灵依 v0.13 项目整体健康，渐进交付节奏良好，代码质量符合私我工具定位。核心改进点：ask.py 边界护栏 + 文档同步更新。*
