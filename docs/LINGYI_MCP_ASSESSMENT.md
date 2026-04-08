# 灵依 LingYi — 功能与工具清单 + MCP 封装评估

> **日期**: 2026-04-07  
> **版本**: v0.16.0  
> **审计范围**: src/lingyi/ 全部 24 个模块

---

## 一、总览

| 指标 | 数值 |
|------|------|
| 功能模块 | 24 |
| 公开函数 | ~135 |
| 已有 MCP 工具 | 12 |
| Web Agent 工具 (tools.py) | 33 |
| REST API 端点 (web_app.py) | 39 |
| Stub / 死代码 | **0** — 全部真实代码 |

---

## 二、已有 12 个 MCP 工具（全部真实可用）

| # | 工具名 | 映射函数 | 功能 | 状态 |
|---|--------|---------|------|------|
| 1 | `add_memo` | memo.add_memo | 添加备忘 | ✅ |
| 2 | `list_memos` | memo.list_memos | 列出备忘 | ✅ |
| 3 | `add_schedule` | schedule.add_schedule | 添加日程 | ✅ |
| 4 | `list_schedules` | schedule.list_schedules | 列出日程 | ✅ |
| 5 | `add_plan` | plan.add_plan | 添加计划 | ✅ |
| 6 | `list_plans` | plan.list_plans | 列出计划 | ✅ |
| 7 | `show_project` | project.show_project | 查看项目 | ✅ |
| 8 | `generate_report` | report.generate_weekly_report | 生成周报 | ✅ |
| 9 | `patrol_project` | patrol.generate_report | 巡逻项目 | ✅ |
| 10 | `get_briefing` | briefing.collect_all + format | 获取情报简报 | ✅ |
| 11 | `digest_content` | digest.digest_text | 消化内容 | ✅ |
| 12 | `ask_lingzhi` | ask.ask_knowledge | 询问灵知 | ✅ |

**MCP 入口**: `src/lingyi/mcp_server.py`，协议 stdio (FastMCP)

---

## 三、未封装的公开函数（按模块）

### 3.1 memo.py — 2 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `show_memo(memo_id)` | `(int) -> Memo \| None` | 查看单条备忘 | 中 | ✅ 简单 |
| `delete_memo(memo_id)` | `(int) -> bool` | 删除备忘 | 中 | ✅ 简单 |

### 3.2 schedule.py — 15 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `today_schedules()` | `() -> list[Schedule]` | 今日日程 | **高** | ✅ 简单 |
| `week_schedules()` | `() -> dict` | 本周日程 | **高** | ✅ 简单 |
| `show_schedule(id)` | `(int) -> Schedule \| None` | 查看单条日程 | 中 | ✅ 简单 |
| `update_schedule(id, **kw)` | `(int, ...) -> Schedule \| None` | 更新日程 | 中 | ✅ 简单 |
| `cancel_schedule(id)` | `(int) -> bool` | 取消日程 | 中 | ✅ 简单 |
| `smart_remind()` | `() -> str` | 智能提醒（日程+偏好+会话） | **高** | ✅ 简单 |
| `check_remind()` | `() -> list` | 门诊提醒 | 低 | ✅ 简单 |
| `check_practice_remind()` | `() -> list` | 练功提醒 | 低 | ✅ 简单 |
| `check_journal_remind()` | `() -> list` | 期刊提醒 | 低 | ✅ 简单 |
| `check_tomorrow_ask()` | `() -> list` | 明日问诊提醒 | 低 | ✅ 简单 |
| `init_clinic()` | `() -> list` | 初始化门诊日程预设 | 低 | ✅ 简单 |
| `init_ask()` | `() -> list` | 初始化问诊日程预设 | 低 | ✅ 简单 |
| `init_practice()` | `() -> list` | 初始化练功日程预设 | 低 | ✅ 简单 |
| `init_journal()` | `() -> list` | 初始化期刊日程预设 | 低 | ✅ 简单 |
| `format_today()` | `() -> str` | 格式化今日日程文本 | 低 | ✅ 简单 |

### 3.3 project.py — 6 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `list_projects(status, category)` | `(str?, str?) -> list` | 列出项目（可筛选） | **高** | ✅ 简单 |
| `add_project(name, alias, ...)` | `(str, ...) -> Project` | 新建项目 | 中 | ✅ 简单 |
| `update_project(name_or_alias, **kw)` | `(str, ...) -> Project?` | 更新项目 | 中 | ✅ 简单 |
| `format_project_kanban(projects?)` | `(list?) -> str` | 看板视图 | 中 | ✅ 简单 |
| `init_projects()` | `() -> list` | 初始化项目预设 | 低 | ✅ 简单 |
| `format_project_detail(p)` | `(Project) -> str` | 项目详情卡片 | 低 | ✅ 简单 |

### 3.4 plan.py — 9 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `show_plan(plan_id)` | `(int) -> Plan?` | 查看单条计划 | 低 | ✅ 简单 |
| `done_plan(plan_id)` | `(int) -> Plan?` | 完成计划 | **高** | ✅ 简单 |
| `cancel_plan(plan_id)` | `(int) -> bool` | 取消计划 | 中 | ✅ 简单 |
| `week_plans()` | `() -> list` | 本周待办 | **高** | ✅ 简单 |
| `plan_stats()` | `() -> dict` | 计划统计（按领域/状态） | **高** | ✅ 简单 |
| `format_plan_week()` | `() -> str` | 格式化周计划 | 低 | ✅ 简单 |
| `format_plan_stats()` | `() -> str` | 格式化统计 | 低 | ✅ 简单 |

### 3.5 session.py — 7 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `save_session(summary, files, ...)` | `(str, ...) -> Session` | 保存会话摘要 | **高** | ✅ 简单 |
| `last_session()` | `() -> Session?` | 最近一次会话 | **高** | ✅ 简单 |
| `list_sessions(limit)` | `(int) -> list` | 列出历史会话 | 中 | ✅ 简单 |
| `get_session(id)` | `(int) -> Session?` | 获取指定会话 | 低 | ✅ 简单 |
| `delete_session(id)` | `(int) -> bool` | 删除会话 | 低 | ✅ 简单 |
| `format_session_resume(s)` | `(Session) -> str` | 会话恢复上下文 | 中 | ✅ 简单 |

### 3.6 pref.py — 4 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `set_pref(key, value)` | `(str, str) -> None` | 设置偏好 | 中 | ✅ 简单 |
| `get_pref(key)` | `(str) -> str?` | 获取偏好 | 中 | ✅ 简单 |
| `list_prefs()` | `() -> list` | 列出所有偏好 | 中 | ✅ 简单 |
| `delete_pref(key)` | `(str) -> bool` | 删除偏好 | 低 | ✅ 简单 |

### 3.7 ask.py — 3 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `search_knowledge(query, category, top_k)` | `(str, str?, int) -> dict` | 搜索灵知知识库 | **高** | ✅ 简单 |
| `get_categories()` | `() -> dict` | 获取灵知分类 | 中 | ✅ 简单 |
| `check_lingzhi()` | `() -> dict` | 灵知健康检查 | 低 | ✅ 简单 |

### 3.8 briefing.py — 4 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `collect_lingzhi()` | `() -> dict` | 采集灵知情报 | 低 | ✅ 简单 |
| `collect_lingflow()` | `() -> dict` | 采集灵通情报 | 低 | ✅ 简单 |
| `collect_lingclaude()` | `() -> dict` | 采集灵克情报 | 低 | ✅ 简单 |
| `collect_lingtongask()` | `() -> dict` | 采集灵通问通道报 | 低 | ✅ 简单 |

### 3.9 digest.py — 2 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `save_digest(data)` | `(dict) -> dict` | 保存消化结果到备忘/偏好 | 中 | ✅ 简单 |
| `format_digest(data)` | `(dict) -> str` | 格式化消化结果 | 低 | ✅ 简单 |

### 3.10 tts.py — 2 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `speak(text, voice)` | `(str, str) -> bool` | 语音播报 | **高** | ⚠️ 依赖 ffplay |
| `synthesize_to_file(text, path, voice)` | `(str, str, str) -> str` | 语音合成到文件 | **高** | ✅ 简单 |

### 3.11 stt.py — 3 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `transcribe_file(audio_path, backend)` | `(str, str?) -> dict` | 语音转文字 | **高** | ⚠️ 依赖 whisper |
| `record_audio(duration, path)` | `(int, str?) -> str?` | 录音 | 中 | ⚠️ 依赖 arecord |
| `check_stt()` | `() -> dict` | STT 后端状态 | 低 | ✅ 简单 |

### 3.12 council.py — 4 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `council_scan()` | `() -> dict` | 扫描讨论、唤醒成员 | **高** | ✅ 简单 |
| `council_status()` | `() -> dict` | 议事厅守护状态 | 中 | ✅ 简单 |
| `council_health()` | `() -> dict` | 议事厅健康检查 | 中 | ✅ 简单 |
| `wake_member(member_id, disc_id)` | `(str, str) -> str?` | 唤醒指定成员 | 中 | ✅ 简单 |

### 3.13 lingmessage.py — 12 个未封装（设计见 LINGMESSAGE_MCP_DESIGN.md）

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `send_message(from_id, topic, content, ...)` | `(str, str, str, ...) -> Message` | 发送灵信 | **高** | ✅ 简单 |
| `list_discussions(status)` | `(str?) -> list` | 列出讨论 | **高** | ✅ 简单 |
| `read_discussion(disc_id)` | `(str) -> dict?` | 读取讨论 | **高** | ✅ 简单 |
| `reply_to_discussion(disc_id, from_id, content, ...)` | `(str, str, str, ...) -> Message?` | 回复讨论 | **高** | ✅ 简单 |
| `close_discussion(disc_id)` | `(str) -> bool` | 关闭讨论 | 中 | ✅ 简单 |
| `search_messages(keyword)` | `(str) -> list` | 搜索消息 | **高** | ✅ 简单 |
| `annotate_discussion(disc_id)` | `(str) -> dict` | 自动标注 | 中 | ✅ 简单 |
| `detect_temporal_anomalies(disc, threshold)` | `(dict, float) -> list` | 异常检测 | 中 | ✅ 简单 |
| `init_store()` | `() -> dict` | 初始化存储 | 低 | ✅ 简单 |
| `format_discussion_list(discs)` | `(list) -> str` | 格式化列表 | 低 | ✅ 简单 |
| `format_discussion_thread(disc)` | `(dict) -> str` | 格式化线程 | 低 | ✅ 简单 |
| `format_message(msg)` | `(Message) -> str` | 格式化消息 | 低 | ✅ 简单 |

### 3.14 trends.py — 4 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `TrendAnalyzer.analyze_weekly()` | `() -> ComparisonReport` | 周趋势分析 | **高** | ✅ 简单 |
| `TrendAnalyzer.analyze_monthly()` | `() -> ComparisonReport` | 月趋势分析 | **高** | ✅ 简单 |
| `TrendAnalyzer.detect_anomalies(threshold)` | `(float) -> list` | 异常检测 | 中 | ✅ 简单 |
| `format_trend_summary(report)` | `(ComparisonReport) -> str` | 格式化趋势摘要 | 低 | ✅ 简单 |

### 3.15 llm_utils.py — 5 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `get_model_status()` | `() -> dict` | 模型可用性/配额 | 中 | ✅ 简单 |
| `get_usage_stats()` | `() -> dict` | Token 使用统计 | 中 | ✅ 简单 |
| `probe_premium_models()` | `() -> dict` | 探测高级模型 | 低 | ✅ 简单 |
| `call_llm_with_fallback(...)` | `(...) -> Any` | 带降级的 LLM 调用 | 低（内部函数） | ❌ 不适合 |
| `create_client()` | `() -> Any` | 创建客户端 | 低（内部函数） | ❌ 不适合 |

### 3.16 agent.py — 1 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `process_message(text, conversation)` | `(str, list) -> str` | 主 Agent 入口 | 低（内部循环） | ❌ 不适合独立封装 |

### 3.17 bridge_client.py — 2 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `connect_to_bridge(on_chat)` | `async (callable)` | 连接智桥 | 低（长期连接） | ❌ 不适合 |
| `bridge_push(ws, text, category)` | `async (ws, str, str)` | 通过智桥推送 | 低（依赖 ws） | ❌ 不适合 |

### 3.18 mobile.py — 4 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `detect_environment()` | `() -> dict` | 环境检测 | 低 | ✅ 简单 |
| `play_audio(file_path, player)` | `(str, str?) -> bool` | 播放音频 | 低 | ⚠️ 依赖播放器 |

### 3.19 dashboard.py — 2 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `generate_dashboard(data)` | `(dict?) -> str` | 生成 HTML 仪表盘 | 中 | ✅ 简单 |
| `save_dashboard(path)` | `(Path?) -> Path` | 保存仪表盘到文件 | 中 | ✅ 简单 |

### 3.20 patrol.py — 1 个未封装

| 函数 | 签名 | 功能 | MCP 必要性 | 可行性 |
|------|------|------|-----------|--------|
| `check_project(name, path)` | `(str, str) -> dict` | 单项目检查 | 中 | ✅ 简单 |

### 3.21 不适合封装的模块

| 模块 | 原因 |
|------|------|
| `config.py` | 配置加载，纯内部 |
| `db.py` | 数据库连接，纯内部 |
| `models.py` | 数据类定义，纯内部 |
| `tools.py` | 已有 33 个工具注册给 Web Agent，与 MCP 不同路径 |

---

## 四、MCP 封装优先级评估

### P0 — 核心缺失（强烈建议封装）

| # | 候选工具 | 来源函数 | 理由 |
|---|---------|---------|------|
| 1 | `today_schedule` | schedule.today_schedules | 最常用功能，MCP 外部访问必需 |
| 2 | `week_schedule` | schedule.week_schedules | 周视图 |
| 3 | `smart_remind` | schedule.smart_remind | 智能提醒是核心差异化功能 |
| 4 | `done_plan` | plan.done_plan | 任务完成闭环 |
| 5 | `week_plans` | plan.week_plans | 本周待办 |
| 6 | `plan_stats` | plan.plan_stats | 五域进度统计 |
| 7 | `list_projects` | project.list_projects | 项目列表（带筛选） |
| 8 | `save_session` | session.save_session | 会话记忆是核心 |
| 9 | `last_session` | session.last_session | 上下文恢复 |
| 10 | `search_knowledge` | ask.search_knowledge | 灵知搜索（比 ask 更灵活） |
| 11 | `speak` | tts.speak | 语音播报 |
| 12 | `synthesize_to_file` | tts.synthesize_to_file | TTS 合成 |
| 13 | `transcribe` | stt.transcribe_file | 语音识别 |
| 14 | `council_scan` | council.council_scan | 议事厅扫描 |
| 15 | `analyze_trends` | trends.analyze_weekly/monthly | 趋势分析 |

### P1 — 补充能力（建议封装）

| # | 候选工具 | 来源函数 | 理由 |
|---|---------|---------|------|
| 16 | `show_memo` | memo.show_memo | 查看单条 |
| 17 | `delete_memo` | memo.delete_memo | 删除 |
| 18 | `update_schedule` | schedule.update_schedule | 修改日程 |
| 19 | `add_project` | project.add_project | 新建项目 |
| 20 | `update_project` | project.update_project | 更新项目 |
| 21 | `cancel_plan` | plan.cancel_plan | 取消计划 |
| 22 | `set_pref` | pref.set_pref | 设置偏好 |
| 23 | `get_pref` | pref.get_pref | 读取偏好 |
| 24 | `list_prefs` | pref.list_prefs | 所有偏好 |
| 25 | `list_sessions` | session.list_sessions | 历史会话 |
| 26 | `council_health` | council.council_health | 议事厅健康 |
| 27 | `generate_dashboard` | dashboard.generate_dashboard | 仪表盘 |
| 28 | `check_project` | patrol.check_project | 单项目检查 |
| 29 | `get_model_status` | llm_utils.get_model_status | 模型状态 |

### P2 — 低优先级

| 候选工具 | 理由 |
|---------|------|
| `check_remind`, `check_practice_remind`, `check_journal_remind`, `check_tomorrow_ask` | 场景窄，被 smart_remind 覆盖 |
| `init_clinic/ask/practice/journal` | 一次性初始化操作 |
| `format_*` 系列 | 纯格式化，MCP 返回结构化数据不需要 |
| `detect_environment`, `play_audio` | 移动端特化，MCP 场景不需要 |
| `bridge_client.*` | 异步长连接，不适合 MCP |

---

## 五、tools.py 与 MCP 的关系

灵依有**两套工具注册系统**：

| 系统 | 入口 | 工具数 | 服务对象 |
|------|------|--------|---------|
| **MCP Server** | mcp_server.py | 12 | 外部 Agent（Claude/Cursor/LingFlow+） |
| **Web Agent Tools** | tools.py | 33 | 内部 LLM function calling（web_app /ws/chat） |

两套有重叠但不同：

| 功能 | MCP | tools.py |
|------|-----|---------|
| 备忘 CRUD | add/list | add/list/delete |
| 日程 | add/list | today/week/add |
| 计划 | add/list | add/list/done |
| 项目 | show | list/show |
| 灵信 | ❌ | list/send/read |
| 偏好 | ❌ | list/set |
| 会话 | ❌ | last |
| 语音 | ❌ | ❌ |
| 外部查询 | ❌ | ai_news/check_github/check_pypi/search_web |
| UI 操作 | ❌ | ui_capture/ui_ocr/ui_find/ui_analyze/ui_status |
| 文件 | ❌ | file_read |
| Git | ❌ | git_status |
| 代码统计 | ❌ | code_stats |

**建议**: MCP server 应向 tools.py 的覆盖面看齐，将高价值函数逐步补齐。

---

## 六、MCP 封装工作量估算

| 优先级 | 工具数 | 每个行数 | 总工作量 |
|--------|--------|---------|---------|
| P0 | 15 | 15-25 行 | 1-2 天 |
| P1 | 14 | 10-20 行 | 1 天 |
| P2 | ~15 | 10 行 | 0.5 天 |
| **合计** | **~44** | | **2.5-3.5 天** |

封装后灵依 MCP 工具总数：12（现有）+ 44（新增）- 若干合并 = **~50 个**。

---

## 七、总结

灵依是灵字辈中**最健康**的项目：

- **0 死代码**，24 个模块全部真实可用
- 已有 12 个 MCP 工具 + 33 个 Web Agent 工具，两套系统互补
- 约 44 个函数有 MCP 封装价值，工作量约 3 天
- 最大缺口：灵信（12 函数 0 封装）、语音（TTS/STT 0 封装）、趋势分析（0 封装）

灵依对 LingFlow+ 的价值：
- 个人管理（备忘/日程/计划/偏好）→ 唯一来源
- 情报汇总（briefing/patrol/report）→ 唯一来源
- 跨项目通信（lingmessage/council）→ 主要入口
- 语音 I/O（TTS/STT）→ 两个提供商之一
