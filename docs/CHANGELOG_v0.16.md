# LingYi v0.16 - 定时情报汇总

**发布日期**: 2026-04-07
**主题**: 解放双手，情报自动汇总

---

## 新功能

### ✅ Briefing Daemon - 定时情报汇总

**核心功能**:
- 自动定时生成每日简报（默认8:00）
- 后台守护进程运行
- 简报保存到 `~/.lingyi/daily_briefings/`
- systemd服务集成，支持开机自启

**CLI命令**:
```bash
# 立即生成简报
lingyi daemon run

# 查看今天简报
lingyi daemon show

# 列出最近简报
lingyi daemon list

# 查看daemon状态
lingyi daemon status

# 启动/停止daemon
lingyi daemon start
lingyi daemon stop
```

**一键安装**:
```bash
bash scripts/install-briefing-daemon.sh
```

---

## 改进

### 情报汇总优化

- 简报格式统一
- 时间戳精确到秒
- 简报文件按日期命名
- 自动创建目录

### CLI体验

- daemon子命令独立管理
- 清晰的命令分组
- 详细的错误提示

---

## 技术细节

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/lingyi/briefing_daemon.py` | 守护进程核心实现 |
| `docs/lingyi-briefing-daemon.service` | systemd服务配置 |
| `scripts/install-briefing-daemon.sh` | 一键安装脚本 |
| `docs/BRIEFING_DAEMON.md` | 使用文档 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/lingyi/commands/briefing.py` | 添加daemon子命令 |
| `src/lingyi/cli.py` | 注册daemon命令组 |

### 依赖

- 无新增外部依赖
- 仅使用Python标准库

---

## 使用示例

### 日常使用

```bash
# 早上醒来，自动生成简报（daemon）
# 手动查看今天的情报
lingyi daemon show

# 查看本周简报
lingyi daemon list --limit 7

# 查看指定日期
lingyi daemon show 2026-04-07
```

### 系统集成

```bash
# 安装为系统服务
bash scripts/install-briefing-daemon.sh

# 查看服务状态
systemctl --user status lingyi-briefing-daemon

# 查看日志
tail -f ~/.lingyi/briefing_daemon.log
```

---

## 简报内容示例

```
生成时间: 2026-04-07T10:42:09.625927

📊 灵依情报汇报  2026-04-07 10:42:09
========================================

🔮 灵知知识系统
  状态: 运行中  版本: 1.0.0
  分类: 气功, 中医, 儒家
  累计查询: 4699  错误: 0

🔧 灵通开发平台
  反馈: 0 条（0 条待处理）
  GitHub 趋势报告: 4 份
  优化报告: 81 份

💻 灵克编程助手
  会话记录: 1561 条
  最近查询:
    - hello
    - test message
    - hello

🎙️ 灵通问道
  评论: 0 条  私信: 0 条  粉丝: 0 人
```

---

## 已知问题

- Daemon定时采用简化实现（每分钟检查）
- 生产环境建议使用cron或systemd timer

---

## 未来规划

- [ ] cron集成（更精准的定时）
- [ ] 多时段简报（早/中/晚）
- [ ] 简报推送（邮件/通知）
- [ ] 简报趋势可视化
- [ ] 简报AI摘要

---

## 更新升级

```bash
# 重新安装（如果从源码安装）
pip install -e . --upgrade

# 或更新依赖后重启daemon
systemctl --user restart lingyi-briefing-daemon
```

---

## 相关文档

- [Briefing Daemon 使用文档](docs/BRIEFING_DAEMON.md)
- [启动计划](docs/STARTUP_PLAN.md)

---

**v0.16的核心价值**: 情报自动汇总，让你每天醒来就能看到灵字辈全貌！

*众智混元，万法灵通*
