# LingYi Briefing Daemon - 定时情报汇总

**版本**: v0.16
**功能**: 自动定时收集灵通/灵知/灵克/灵通问道情报，生成每日简报

---

## 功能特性

- ✅ **定时自动**: 每天8:00自动生成简报
- ✅ **多源集成**: 灵通/灵知/灵克/灵通问道
- ✅ **文件存储**: 简报保存到 `~/.lingyi/daily_briefings/`
- ✅ **守护进程**: 后台运行，不占用终端
- ✅ **systemd集成**: 支持开机自启
- ✅ **CLI管理**: 简单的命令行界面

---

## 快速开始

### 1. 手动生成简报

```bash
# 立即生成一次简报
lingyi daemon run
```

### 2. 查看简报

```bash
# 查看今天的简报
lingyi daemon show

# 查看指定日期的简报
lingyi daemon show 2026-04-07

# 列出最近5条简报
lingyi daemon list

# 列出最近10条简报
lingyi daemon list --limit 10
```

### 3. 管理守护进程

```bash
# 查看daemon状态
lingyi daemon status

# 启动daemon（需要手动运行）
# 注意：建议使用systemd安装脚本
python3 -m lingyi.briefing_daemon start_daemon

# 停止daemon
lingyi daemon stop
```

---

## 安装为系统服务

### 自动安装

```bash
# 运行安装脚本
cd /home/ai/LingYi
bash scripts/install-briefing-daemon.sh
```

安装脚本会自动：
1. 复制 systemd 服务文件
2. 重新加载 systemd 配置
3. 启用开机自启
4. 启动服务
5. 显示服务状态

### 手动安装

```bash
# 1. 复制服务文件
mkdir -p ~/.config/systemd/user
cp docs/lingyi-briefing-daemon.service ~/.config/systemd/user/

# 2. 重新加载 systemd
systemctl --user daemon-reload

# 3. 启用开机自启
systemctl --user enable lingyi-briefing-daemon

# 4. 启动服务
systemctl --user start lingyi-briefing-daemon

# 5. 查看状态
systemctl --user status lingyi-briefing-daemon
```

---

## 日志和调试

### 查看日志

```bash
# Daemon日志文件
tail -f ~/.lingyi/briefing_daemon.log

# systemd日志
journalctl --user -u lingyi-briefing-daemon -f
```

### 检查状态

```bash
# 简报目录
ls -lh ~/.lingyi/daily_briefings/

# PID文件
cat ~/.lingyi/briefing_daemon.pid
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
  最近审计: DEEP_AUDIT_2026_04_03.md, ...

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

## 数据源说明

### 灵知 (LingZhi)
- API: `http://localhost:8000`
- 数据: 状态、版本、分类、查询统计

### 灵通 (LingFlow)
- 路径: `/home/ai/LingFlow/.lingflow/`
- 数据: 反馈统计、趋势报告、优化报告、审计报告

### 灵克 (LingClaude)
- 路径: `/home/ai/LingClaude/data/session_history.json`
- 数据: 会话记录、最近查询

### 灵通问道 (LingTongAsk)
- 路径: `/home/ai/lingtongask/data/fan_engagement/reports/`
- 数据: 评论、私信、粉丝数、情感分析

---

## 故障排查

### Daemon未运行

```bash
# 检查状态
lingyi daemon status

# 查看日志
tail -f ~/.lingyi/briefing_daemon.log

# 查看systemd服务状态
systemctl --user status lingyi-briefing-daemon
```

### 简报生成失败

1. 检查各服务是否运行
2. 检查文件权限
3. 查看详细日志

### 定时未触发

- 当前版本为简化实现，每分钟检查一次
- 生产环境建议使用cron或systemd timer

---

## 未来改进

- [ ] 改用cron定时（更精准）
- [ ] 支持多时段简报（早/中/晚）
- [ ] 简报推送（邮件/通知）
- [ ] 简报趋势分析
- [ ] 简报可视化（图表）

---

## 版本历史

### v0.16 (2026-04-07)
- ✅ 定时情报汇总功能
- ✅ systemd服务集成
- ✅ CLI管理命令
- ✅ 简报文件存储
- ✅ 自动生成目录

---

## 相关文件

- `src/lingyi/briefing_daemon.py` - 守护进程实现
- `src/lingyi/commands/briefing.py` - CLI命令
- `docs/lingyi-briefing-daemon.service` - systemd服务配置
- `scripts/install-briefing-daemon.sh` - 安装脚本
- `src/lingyi/briefing.py` - 情报收集模块

---

**让情报自动汇总，解放你的双手！** 🚀
