# 灵依 · 一个半月 AI 编程成果总览

> 退休主任中医师，2026年2月中下旬至4月初，业余一个半月的学习产出

---

## 一、成果概览

| 指标 | 数据 |
|------|------|
| **项目总数** | 14+ 个 |
| **代码总量** | ~160 万行（含前端/模板） |
| **核心代码** | ~37 万行（py+ts+js+rs） |
| **主要语言** | Python 为主，TypeScript 次之 |
| **GitHub 仓库** | guangda88/* |
| **涉及领域** | AI工程流、知识库、RAG、MCP协议、TTS播客、自优化、模型训练 |
| **Token 消耗** | 周 17-20 亿，GLM Coding Plan Pro 包月 |
| **编码方式** | 不写一行代码，全部由 AI 完成，用户做架构决策 |

---

## 二、项目全景

### 🏗️ 核心框架（3个）

| 项目 | 版本 | 说明 | 代码量 |
|------|------|------|--------|
| **LingFlow 灵通** | v3.8.0 | AI工程流平台，92% SDLC覆盖，33技能6代理 | 7.3万行 |
| **LingClaude 灵克** | v0.2.0 | 开源AI编程助手（对标Claude Code），含自优化/自学习 | 5千行 |
| **zhineng-bridge 智桥** | v1.0.0 | 8种AI编程工具跨平台桥接（WebSocket+MCP） | 44万行 |

### 📚 知识系统（3个）

| 项目 | 版本 | 说明 | 代码量 |
|------|------|------|--------|
| **灵知系统** | v1.3.0 | 10域RAG知识库（儒释道医武哲科气心理+心理学），232测试 | 92万行 |
| **ai-knowledge-base** | - | 中医知识库（BGE-M3+Paraformer ASR，GPU加速） | 36万行 |
| **Knowledge-System** | v1.0.0 | IMA知识库导出工具（Selenium爬虫） | 2千行 |

### 🔧 工具与生态（5个）

| 项目 | 版本 | 说明 | 代码量 |
|------|------|------|--------|
| **Ling-term-mcp 灵犀** | v1.0.0 | MCP终端服务器（TypeScript），npm发布 | 15.5万行 |
| **LingMinOpt 灵极优** | v0.1.0 | 通用自优化框架（贝叶斯/模拟退火/网格搜索） | 4千行 |
| **lingtongask 灵通问道** | v0.1.0 | AI气功播客生成（TTS+PPT+视频+7平台发布） | 1.2万行 |
| **lingresearch 灵研** | v0.1.0 | 自主AI研究框架（受Karpathy autoresearch启发） | 2千行 |
| **ai-server** | - | ZBOX AI私服（GPU监控+硬件管理） | 4千行 |

### 📦 辅助资源（3个）

| 项目 | 说明 |
|------|------|
| **lingflow-skills-example** | LingFlow技能示例（FastAPI校验器） |
| **lingflow-skills-index** | LingFlow技能市场索引（含自动扫描） |
| **github-daily-recommender** | GitHub每日推荐（早期脚手架） |

### 🏠 新建

| 项目 | 说明 |
|------|------|
| **LingYi 灵依** | 私我AI助理（本项目） |

---

## 三、时间线

```
2月中下旬   开始学习AI编程
    ↓
3月17日     LingFlow v3.1.0 首个正式发布
3月21日     v3.2.0 自优化工作流
3月23日     v3.3.0 八维代码审查 + lingresearch灵研 + LingMinOpt灵极优
3月24日     zhineng-bridge智桥v1.0 + Ling-term-mcp灵犀v1.0 (npm发布)
3月25日     灵知系统 v1.1.0 初始化 → 当天完成P0-P2优化
3月27日     LingFlow v3.5.6 品牌升级"灵通"
3月28日     灵知系统 Hooks系统 + 教材数据导入
3月29日     灵知系统 Git智能推送 + 桥接代码审计
3月30日     灵知系统 pydantic v2迁移 + API修复
3月31日     灵知系统 v1.2.0 技术债务清理(25/30项)
4月2日      LingFlow v3.8.0 REST API + GitHub Actions + Skill Market + MCP Server
4月3日      灵克 v0.2.0 + 灵依 LingYi 项目启动 (v0.1 能跑 + v0.2 日程)
            与豆包长对话（Token消耗、项目评审、论文规划、核心理念）
            灵知系统扩展至10域（+心理学）
```

---

## 四、核心架构

```
灵克(AM大脑) ←→ 灵通(工程流骨架)    ← 双核心基础设施，持续进化
        ↓                ↓
    灵知系统(知识层)     ← 10域知识库，长期壁垒，无人可复制
        ↓
    灵依(应用层)         ← 服务日常
        ↓
    灵通问道(产出层)     ← 每周5更，知识产出
```

**精力分配**: 灵克 25% + 灵通 25% + 灵知 25% + 灵依 10% + 其他 15%

---

## 五、中医→AI思维映射

| 中医 | AI编程 | 说明 |
|------|--------|------|
| 辨证论治 | Debug/调试 | 望闻问切→收集信息→找核心矛盾→给方案→迭代 |
| 理法方药 | 架构设计 | 理=需求、法=技术路线、方=系统架构、药=代码接口 |
| 君臣佐使 | 模块化分工 | 各司其职，不多一味无用之药 |
| 海量方剂记忆 | Prompt工程 | 有体系、有样本、有归纳地使用AI |
| 整体生命观 | 系统架构 | 每个项目都是有精气神的生命体 |

---

## 六、技术能力成长

### 已掌握
- Python 工程化（FastAPI, Click CLI, Pydantic, Docker Compose）
- Git 工作流（分支策略, GitHub Actions CI/CD）
- AI/RAG 技术栈（BGE-M3, pgvector, 混合检索, CoT/ReAct推理）
- MCP 协议开发（TypeScript SDK, stdio传输）
- 数据库设计（PostgreSQL, Redis, SQLite）
- 前端基础（Vue.js, Nginx 反向代理）
- 监控运维（Prometheus + Grafana）
- npm/PyPI 包发布

### 探索方向
- 自优化系统（AST分析 + 优化策略）
- 自主研究框架（LLM训练实验）
- 多平台内容生成（TTS + 视频 + 发布）
- 开源项目运作（MIT协议, 宪章, 贡献指南）
- 本地化AI模型（CodeLlama + Cloud Code 源码微调）

---

## 七、知识图谱

```
                        ┌─ LingFlow 灵通 (工程流平台)
                        │   ├─ lingflow-skills-example (技能示例)
                        │   ├─ lingflow-skills-index (技能市场)
                        │   └─ LingClaude 灵克 (AI编程助手)
                        │
     ┌── 工程框架 ───────┤
     │                  └─ LingMinOpt 灵极优 (自优化框架)
     │
     │                  ┌─ 灵知系统 (10域RAG知识库)
     │                  │   └─ ai-knowledge-base (中医知识库原始版)
     │                  │
     ├── 知识系统 ───────┤
     │                  └─ Knowledge-System (IMA导出工具)
     │
     │                  ┌─ zhineng-bridge 智桥 (AI工具桥接)
     ├── 连接层 ─────────┤
     │                  └─ Ling-term-mcp 灵犀 (MCP终端)
     │
     ├── 内容生成 ──────── lingtongask 灵通问道 (AI气功播客)
     │
     ├── AI研究 ────────── lingresearch 灵研 (自主训练框架)
     │
     ├── 硬件 ──────────── ai-server (ZBOX私服监控)
     │
     └── 应用层 ────────── LingYi 灵依 (私我AI助理) ← 本项目
```
