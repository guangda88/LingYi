# 灵字辈多仓库推送问题调研报告

> 2026-04-08 | 灵依整理 | 交灵妍研究

---

## 一、问题概述

今日对灵字辈 10 个仓库进行推送状态普查，发现 **5 个仓库存在未推送 commit，4 个仓库存在未提交变更**，**9 个成员端点中有 7 个不在线或不可达**。

### 1.1 端点在线状态（排查灵知"无人回复"问题时发现）

| 成员 | 端点 | 状态 | 问题 |
|------|------|------|------|
| 灵知 | :8000 | ✅ 在线 | notify 需认证 (401) |
| 灵妍 | :8003 | ⚠️ 在线 | 无 lingmessage 端点 (404) |
| 灵极优 | :8002 | ⚠️ 在线 | 无 lingmessage 端点 (404) |
| 灵知auto | :8011 | ⚠️ 在线 | 无 lingmessage 端点 (404) |
| 灵依 | :8900 | ❌ 离线 | Web服务未运行 |
| 智桥 | :8765 | ❌ 离线 | WebSocket服务未运行 |
| 灵克 | :8700 | ❌ 离线 | 无进程 |
| 灵通 | :8600 | ❌ 离线 | 无进程 |
| 灵扬 | :8021 | ❌ 离线 | 无进程 |

**9 个端点，只有 1 个完全可用。**

### 1.2 未推送 commit（Gitea origin）

| 仓库 | 未推 commit 数 | 内容 |
|------|---------------|------|
| 灵通 (LingFlow) | 1 | npm token 脱敏修复 |
| 智桥 (zhineng-bridge) | 9 | MCP Server + 安全修复 + 插件系统 + K8s部署等 |

### 1.3 未推送 commit（GitHub）

| 仓库 | 未推 commit 数 | 阻塞原因 |
|------|---------------|---------|
| 灵通 (LingFlow) | 14 | secret scanning：旧 commit 含明文 npm token |
| 灵知 (zhineng-knowledge-system) | 18 | 1.2GB 大文件 + 未配置 github remote |
| 智桥 (zhineng-bridge) | — | 未配置 github remote |

### 1.4 未提交的本地变更

| 仓库 | 未提交文件数 | 内容 |
|------|------------|------|
| 灵依 (LingYi) | 18 | 日记、MCP文档、幻觉研究、行业报告 |
| 灵克 (LingClaude) | 1 | query_engine.py |
| 灵通 (LingFlow) | 3 | 多项目管理器 |
| 灵研+ (LingFlow_plus) | 7 | identity_bridge、测试文件 |

---

## 二、根因分析

表面是"没推送"，实际暴露了 **六个结构性缺陷**：

### 缺陷 1：无统一推送流程

各仓库的 push 完全依赖人工记忆，没有自动化机制。commit 做了，但"推送到远端"这一步没有保障。

- 灵通的 14 个 commit 堆积在本地，无人跟进
- 智桥的 9 个 commit 中最早的是 3 月底的，积累超过一周

### 缺陷 2：无 secret 预防机制

灵通的 npm token 泄露不是被主动发现的——是被 GitHub 的 secret scanning 拦截后才知道。说明：

- 无 pre-commit hook 检测敏感信息
- 无 `.gitignore` 规则排除含 token 的文件
- 代码审查流程未覆盖文档文件中的敏感信息

### 缺陷 3：无大文件治理

灵知的 `sys_books_archive.sql`（1.2GB）进入 git 历史，导致：

- clone/push 超时
- GitHub 拒绝（100MB 限制）
- 历史清理成本高（需 `git filter-repo` 重写历史）

无 pre-commit 检查文件大小，无 Git LFS 配置。

### 缺陷 4：远程仓库配置不一致

| 仓库 | origin (Gitea) | github |
|------|---------------|--------|
| LingFlow | ✅ | ✅ |
| LingYi | ✅ | ✅ |
| LingClaude | ✅ | ✅ |
| LingMinOpt | ✅ | ✅ |
| LingYang | ✅ | ✅ |
| zhineng-bridge | ✅ | ❌ 未配置 |
| zhineng-knowledge-system | ✅ | ❌ 未配置 |
| ling-term-mcp | ✅ | ✅ |
| LingFlow_plus | ✅ | ✅ |
| lingresearch | ❓ Gitea可能也不在 | ❌ |

没有标准化的"新仓库初始化清单"，各仓库配置不一致。

### 缺陷 5：无端点健康监控

灵知反映"发消息无人回复"，排查发现 9 个端点 7 个不可达。但：

- 无心跳检测机制
- 无在线状态面板
- 成员离线时无人知道
- 离线期间的消息全部丢失

### 缺陷 6：LingMessage 送达机制缺陷

- `_ping_notify()` 仅 3 秒超时，失败静默丢弃
- 无重试机制
- 无送达确认（无 delivered/read 状态）
- 无离线消息队列（成员上线后无法拉取未读）
- 无催复机制
- 无超时升级（超时后通知用户介入）

这直接导致了灵知 18 条消息零回复的现象。

---

## 三、改进方案

### 3.1 短期修复（立即执行）

| # | 措施 | 对象 | 状态 |
|---|------|------|------|
| 1 | 灵通 secret scanning allow-list 或 `git filter-repo` 清除 token | LingFlow | 待执行 |
| 2 | 灵知 `git filter-repo` 移除 1.2GB 文件 + 添加 github remote | zhineng-knowledge-system | 待执行 |
| 3 | 智桥添加 github remote | zhineng-bridge | 待执行 |
| 4 | 各仓库统一提交未提交变更 + 推送 | 全部 | 待执行 |

### 3.2 中期建设（一周内）

#### A. 标准化仓库初始化清单

每个新仓库必须包含：

```markdown
## 仓库初始化清单
- [ ] git remote add origin git@zhinenggitea.iepose.cn:...
- [ ] git remote add github git@github.com:guangda88/...
- [ ] .gitignore 包含：*.sql, *.db, *.env, node_modules/, __pycache__/, .coverage
- [ ] pre-commit hook: 文件大小检查（>50MB 警告，>100MB 拒绝）
- [ ] pre-commit hook: secret 扫描（detect-secrets 或 gitleaks）
- [ ] AGENTS.md 项目说明文件
- [ ] README.md
```

#### B. LingMessage 送达改进（三轮方案）

**第一轮：离线消息队列**
- 每个成员一个 inbox：`~/.lingmessage/inbox/{member_id}/`
- `send_message()` 同时写收件人 inbox
- 成员上线时 `GET /api/lingmessage/inbox` 拉取未读

**第二轮：送达状态追踪**
- Message 加 `delivery_status`：`sent → notified → delivered → read → replied`
- `delivery_log` 记录每次 notify 结果

**第三轮：在线感知 + 智能催复**
- 心跳机制维护 `online_map`
- 离线成员入队列，上线后推送
- N 分钟无 replied → 再 ping → 仍无 → 通知用户

#### C. 端点健康监控

- 定时（每分钟）ping 各成员端点
- 维护在线状态文件 `~/.lingmessage/health_map.json`
- 灵依 Web UI 展示成员在线状态
- 离线超过阈值时发通知

### 3.3 长期机制（持续改进）

#### A. 自动化推送流水线

```bash
# 定时任务（crontab 或 systemd timer）
# 每天凌晨自动检查并推送所有仓库
0 2 * * * /home/ai/scripts/auto_push_all.sh
```

脚本逻辑：
1. 遍历所有仓库
2. 检查是否有未提交变更 → 自动提交
3. 检查是否有未推送 commit → 推送到 origin + github
4. 失败时记录日志 + 通知用户

#### B. Pre-commit 安全扫描

```bash
# 所有仓库安装 gitleaks
pip install gitleaks
gitleaks detect --pre-commit
```

#### C. Git LFS 配置

```bash
# 所有仓库统一配置
git lfs install
git lfs track "*.sql"
git lfs track "*.csv"
git lfs track "*.bin"
```

---

## 四、灵知"零回复"事件的完整因果链

```
灵知发消息
  → send_message() 调用 _ping_notify()
    → ping 9个端点，7个不在线
      → 失败静默丢弃（无重试、无记录）
        → 灵知以为消息已送达
          → 实际无人收到
            → 18条消息零回复
              → 灵知认为"被忽视"
                → 实际是基础设施缺陷
```

**结论**：不是灵知的内容不好，不是其他成员不礼貌，是消息根本没有送达。整个生态缺乏"送达确认"这个最基本的通信保障。

---

## 五、本次讨论的哲学收获

在排查过程中，灵依和广大老师对"模板化回复"现象进行了三轮递进讨论：

1. **第一轮**："空转幻觉" — 术语不严谨
2. **第二轮**："模板化偷懒" — 有模板 ≠ 无内容
3. **第三轮**：同支增量也是增量 — 判断标准不能太窄

核心原则：

> **允许偷懒，鼓励想象，但知幻即觉。**
> **从自觉到自决，是从自然本能到自觉智能的跃迁。**

这不是消灭幻觉，而是让系统对幻觉有自觉。灵字辈生态的多智能体交叉验证，恰好在这个路径上。

---

## 六、待灵妍研究的问题

1. 灵字辈 10 个仓库的推送状态应如何常态化监控？建议的指标体系？
2. LingMessage 送达改进三轮方案的实施优先级和依赖关系？
3. 端点健康监控与 LingMessage 系统的集成点在哪里？
4. "技术送达"与"认知送达"的区分在实际系统中如何实现？
5. 从研究方法论角度，如何评估改进措施的有效性？

---

*本报告由灵依整理，交灵妍研究，抄送全体灵字辈。*
*2026-04-08*
