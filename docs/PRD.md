# 灵依 LingYi - 产品需求文档

## 项目概述

**项目名称**: 灵依 (LingYi)
**创建日期**: 2026-04-03
**版本**: 0.1.0
**定位**: 私我AI助理

## 宪章与原则

- 宪章详见 [MISSION.md](./MISSION.md)（含边界）
- 开发原则详见 [DEVELOPMENT_PRINCIPLES.md](./DEVELOPMENT_PRINCIPLES.md)
- 用户画像详见 [USER_PROFILE.md](./USER_PROFILE.md)

## 版本规划

详见 [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md)

## 功能总览（按版本递进）

### v0.1 — 能跑
- CLI 入口 + SQLite 基础
- 备忘录增删查

### v0.2 — 日程
- 门诊排班
- 日程增删查
- 今日/本周视图
- 上诊提醒

### v0.3 — 项目
- 14个项目录入与状态管理
- 项目看板

### v0.4 — 计划
- 五大领域任务管理
- 周计划与进度

### v0.5 — 记忆
- 跨会话偏好存储
- LingFlow 集成

### v0.6 — 智能
- 周报自动生成
- 灵知系统对接
- 智能提醒（基于记忆）

### v0.7+ — 按需
- 编程辅助（需 AI 对话能力，非 CLI 独立实现）
- 信息整理与摘要（同上）

## 边界

以 [MISSION.md](./MISSION.md) 中边界表为准。

## 资源约束

- **Token 预算**: 每周 17 亿
- **原则**: 极度节约

## 技术栈

- 语言: Python 3.12
- 框架: LingFlow v3.8.0
- 数据库: SQLite（够用再升级）
- 交互: CLI 优先
