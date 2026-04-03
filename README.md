# 灵依 LingYi

> 你的私我AI助理

灵依，寓意**灵性相依**——一个完全属于你的私人AI助理。
深度理解你的习惯与需求，提供个性化智能服务，数据本地化、隐私可控。

## 项目结构

```
LingYi/
├── .lingflow/           # LingFlow 工作目录
│   ├── config/          # 配置文件
│   ├── sessions/        # 会话状态
│   └── logs/            # 日志输出
├── src/                 # 源代码
├── tests/               # 测试
├── docs/                # 文档
│   └── PRD.md           # 产品需求文档
├── skills/              # LingFlow 技能
├── workflows/           # 工作流定义
└── README.md            # 项目说明
```

## 快速开始

```bash
cd LingYi
lingflow list-skills
lingflow run <skill-name>
lingflow workflow <workflow.yaml>
```

## 版本

- v0.1.0 - 项目初始化，定义私我AI助理方向
