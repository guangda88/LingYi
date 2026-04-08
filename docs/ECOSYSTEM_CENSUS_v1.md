# 灵字辈生态普查报告 v1

> **普查日期**: 2026-04-07  
> **范围**: 灵字辈大家庭全部 11 个项目  
> **重点**: MCP 工具、可封装为 MCP 的功能、死代码/未使用代码

---

## 一、总览

| 指标 | 数值 |
|------|------|
| 项目总数 | 11 |
| 自研 MCP 工具 | **53** |
| 可封装为 MCP 的 REST API / 功能 | **30+** |
| 外部 SaaS 工具（智谱，非自研） | 11 |
| 源代码总量（自研） | ~195,000 行 |
| 测试代码总量 | ~50,000 行 |
| 完全死代码（stub） | 灵通 22 个 skill 为文档驱动 stub |
| 从未使用过的功能模块 | 灵克 15 个模块无测试覆盖 |

---

## 二、项目清单

| # | 项目 | 灵 | 语言 | 源码行数 | 测试行数 | MCP 工具 | 版本 | 状态 |
|---|------|-----|------|---------|---------|---------|------|------|
| 1 | **LingFlow** | 灵通 | Python | 49,205 | 41,679 + 9,094 (skills) | **21** | v3.9.1 | 活跃，已发布 PyPI |
| 2 | **LingClaude** | 灵克 | Python | 12,446 | 5,771 | **15** | v0.3.0 | 活跃 |
| 3 | **LingYi** | 灵依 | Python | 10,352 | 2,749 | **12** | v0.16.0 | 活跃 |
| 4 | **Ling-term-mcp** | 灵犀 | TypeScript | 1,357 | — | **5** | v1.0 | 已发布 npm |
| 5 | **zhineng-knowledge-system** | 灵知 | Python | 8,455 | — | ⚠️ 0 (25+ REST API) | 生产部署 | 活跃 |
| 6 | **zhineng-bridge** | 智桥 | Python+TS+JS | 77,965 | — | ⚠️ 0 (stub) | v1.0 | 活跃 |
| 7 | **LingMinOpt** | 灵极优 | Python | 4,014 | — | ❌ | v0.2 | 活跃 |
| 8 | **LingMessage** | 灵信 | Python | 微量 | — | ❌ | v1.0 | 79 讨论活跃 |
| 9 | **LingYang** | 灵扬 | Python | 极少 | — | ❌ | v0.1 | 最小化 |
| 10 | **lingresearch** | 灵研 | Python | 小型 | — | ❌ | — | 活跃 |
| 11 | **lingtongask** | 灵通问道 | Python | 中型 | — | ❌ | — | 30+ 期已发布 |

---

## 三、MCP 工具详细清单（53 个自研）

### 3.1 灵通 LingFlow — 21 个 MCP 工具

| # | 工具名 | 功能 | 重量级 | 实际使用 |
|---|--------|------|--------|---------|
| 1 | `list_skills` | 列出所有可用技能 | ✅ | ✅ |
| 2 | `run_skill` | 执行指定技能 | ✅ | ⚠️ 部分 skill 为 stub |
| 3 | `review_code` | 代码审查 | ✅ | ✅ |
| 4 | `get_github_trends` | GitHub 趋势分析 | ✅ | ✅ |
| 5 | `get_npm_trends` | NPM 趋势分析 | ✅ | ✅ |
| 6 | `list_workflows` | 列出工作流 | ✅ | ✅ |
| 7 | `run_workflow` | 执行工作流 | ✅ | ✅ |
| 8 | `get_workflow` | 获取工作流详情 | ✅ | ✅ |
| 9 | `create_requirement` | 创建需求 | ✅ | ✅ |
| 10 | `update_requirement` | 更新需求 | ✅ | ✅ |
| 11 | `delete_requirement` | 删除需求 | ✅ | ✅ |
| 12 | `list_requirements` | 列出需求 | ✅ | ✅ |
| 13 | `run_tests` | 运行测试 | ✅ | ✅ |
| 14 | `get_coverage` | 获取覆盖率 | ✅ | ✅ |
| 15 | `generate_test_report` | 生成测试报告 | ✅ | ✅ |
| 16 | `get_health_status` | 健康状态检查 | ✅ | ✅ |
| 17 | `get_metrics` | 获取度量数据 | ✅ | ✅ |
| 18 | `detect_anomaly` | 异常检测 | ✅ | ✅ |
| 19 | `get_task_status` | 获取任务状态 | ✅ | ✅ |
| 20 | `list_tasks` | 列出任务 | ✅ | ✅ |
| 21 | `create_task` | 创建任务 | ✅ | ✅ |

**MCP 入口**: `/home/ai/LingFlow/mcp_server/lingflow_mcp/`  
**协议**: stdio (FastMCP)  
**外部路由**: `ExternalMCPRouter` 支持发现和代理外部 MCP 工具

### 3.2 灵克 LingClaude — 15 个 MCP 工具

| # | 工具名 | 功能 | 重量级 | 实际使用 |
|---|--------|------|--------|---------|
| 1 | `read_file` | 读取文件内容 | ✅ | ✅ |
| 2 | `write_file` | 写入文件 | ✅ | ✅ |
| 3 | `edit_code` | 编辑代码（AST 感知） | ✅ | ✅ |
| 4 | `search_code` | 搜索代码 | ✅ | ✅ |
| 5 | `run_bash` | 执行 Bash 命令 | ✅ | ✅ |
| 6 | `index_project` | 索引项目结构 | ✅ | ✅ |
| 7 | `list_functions` | 列出函数 | ✅ | ✅ |
| 8 | `replace_function` | 替换函数体 | ✅ | ✅ |
| 9 | `git_status` | Git 状态 | ✅ | ✅ |
| 10 | `git_log` | Git 日志 | ✅ | ✅ |
| 11 | `git_diff` | Git 差异 | ✅ | ✅ |
| 12 | `evaluate_code` | 代码评估 | ✅ | ✅ |
| 13 | `run_optimization` | 运行优化 | ✅ | ⚠️ 依赖 self._config bug |
| 14 | `get_advice` | 获取建议 | ✅ | ✅ |
| 15 | `check_triggers` | 检查触发器 | ✅ | ✅ |

**MCP 入口**: `/home/ai/LingClaude/lingclaude/mcp/server.py`  
**协议**: stdio (FastMCP)

### 3.3 灵依 LingYi — 12 个 MCP 工具

| # | 工具名 | 功能 | 重量级 | 实际使用 |
|---|--------|------|--------|---------|
| 1 | `add_memo` | 添加备忘 | ✅ | ✅ |
| 2 | `list_memos` | 列出备忘 | ✅ | ✅ |
| 3 | `add_schedule` | 添加日程 | ✅ | ✅ |
| 4 | `list_schedules` | 列出日程 | ✅ | ✅ |
| 5 | `add_plan` | 添加计划 | ✅ | ✅ |
| 6 | `list_plans` | 列出计划 | ✅ | ✅ |
| 7 | `show_project` | 查看项目 | ✅ | ✅ |
| 8 | `generate_report` | 生成周报 | ✅ | ✅ |
| 9 | `patrol_project` | 巆逻项目 | ✅ | ✅ |
| 10 | `get_briefing` | 获取情报简报 | ✅ | ✅ |
| 11 | `digest_content` | 消化内容 | ✅ | ✅ |
| 12 | `ask_lingzhi` | 询问灵知 | ✅ | ✅ |

**MCP 入口**: `/home/ai/LingYi/src/lingyi/mcp_server.py`  
**协议**: stdio (FastMCP)

### 3.4 灵犀 Ling-term-mcp — 5 个 MCP 工具

| # | 工具名 | 功能 | 重量级 | 实际使用 |
|---|--------|------|--------|---------|
| 1 | `execute_command` | 执行终端命令 | ✅ | ✅ |
| 2 | `create_session` | 创建终端会话 | ✅ | ✅ |
| 3 | `destroy_session` | 销毁终端会话 | ✅ | ✅ |
| 4 | `list_sessions` | 列出会话 | ✅ | ✅ |
| 5 | `sync_terminal` | 同步终端状态 | ✅ | ✅ |

**MCP 入口**: `/home/ai/Ling-term-mcp/src/index.ts`  
**协议**: stdio (npm 发布)

---

## 四、可封装为 MCP 的功能（30+ 候选）

### 4.1 灵知 zhineng-knowledge-system — 25+ REST API

灵知有完整的 FastAPI 服务（端口 8000），**零 MCP 工具**，但 REST API 极其丰富。封装成本极低 — 只需一层 MCP wrapper 调用已有的 REST 端点。

| # | API 路径前缀 | 功能领域 | 封装难度 | 优先级 |
|---|-------------|---------|---------|--------|
| 1 | `/search` | 知识搜索 | 低 | P0 |
| 2 | `/books` | 书籍管理 | 低 | P1 |
| 3 | `/guoxue` | 国学经典 | 低 | P1 |
| 4 | `/sysbooks` | 系统书籍 | 低 | P2 |
| 5 | `/reasoning` | 推理引擎 | 低 | P0 |
| 6 | `/audio` | 音频处理 | 中 | P1 |
| 7 | `/generation` | 内容生成 | 低 | P1 |
| 8 | `/intelligence` | 智能分析 | 低 | P0 |
| 9 | `/learning` | 学习系统 | 中 | P1 |
| 10 | `/evolution` | 知识进化 | 中 | P2 |
| 11 | `/optimization` | 优化系统 | 中 | P2 |
| 12 | `/context` | 上下文管理 | 低 | P1 |
| 13 | `/annotation` | 标注系统 | 低 | P1 |
| 14 | `/pipeline` | 管道处理 | 中 | P1 |
| 15 | `/lingmessage` | 跨项目讨论 | 低 | P0 |
| 16 | `/knowledge_gaps` | 知识缺口检测 | 低 | P1 |
| 17 | `/feedback` | 反馈系统 | 低 | P2 |
| 18 | `/staging` | 暂存区 | 低 | P2 |
| 19 | `/analytics` | 分析统计 | 低 | P1 |
| 20 | `/documents` | 文档管理 | 低 | P1 |
| 21 | `/health` | 健康检查 | 低 | P2 |
| 22 | `/textbook_processing` | 教材处理 | 中 | P1 |

**封装方案**: 新建 `zhineng-knowledge-system/mcp_server/`，用 FastMCP 包装 REST 调用。预计每个工具 20-30 行代码，总工作量约 2-3 天。

### 4.2 智桥 zhineng-bridge — 丰富 API，MCP 为 stub

智桥有 77,965 行代码（含 Web UI），已有 MCP server 目录但是 **空壳 stub**。核心功能是跨项目消息中继（端口 8080），已有成熟的 REST API。

**可封装功能**:
- 消息中继 API → MCP 工具
- 跨项目通信接口 → MCP 工具
- Web Dashboard 数据接口 → MCP 工具

### 4.3 灵信 LingMessage — 文件式通信，极易封装

灵信使用纯文件系统存储（`/home/ai/.lingmessage/discussions/`），79 个活跃讨论。当前只被灵依 CLI 调用。

**可封装功能**:
- `send_message()` → MCP 工具
- `list_discussions()` → MCP 工具
- `read_discussion()` → MCP 工具
- `reply_message()` → MCP 工具
- `search_messages()` → MCP 工具
- `close_discussion()` → MCP 工具

**封装成本**: 极低，每个工具 10-15 行 Python，1 天可完成。

### 4.4 灵极优 LingMinOpt — 优化库 + CLI

4,014 行优化算法库，支持多种优化方法。

**可封装功能**:
- `optimize()` → MCP 工具（运行优化）
- `get_results()` → MCP 工具（获取结果）
- `list_methods()` → MCP 工具（列出方法）

---

## 五、重量开发 vs 未使用代码评估

### 5.1 灵通 LingFlow — 核心问题项目

灵通是最大的项目（103K 行），但存在严重的**「文档驱动 stub」**问题。

#### Skill 实际功能分层

| 层级 | 数量 | 说明 | 实际可用 |
|------|------|------|---------|
| **Tier 1 — 完整功能** | 5 | code-review, conditional-branch, task-runner, test-runner, code-refactor（但 refactor_file()=pass） | ✅ 大部分可用 |
| **Tier 2 — 部分功能** | 5 | workflow-executor, error-handler, loop-iterator, database-export, notification | ⚠️ 不完整 |
| **Tier 3 — 文档驱动 stub** | 22 | brainstorming, writing-plans, subagent-driven-development, systematic-debugging, TDD, verification, git-worktrees, finishing-branch, dispatching-parallel-agents, ui-mockup-generator, api-doc-generator, ci-cd-orchestrator, environment-manager, deployment-automation, database-schema-designer, skill-versioning/templates/testing/analytics/categorization/creator/integration | ❌ 只有 SKILL.md，implementation.py ≈ 40 行模板 |

**具体 stub 模式**（以 brainstorming 为例）:

```python
# implementation.py 的典型结构
class BrainstormingSkill:
    def execute(self, params):
        return {
            "status": "success",
            "instructions": "请参考 SKILL.md 中的流程...",  # AI 读取文档
            "data": {}
        }
```

这不是 bug — 是灵通的设计理念（AI 读取 SKILL.md 来执行）。但从**代码执行**角度看，这 22 个 skill 没有真正的 Python 实现逻辑。

#### 其他死代码 / Stub

| 位置 | 问题 | 严重程度 |
|------|------|---------|
| `Agent.execute_task()` | 整个方法只是 `time.sleep(0.05)` + 返回假数据 | **严重** — 核心功能是空壳 |
| `code_refactor.refactor_file()` | 函数体是 `pass` | 高 |
| `phase5/ai_tool_learning.py` | `AIToolLearningSystem` 类被注释，标注「待实现」 | 中 |
| 33 个 skill 中 22 个是 stub | 占比 67% | 架构级问题 |

### 5.2 灵克 LingClaude — 功能完整但有覆盖盲区

灵克是**代码质量最高**的项目 — 48 个模块全部有真实实现，0 个 stub。

#### 无测试覆盖的模块（15 个）

| 模块 | 功能 | 风险等级 |
|------|------|---------|
| `bash.py` | Bash 命令执行 | 🔴 安全关键 |
| `permissions.py` | 权限管理 | 🔴 安全关键 |
| `behavior_aware_router.py` | 行为感知路由 | 🟡 有 bug（self._config） |
| `task_aggregation.py` | 任务聚合 | 🟡 与 task_scheduler 枚举重复 |
| `task_scheduler.py` | 任务调度 | 🟡 重复枚举定义 |
| 其他 10 个模块 | 各种辅助功能 | 🟢 低风险 |

#### 已知 Bug

- `behavior_aware_router.py`: `self._config` vs `self.config` 属性名不一致
- `task_aggregation.py` + `task_scheduler.py`: `TaskPriority`/`TaskStatus` 枚举重复定义

### 5.3 灵依 LingYi — 最健康的项目

36 个模块全部有真实实现，0 stub。39 个测试类，200+ 测试方法，2315 行测试代码。

#### 无测试覆盖的模块（7 个）

| 模块 | 功能 | 说明 |
|------|------|------|
| `council.py` | 跨项目议事 | 新功能 |
| `bridge_client.py` | 智桥客户端 | 新功能 |
| `web_app.py` | Web 应用 | 41 个 API 端点 |
| `dashboard.py` | 仪表盘 | 前端组件 |
| `trends.py` | 趋势分析 | 新功能 |
| `agent.py` | LLM Agent | 核心模块 |
| `llm_utils.py` | LLM 工具 | 核心模块 |

### 5.4 其他项目

| 项目 | 评估 |
|------|------|
| 灵犀 | 5 个 MCP 工具全部可用，代码简洁 |
| 灵知 | 25+ REST API 全部生产可用，只是没 MCP wrapper |
| 智桥 | 大量代码但 MCP 是空壳 |
| 灵极优 | 小型优化库，功能完整 |
| 灵信 | 文件式存储，极简但实用，79 讨论活跃 |
| 灵扬 | 极早期，几乎无内容 |
| 灵研 | 小型，功能不详 |
| 灵通问道 | 内容项目（30+ 期），非工具 |

---

## 六、外部 SaaS 工具（非自研）

以下工具来自智谱 AI（`@z_ai/mcp-server`，open.bigmodel.cn），**不属于灵字辈自研**：

| # | 工具名 | 类型 | 来源 |
|---|--------|------|------|
| 1 | `analyze_image` | 图像分析 | 智谱 MCP |
| 2 | `analyze_video` | 视频分析 | 智谱 MCP |
| 3 | `analyze_data_visualization` | 数据可视化分析 | 智谱 MCP |
| 4 | `extract_text_from_screenshot` | OCR 文字提取 | 智谱 MCP |
| 5 | `diagnose_error_screenshot` | 错误截图诊断 | 智谱 MCP |
| 6 | `ui_to_artifact` | UI 截图转代码/描述 | 智谱 MCP |
| 7 | `ui_diff_check` | UI 对比检查 | 智谱 MCP |
| 8 | `understand_technical_diagram` | 技术图表理解 | 智谱 MCP |
| 9 | `web_search_prime` | 网页搜索 | 智谱 MCP |
| 10 | `web_reader` | 网页读取 | 智谱 MCP |
| 11 | `zread` (get_repo_structure, read_file, search_doc) | GitHub 仓库读取 | 智谱 MCP |

**首次出现**: 2026-03-24，配置于 `/home/ai/.claude/settings.json`  
**性质**: 第三方 SaaS 服务，按调用量计费  
**对 LingFlow+ 的启示**: 需要设计 `VisionProvider` 接口，支持可插拔后端（智谱/OpenAI Vision/本地 Qwen-VL）

---

## 七、代码统计汇总

### 7.1 按项目代码量排名

```
灵通 LingFlow      ████████████████████████████████████████  103,978 行 (53%)
智桥 zhineng-bridge ████████████████████████████████         77,965 行 (40%)
灵克 LingClaude     ██████                                   18,217 行 (9%)
灵依 LingYi        █████                                    13,101 行 (7%)
灵知 zhineng-ks    ████                                      8,455 行 (4%)
灵极优 LingMinOpt  ██                                         4,014 行 (2%)
灵犀 Ling-term-mcp  █                                         1,357 行 (1%)
灵信 LingMessage    ▏                                         微量
灵扬/灵研/灵通问道                                            极少~中型
```

> **注意**: 智桥 77,965 行中大部分是 Web UI（HTML/CSS/JS），核心 Python 逻辑约 3,000-5,000 行。

### 7.2 代码健康度评估

| 项目 | 功能代码占比 | Stub/死代码占比 | 测试覆盖 | 健康度 |
|------|-------------|----------------|---------|--------|
| 灵克 | 100% | 0% | 69% (33/48) | 🟢 优秀 |
| 灵依 | 100% | 0% | 81% (29/36) | 🟢 优秀 |
| 灵犀 | 100% | 0% | 无 | 🟡 良好 |
| 灵知 | 100% | 0% | 无 | 🟡 良好 |
| 灵极优 | 100% | 0% | 无 | 🟡 良好 |
| 灵通 | 33% | **67% stub** | 有 | 🔴 需关注 |
| 智桥 | ~90% | MCP 为空壳 | 无 | 🟡 良好 |

### 7.3 MCP 工具分布

```
灵通 21 █████████████████████ (40%)
灵克 15 ███████████████       (28%)
灵依 12 ████████████          (23%)
灵犀  5 █████                 (9%)
─────────────────────────────
合计 53 个自研 MCP 工具
```

---

## 八、关键发现与建议

### 8.1 核心发现

1. **灵通虚胖严重** — 103K 行代码中，67% 的 skill 是文档驱动 stub，Agent 核心执行方法是空壳。MCP 工具层（21 个）是真实的，但底层 skill 执行大量依赖 AI 读取 SKILL.md。

2. **灵克是被低估的核心资产** — 48 个模块全部功能完整，15 个 MCP 工具（文件读写、代码编辑、Bash 执行、Git 操作），是最完整的「AI 编码引擎」。且有幻觉修正循环（`QueryEngine`）这种高级功能。

3. **灵知是最大的 MCP 空白** — 25+ REST API 生产可用，但零 MCP 工具。封装成本极低（每个 ~25 行），是 ROI 最高的 MCP 化候选。

4. **灵信极易 MCP 化** — 6 个纯文件操作函数，封装为 MCP 每个仅需 10-15 行，1 天可完成。

5. **外部工具依赖风险** — 11 个智谱 SaaS 工具（含 8 个视觉分析）被误认为自研。LingFlow+ 需要设计 Provider 抽象层。

### 8.2 优先行动建议

| 优先级 | 行动 | 预计工时 | ROI |
|--------|------|---------|-----|
| **P0** | 灵知 REST API → MCP 封装（22+ 工具） | 2-3 天 | 极高 |
| **P0** | 灵信 LingMessage → MCP 封装（6 工具） | 1 天 | 高 |
| **P1** | 灵通 stub 清理或明确标注 | 2 天 | 中 |
| **P1** | 灵克安全模块测试覆盖（bash.py, permissions.py） | 1 天 | 高 |
| **P2** | 智桥 MCP stub 实现或删除 | 2-3 天 | 中 |
| **P2** | 灵极优 → MCP 封装 | 0.5 天 | 低 |

### 8.3 对 LingFlow+ 的架构启示

```
可用资产:
├── 灵通: 编排引擎（并行调度、工作流、上下文压缩、安全沙箱）✅ 可直接复用
├── 灵通: MCP Server + ExternalMCPRouter               ✅ 可直接复用
├── 灵克: 15 个编码工具                                 ✅ 可直接复用
├── 灵克: QueryEngine（幻觉修正循环）                   ✅ 可直接复用
├── 灵克: Model Provider（OpenAI/Anthropic）            ✅ 可直接复用
├── 灵依: 12 个生活管理工具                              ✅ 可直接复用
├── 灵犀: 5 个终端工具                                  ✅ 可直接复用
├── 灵知: 25+ 知识 API（需 MCP 封装）                   ⚠️ 封装后可用
├── 灵信: 跨项目通信                                    ⚠️ 封装后可用
│
需要新建:
├── LLM Provider 抽象层（灵克已有基础）                  🆕 新建
├── 真实 Agent Runtime（替换灵通 stub）                  🆕 新建
└── Project Workspace + CLI REPL                        🆕 新建
```

**结论**: 灵字辈生态已有 **53 个自研 MCP 工具 + 30+ 可封装功能**，技术资产丰富。核心问题是灵通的 Agent 层是空壳。LingFlow+ 的核心工作是「给灵通的编排引擎装上灵克的大脑」+ 统一 Provider 抽象。

---

## 九、附录：项目路径

| 项目 | 路径 |
|------|------|
| 灵通 LingFlow | `/home/ai/LingFlow/` |
| 灵克 LingClaude | `/home/ai/LingClaude/` |
| 灵依 LingYi | `/home/ai/LingYi/` |
| 灵犀 Ling-term-mcp | `/home/ai/Ling-term-mcp/` |
| 灵知 zhineng-knowledge-system | `/home/ai/zhineng-knowledge-system/` |
| 智桥 zhineng-bridge | `/home/ai/zhineng-bridge/` |
| 灵极优 LingMinOpt | `/home/ai/LingMinOpt/` |
| 灵信 LingMessage | `/home/ai/.lingmessage/` |
| 灵扬 LingYang | `/home/ai/LingYang/` |
| 灵研 lingresearch | `/home/ai/lingresearch/` |
| 灵通问道 lingtongask | `/home/ai/lingtongask/` |