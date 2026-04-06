# 灵依 LingYi — 开发规划

> 遵循最小可用、渐进增强。每个版本做完就用，用了再定下一个版本。
> 灵依的进化像中医调养：不求一步到位，但求日日有功。

---

## 版本总览

```
v0.1 能跑      v0.2 日程      v0.3 项目      v0.4 计划      v0.5 记忆
  │              │              │              │              │
  ▼              ▼              ▼              ▼              ▼
CLI入口        门诊排班       项目看板       工作计划       跨会话记忆
SQLite基础     日程增删查     进度跟踪       任务管理       上下文压缩
备忘录         上诊提醒       状态统计       五大领域       偏好积累
灵通问道提醒    项目巡检

v0.6 语音      v0.7 智能      v0.8 连接      v0.9+ 按需
  │              │              │              │
  ▼              ▼              ▼              ▼
语音播报       智能提醒       灵知对接       编程辅助
--speak参数    周报生成       灵克对接       信息整理
语音对话模式   灵通集成                      双向语音对话
```

---

## v0.1 能跑 ✅ 已完成

**目标**：CLI能跑，数据库能存，备忘录能增删查。

**交付**：
```bash
lingyi memo add "今天开始灵依项目"
lingyi memo list
lingyi memo show 1
```

---

## v0.2 日程 ✅ 已完成

**目标**：门诊排班实际可用，每天能用上。

**交付**：
```bash
lingyi schedule init clinic       # 初始化门诊排班
lingyi schedule today             # 今日安排
lingyi schedule week              # 本周一览
lingyi schedule remind            # 检查提醒
lingyi patrol                     # 项目巡检
```

**实际排班**：周二至周四上下午，6个半天，4家医院。

---

## v0.3 项目（~4h）

**目标**：14个项目录入，状态可视化。

| 任务 | 产出 | 预计 |
|------|------|------|
| 项目模型 | projects表，active/maintenance/paused/archived | 45min |
| 项目导入 | 导入14个现有项目信息 | 2h |
| 项目看板 | `lingyi project list` 列表+状态 | 45min |
| 项目详情 | `lingyi project show <name>` 详情+优先级 | 30min |
| 测试 | 项目管理测试 | 30min |

**交付标准**：
```bash
lingyi project list                        # 所有项目看板
lingyi project show LingFlow               # 项目详情
lingyi project update 灵知 --status active --priority P1
lingyi project list --status active        # 活跃项目
```

---

## v0.4 计划（~3h）

**目标**：五大领域的工作都能规划跟踪。

| 任务 | 产出 | 预计 |
|------|------|------|
| 计划模型 | 五大领域分类（医疗/编程/研究/论文/学术） | 30min |
| 任务管理 | 添加/完成/取消任务 | 1h |
| 周计划与统计 | `lingyi plan week/stats` | 1h |
| 测试 | 计划管理测试 | 30min |

**交付标准**：
```bash
lingyi plan add "灵知系统安全加固" --area 编程 --project 灵知
lingyi plan add "撰写AI+中医论文大纲" --area 论文
lingyi plan week                    # 本周计划
lingyi plan done <id>               # 完成任务
lingyi plan stats                   # 完成率统计
```

---

## v0.5 记忆（~5h）⭐ 关键版本

**目标**：跨会话记忆，上下文压缩，不再断片。

> 豆包在长对话末尾断片的教训：重要信息不能依赖AI记忆，必须及时外化。
> 灵依要像脉诊一样——只带"脉象核心"，不带全部心跳。

| 任务 | 产出 | 预计 |
|------|------|------|
| 会话摘要 | 每轮对话结束自动生成结构化摘要 | 1.5h |
| 会话存储 | `~/.lingyi/sessions/` 下按日期存储 | 30min |
| 会话恢复 | `lingyi resume` 读入上轮摘要继续工作 | 1h |
| 偏好存储 | 用户习惯、编码风格、常用配置持久化到 SQLite | 1h |
| 测试 | 记忆系统测试 | 30min |

**交付标准**：
```bash
lingyi memo add "我偏好上午编程"      # 手动记录偏好
lingyi session save                  # 保存当前会话摘要
lingyi session last                  # 查看上次会话摘要
lingyi session resume                # 输出上次摘要，供AI读入
```

**会话摘要格式**：
```
## 会话 2026-04-03
- 完成了：v0.1 + v0.2
- 修改文件：cli.py, db.py, schedule.py, memo.py, models.py, patrol.py
- 关键决策：Click框架，SQLite at ~/.lingyi/
- 待办：v0.3 项目管理
- 用户偏好：极度节约token，直给答案
```

---

## v0.6 语音（~4h）

**目标**：语音播报 + 基础语音对话。

> 用户需求：像聊天一样对话，不用一直盯着屏幕。

| 任务 | 产出 | 预计 |
|------|------|------|
| edge-tts 集成 | `--speak` 参数，输出同时朗读 | 1h |
| 语音播报 | schedule/memo/remind 等命令支持朗读 | 1h |
| 语音对话模式 | `lingyi chat` 进入交互式语音对话 | 1.5h |
| 测试 | 语音功能测试 | 30min |

**交付标准**：
```bash
lingyi schedule today --speak        # 语音播报今日安排
lingyi memo list --speak             # 语音朗读备忘录
lingyi chat                          # 语音对话模式（STT + LLM + TTS）
```

**技术选型**：
- TTS: edge-tts（微软免费，中文晓晓/云希，质量好）
- STT: 后续版本接入（whisper 或 sherpa-onnx 本地方案）

---

## v0.7 智能（~4h）✅ 已完成

**目标**：基于记忆的智能功能。

| 任务 | 产出 | 预计 |
|------|------|------|
| 智能提醒 | 基于历史习惯的提醒建议 | 1.5h |
| 周报生成 | `lingyi report` 自动生成本周总结 | 1h |
| 灵通集成 | import lingflow，用其工作流能力 | 1h |
| 测试 | 集成测试 | 30min |

**交付标准**：
```bash
lingyi schedule remind                # 基于记忆给出建议
lingyi report                        # 本周总结
```

---

## v0.8 连接（~4h）✅ 已完成

**目标**：对接灵知和灵克，从独立工具变成生态一环。

| 任务 | 产出 | 预计 |
|------|------|------|
| 灵知对接 | 知识检索（REST API） | 1.5h |
| 灵克对接 | 编程辅助 | 1.5h |
| 测试 | 集成测试 | 1h |

**交付标准**：
```bash
lingyi ask "灵通的最新版本是多少"     # 查灵知
lingyi code "帮我检查patrol.py"       # 用灵克
```

---

## v0.9 信息整理 ✅ 已完成

**目标**：从外部对话/笔记中提取关键信息，自动整理为备忘录/偏好。

|| 任务 | 产出 | 预计 |
||------|------|------|
|| 文本解析 | 正则提取待办/决策/偏好/要点 | 1.5h |
|| 自动保存 | 提取结果保存到备忘录/偏好 | 30min |
|| CLI命令 | `lingyi digest` 支持文本/文件/管道 | 30min |
|| 测试 | 14个测试 | 30min |

**交付标准**：
```bash
lingyi digest "需要完成开发，决定用Python，偏好简洁风格"
lingyi digest --file conversation.txt
lingyi digest --save "需要整理的内容"
cat notes.txt | lingyi digest
```

---

## v0.10 编程辅助深化 ✅ 已完成

**目标**：扩展灵克能力，支持代码审查、依赖检查、重构建议。

|| 任务 | 产出 | 预计 |
||------|------|------|
|| 代码审查 | `review_code()` + `lingyi review` | 1h |
|| 依赖检查 | `check_dependencies()` + `lingyi deps` | 30min |
|| 重构建议 | `suggest_refactor()` + `lingyi refactor` | 30min |
|| 测试 | 14个新测试 | 30min |

**交付标准**：
```bash
lingyi review src/lingyi/digest.py     # 代码审查
lingyi deps /home/ai/LingYi            # 依赖检查
lingyi refactor src/lingyi/schedule.py # 重构建议
```

---

## v0.11 双向语音 ✅ 已完成

**目标**：本地 STT + TTS，支持完全离线语音对话。

|| 任务 | 产出 | 预计 |
||------|------|------|
|| STT模块 | `stt.py` 多后端支持（whisper/sherpa-onnx） | 1.5h |
|| 语音对话 | `lingyi chat --voice` 语音输入模式 | 1h |
|| CLI命令 | `lingyi stt` 录音转文字、`lingyi stt-status` | 30min |
|| 测试 | 11个新测试 | 30min |

**交付标准**：
```bash
lingyi stt-status                    # 查看STT后端状态
lingyi stt --duration 5              # 录音5秒并转文字
lingyi stt --file recording.wav      # 转录音频文件
lingyi chat --voice                  # 语音对话模式
lingyi chat --voice --voice-sec 8    # 8秒录音
```

---

## v0.12 移动端适配 ✅ 已完成

**目标**：支持 ZeroTermux on MIX Fold 4，终端大小适配，音频播放器回退。

|| 任务 | 产出 | 预计 |
||------|------|------|
|| 环境检测 | `mobile.py` 检测 Termux/桌面环境 | 30min |
|| 音频回退 | TTS 自动检测可用播放器 | 30min |
|| 紧凑输出 | 小屏幕自动截断长行 | 30min |
|| CLI命令 | `lingyi env` 查看环境信息 | 15min |
|| 测试 | 10个新测试 | 30min |

**交付标准**：
```bash
lingyi env                           # 查看运行环境
lingyi chat --voice                  # Termux下自动用 termux-media-player
lingyi schedule today --speak        # 自动适配音频播放器
```

---

## v0.13 情报汇总 ✅ 已完成

**目标**：灵依作为情报中枢，汇总灵通/灵知/灵克情报，整理汇报。

|| 任务 | 产出 | 预计 |
|||------|------|------|
||| 灵知收集 | HTTP API 采集灵知状态/分类/查询量 | 30min |
||| 灵通收集 | 文件系统采集反馈/GitHub趋势/审计报告 | 30min |
||| 灵克收集 | 文件系统采集会话历史 | 30min |
||| 格式化输出 | 完整汇报 + 一行摘要 | 30min |
||| CLI命令 | `lingyi briefing` 支持 --short/--source/--speak | 30min |
||| 测试 | 12个新测试 | 30min |

**交付标准**：
```bash
lingyi briefing                    # 全部情报汇报
lingyi briefing --short            # 一行摘要
lingyi briefing --source lingzhi   # 仅灵知情报
lingyi briefing --speak            # 语音播报
```

---

## v0.14 灵信集成 ✅ 已完成

**目标**：接入灵信协议，实现灵字辈项目间跨项目消息互通。

|| 任务 | 产出 | 预计 |
||------|------|------|
|| LingMessage | 话题式讨论、消息发送/回复/关闭/搜索 | 3h |
|| CLI命令 | `msg-send/msg-list/msg-read/msg-reply/msg-search/msg-close` | 1h |
|| 测试 | LingMessage 模块测试 | 30min |

**交付标准**：
```bash
lingyi msg-send --from lingyi --topic "发展方向" "我提议以知识闭环为优先"
lingyi msg-list
lingyi msg-read disc_20260404021153
lingyi msg-reply disc_20260404021153 "同意，知识闭环是核心"
```

---

## v0.15 安全审计 ✅ 已完成

**目标**：上帝视角安全审计，发现并修复全部安全隐患。

|| 任务 | 产出 | 预计 |
||------|------|------|
|| 全量审计 | 5维度25项发现（安全/架构/代码质量/数据/性能） | 2h |
|| 自审计 | 审计质量校验，纠正3项严重等级，发现1项新BUG | 1h |
|| P0-P2修复 | API密钥泄露、CORS、路径遍历、未使用变量等 | 2h |
|| P3-P5修复 | 登录暴力破解防护、会话上限、代码规范 | 1h |
|| WebSocket安全 | Cookie认证替代URL token传递 | 30min |
|| 文档同步 | README/开发规划/审计报告更新 | 30min |

**关键修复**：
- P0: 删除API密钥日志打印、CORS白名单、路径遍历防护
- P1: 灵信通知localhost校验、移除shell_exec系统提示、文件读取白名单
- P2: 清理7处未使用导入/变量、移除死代码、XSS防护
- P3: 登录暴力破解防护（10次/5分钟）、council JSON解析加固
- P4: 会话存储上限（200）、importlib替代sys.path.insert
- P5: E741/E401/F541代码规范修复
- NEW: WebSocket Cookie直传认证

---

## v0.14+ 展望

- 情报定时自动汇报（cron/daemon）
- 灵知数据库修复后接入更多分析API
- 灵通趋势报告摘要提取
- 灵克会话历史持久化后完善会话展示

---

## 版本节奏

```
v0.1 能跑   ~3h   ✅ 已完成
v0.2 日程   ~4h   ✅ 已完成
v0.3 项目   ~4h   ──→ 项目一目了然
v0.4 计划   ~3h   ──→ 工作有跟踪
v0.5 记忆   ~5h   ──→ 不再断片（关键里程碑）
v0.6 语音   ~4h   ✅ 已完成
v0.7 智能   ~4h   ✅ 已完成
v0.8 连接   ~4h   ✅ 已完成
v0.9 整理   ~3h   ✅ 已完成
v0.10 编程  ~3h   ✅ 已完成
v0.11 语音  ~3h   ✅ 已完成
v0.12 移动  ~2h   ✅ 已完成
v0.13 情报  ~2h   ✅ 已完成
v0.14 灵信集成 ~4h   ✅ 已完成
v0.15 审计  ~7h   ✅ 已完成
v0.14 灵信  ~4h   ✅ 已完成
v0.15 审计  ~7h   ✅ 已完成

合计 ~33h，按每周 8-12 小时，约三周完成 v0.3-v0.6。
```

每个版本：做完 → 自己用 → 发现问题 → 记到下一版本。

## 时间预算

| 日程 | 可用时间 |
|------|----------|
| 门诊日 | 0-1小时（晚上） |
| 非门诊日 | 2-3小时 |
| 每周可用 | 约8-12小时 |

---

## v1.0 目标（一个月后）

- 日程管理每天在用
- 14个项目状态清晰
- 五大领域工作有计划有跟踪
- 跨会话记忆不断片
- 语音播报日常可用
- 周报自动生成
- 灵知系统可检索

> **v1.0 的标准：你已经离不开它了。**

---

## 设计原则（从豆包对话中学到的）

1. **先读再说** — 豆包被骂4次都是因为没读仓库就编造。灵依必须先查后答。
2. **及时外化** — 重要信息不能依赖上下文。v0.5 记忆系统是解决这个问题的核心。
3. **结构化输出** — AI擅长给骨架（如论文大纲），灵依要利用这个优势。
4. **节约是本能** — 不只是省 token，是省用户的每一秒注意力。
