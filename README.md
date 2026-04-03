# 灵依 LingYi

> 你的私人AI助理

灵依，寓意**灵性相依**——一个完全属于你的私人AI助理。
深度理解你的习惯与需求，提供个性化智能服务，数据本地化、隐私可控。

## 版本

- **v0.13 情报汇总** — 每日情报聚合、多源摘要、天气/日程/任务/项目一站概览
- v0.12 移动端 — 移动设备支持、远程访问
- v0.11 双向语音 — Whisper语音识别、语音命令
- v0.10 编程辅助深化 — 灵克代码助手、代码审查、重构
- v0.9 信息整理 — 内容摘要、文件消化、知识入库
- v0.8 连接 — 灵知知识库对接、医疗查询护栏
- v0.7 智能 — 智能提醒、周报生成
- v0.6 语音 — TTS语音播报、交互式对话
- v0.5 记忆 — 会话摘要、偏好持久化
- v0.4 计划 — 五大领域任务追踪、周计划、完成率统计
- v0.3 项目 — 14项目看板、状态管理
- v0.2 日程 — 门诊排班、练功提醒、日记提醒
- v0.1 能跑 — CLI入口、SQLite、备忘录

## 项目结构

```
LingYi/
├── src/lingyi/
│   ├── cli.py              # CLI 入口（命令路由）
│   ├── commands/            # CLI 子命令
│   │   ├── memo.py          #   备忘录命令
│   │   ├── schedule.py      #   日程命令
│   │   ├── project.py       #   项目命令
│   │   ├── plan.py          #   计划命令
│   │   ├── session.py       #   会话命令
│   │   ├── pref.py          #   偏好命令
│   │   ├── chat.py          #   交互对话
│   │   ├── connect.py       #   灵知/灵克命令
│   │   ├── digest.py        #   信息整理命令
│   │   ├── briefing.py      #   情报汇总命令
│   │   ├── voice.py         #   语音命令
│   │   └── mobile.py        #   移动端命令
│   ├── models.py            # 数据模型
│   ├── db.py                # SQLite 连接
│   ├── config.py            # 预设加载器
│   ├── memo.py              # 备忘录逻辑
│   ├── schedule.py          # 日程逻辑
│   ├── project.py           # 项目逻辑
│   ├── plan.py              # 计划逻辑
│   ├── session.py           # 会话记忆
│   ├── pref.py              # 偏好管理
│   ├── report.py            # 周报生成
│   ├── tts.py               # TTS 语音合成
│   ├── stt.py               # STT 语音识别
│   ├── patrol.py            # 项目巡检
│   ├── ask.py               # 灵知知识库对接
│   ├── code.py              # 灵克编程助手
│   ├── digest.py            # 内容摘要
│   ├── briefing.py          # 情报聚合
│   └── mobile.py            # 移动端支持
├── tests/                   # 测试（211 tests）
├── docs/                    # 文档
│   ├── MISSION.md           #   宪章
│   ├── DEVELOPMENT_PRINCIPLES.md  # 开发原则
│   ├── DEVELOPMENT_PLAN.md  #   开发规划
│   └── AUDIT_REPORT_v0.13.md #  v0.13 审计报告
├── presets.example.json     # 预设模板（公开）
└── pyproject.toml           # 项目配置
```

## 快速开始

```bash
cd LingYi
pip install -e . --break-system-packages

# 复制预设模板，填入真实数据
cp presets.example.json ~/.lingyi/presets.json

# 初始化数据
lingyi schedule init clinic
lingyi schedule init practice
lingyi project init

# 日常使用
lingyi memo add "今天开始灵依项目"
lingyi schedule today
lingyi plan add "灵知系统安全加固" --area 编程 --project 灵知 --due 2026-04-10
lingyi plan list
lingyi plan done 1
lingyi plan stats
lingyi project list
lingyi patrol

# 知识与编程
lingyi ask "什么是气功"
lingyi ask "道德经的核心思想" --category 道家
lingyi code "写一个快速排序函数"

# 语音
lingyi schedule today --speak
lingyi stt recording.wav

# 信息整理
lingyi digest ~/notes.txt
lingyi briefing

# 智能
lingyi schedule remind --smart
lingyi report
```

## 配置

私人数据存放在 `~/.lingyi/presets.json`（不入Git），包括：
- 门诊排班、练功/日记日程
- 项目列表详情
- 巡检路径（各项目本地路径）

模板见 `presets.example.json`。

## 技术栈

| 原则 | 选择 |
|------|------|
| 语言 | Python 3.12 |
| 框架 | Click (CLI) |
| 数据库 | SQLite |
| TTS | edge-tts (Microsoft) |
| STT | Whisper (OpenAI) |
| 存储 | 本地文件 |

## 文档

- [宪章 MISSION.md](docs/MISSION.md) — 使命、价值观、边界
- [开发原则 DEVELOPMENT_PRINCIPLES.md](docs/DEVELOPMENT_PRINCIPLES.md) — 十条开发原则
- [开发规划 DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) — 版本路线图 v0.1–v0.14+
- [审计报告 AUDIT_REPORT_v0.13.md](docs/AUDIT_REPORT_v0.13.md) — v0.13 系统审计
