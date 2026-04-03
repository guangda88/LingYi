# 灵依 LingYi — 开发规划

> 遵循最小可用、渐进增强。每个版本做完就用，用了再定下一个版本。

---

## 版本总览

```
v0.1 能跑    v0.2 日程     v0.3 项目     v0.4 计划     v0.5 记忆     v0.6 智能     v0.7+ 按需
  │           │             │             │             │             │             │
  ▼           ▼             ▼             ▼             ▼             ▼             ▼
CLI入口     门诊排班      项目看板      工作计划      偏好存储      周报生成      编程辅助
SQLite基础  日程增删查    进度跟踪      任务管理      LingFlow集成  灵知对接      信息整理
备忘录      上诊提醒      状态统计      五大领域      跨会话记忆    智能提醒
```

---

## v0.1 能跑（~3h）

**目标**：CLI能跑，数据库能存，备忘录能增删查。

| 任务 | 产出 | 预计 |
|------|------|------|
| 项目结构搭建 | `src/lingyi/` 包结构，CLI入口 | 45min |
| SQLite 数据模型 | schedules、memos 两张表 | 45min |
| CLI 备忘录命令 | `lingyi memo add/list/show` | 45min |
| 基础测试 | 数据模型CRUD测试 | 30min |

**交付标准**：
```bash
lingyi memo add "今天开始灵依项目"
lingyi memo list
lingyi memo show 1
```

**目录结构**：
```
src/lingyi/
├── __init__.py
├── cli.py           # Click CLI入口
├── db.py            # SQLite连接与初始化
├── models.py        # 数据模型（dataclass）
└── memo.py          # 备忘录
```

---

## v0.2 日程（~4h）

**目标**：门诊排班实际可用，每天能用上。

| 任务 | 产出 | 预计 |
|------|------|------|
| 日程模型 | schedule表增删改查 | 1h |
| 门诊排班 | 设定每周6个半天固定排班 | 1h |
| 今日/本周视图 | `lingyi schedule today/week` | 1h |
| 上诊提醒 | `lingyi schedule remind` 检查今日是否有门诊 | 30min |
| 测试 | 日程CRUD + 查询 + 提醒逻辑 | 30min |

**交付标准**：
```bash
lingyi schedule init clinic           # 初始化门诊排班
lingyi schedule add --type study --day Saturday --time morning
lingyi schedule today                 # 今日安排
lingyi schedule week                  # 本周一览
lingyi schedule remind                # 检查提醒
```

> **注意**：门诊具体在哪几天需要用户确认后填入。

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

## v0.5 记忆（~4h）

**目标**：接入LingFlow，开始积累记忆。

| 任务 | 产出 | 预计 |
|------|------|------|
| LingFlow集成 | import lingflow，用其工作流能力 | 2h |
| 记忆系统 | 跨会话偏好存储与读取 | 1.5h |
| 测试 | 集成测试 | 30min |

**交付标准**：
```bash
lingyi memory set "我偏好上午编程"
lingyi memory get
lingyi memory list
```

---

## v0.6 智能（~4h）

**目标**：基于记忆的智能功能，灵知对接。

> 智能提醒依赖 v0.5 的记忆系统，故拆为独立版本。

| 任务 | 产出 | 预计 |
|------|------|------|
| 智能提醒 | 基于历史习惯的提醒建议 | 1.5h |
| 周报生成 | `lingyi report` 自动生成本周总结 | 1h |
| 灵知对接 | 非医疗类知识检索（REST API） | 1h |
| 测试 | 集成测试 | 30min |

**交付标准**：
```bash
lingyi schedule remind                # 现在会基于记忆给出建议
lingyi report                        # 本周总结
lingyi ask "灵通的最新版本是多少"     # 查灵知
```

---

## v0.7+ 按需

> 以下功能需要AI对话能力，非CLI独立实现，视需求决定是否开发。

- 编程辅助（代码答疑、调试）
- 信息整理与摘要

---

## 版本节奏

```
v0.1 能跑   ~3h   ──→ 立即可用
v0.2 日程   ~4h   ──→ 每天用上
v0.3 项目   ~4h   ──→ 项目一目了然
v0.4 计划   ~3h   ──→ 工作有跟踪
v0.5 记忆   ~4h   ──→ 开始积累
v0.6 智能   ~4h   ──→ 开始变聪明

合计 ~22h，按每周 8-12 小时，约两周完成 v0.1-v0.4，第三周完成 v0.5-v0.6。
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
- 周报自动生成
- 记忆系统开始积累
- 灵知系统可检索

> **v1.0 的标准：你已经离不开它了。**
