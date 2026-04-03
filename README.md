# 灵依 LingYi

> 你的私我AI助理

灵依，寓意**灵性相依**——一个完全属于你的私人AI助理。
深度理解你的习惯与需求，提供个性化智能服务，数据本地化、隐私可控。

## 版本

- **v0.4 计划** — 五大领域任务追踪、周计划、完成率统计
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
│   │   └── plan.py          #   计划命令
│   ├── config.py            # 预设加载器
│   ├── db.py                # SQLite 连接
│   ├── models.py            # 数据模型
│   ├── memo.py              # 备忘录逻辑
│   ├── schedule.py          # 日程逻辑
│   ├── project.py           # 项目逻辑
│   ├── plan.py              # 计划逻辑
│   └── patrol.py            # 项目巡检
├── tests/                   # 测试
├── docs/                    # 文档
│   ├── MISSION.md           #   宪章
│   ├── DEVELOPMENT_PRINCIPLES.md  # 开发原则
│   └── DEVELOPMENT_PLAN.md  #   开发规划
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
```

## 配置

私人数据存放在 `~/.lingyi/presets.json`（不入Git），包括：
- 门诊排班、练功/日记日程
- 项目列表（14个项目详情）
- 巡检路径（各项目本地路径）

模板见 `presets.example.json`。

## 技术栈

| 原则 | 选择 |
|------|------|
| 语言 | Python 3.12 |
| 框架 | Click (CLI) |
| 数据库 | SQLite |
| 存储 | 本地文件 |

## 文档

- [宪章 MISSION.md](docs/MISSION.md) — 使命、价值观、边界
- [开发原则 DEVELOPMENT_PRINCIPLES.md](docs/DEVELOPMENT_PRINCIPLES.md) — 十条开发原则
- [开发规划 DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) — 版本路线图
