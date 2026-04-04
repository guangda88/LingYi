# 灵依 LingYi - 产品需求文档

## 项目概述

**项目名称**: 灵依 (LingYi)
**创建日期**: 2026-04-03
**版本**: 0.14.0
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
- 会话摘要持久化

### v0.6 — 语音
- TTS 语音播报（edge-tts）
- 交互式对话模式

### v0.7 — 智能
- 周报自动生成
- 智能提醒（基于记忆）

### v0.8 — 连接
- 灵知 REST API 对接
- 医疗查询护栏

### v0.9 — 信息整理
- 内容摘要与文件消化
- 知识入库

### v0.10 — 编程辅助深化
- 灵克 LingClaude 代码助手
- 代码审查、依赖分析、重构建议

### v0.11 — 双向语音
- Whisper 语音识别
- 语音命令（STT + TTS）

### v0.12 — 移动端
- 移动设备支持
- 远程访问

### v0.13 — 情报汇总
- 每日情报聚合
- 多源摘要（天气/日程/任务/项目）

### v0.14 — 灵信 (LingMessage)
- 跨项目讨论框架
- 话题式线程、9项目身份系统
- msg-send/msg-list/msg-read/msg-reply/msg-search/msg-close 命令

### v0.15 — Web UI
- 手机浏览器打开，替代 ZeroTermux 终端操作
- 语音对话为主，文字为辅（折叠屏场景）
- 快速查看日程/备忘/计划，不用记命令
- 自然对话操作所有功能（备忘/日程/计划/项目等）
- 与 CLI 共享同一套 AI 对话引擎（Qwen LLM）

### v0.14+ — 按需
- 见 DEVELOPMENT_PLAN.md

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
