# 灵依 LingYi 深度代码审计报告

> **审计范围**: `src/lingyi/` 全部源码 (~5,400 行)  
> **审计日期**: 2026-04-05  
> **基准版本**: `539f88b` (master, ahead of origin by 8 commits)  
> **审计方法**: 上帝视角逐文件审查，覆盖安全、业务逻辑、代码质量、合规、架构五个维度

---

## 一、总览

| 维度 | 严重 | 高危 | 中危 | 低危 | 信息 |
|------|------|------|------|------|------|
| 安全漏洞 | 2 | 3 | 3 | 1 | 1 |
| 代码质量 | — | — | 2 | 4 | 2 |
| 架构风险 | — | 1 | 2 | 1 | — |
| 业务逻辑 | — | — | 1 | 1 | — |
| 合规规范 | — | 1 | — | 1 | — |
| **合计** | **2** | **5** | **8** | **7** | **3** |

---

## 二、安全问题 (按严重程度排序)

### 🔴 CRITICAL-01: API 密钥明文写入日志
- **文件**: `web_app.py:839`
- **代码**: `logger.info(f"OpenAI client created, API key: {_GLM_API_KEY[:10]}...")`
- **风险**: 日志文件中永久记录 API 密钥前 10 位字符，配合密钥格式规律可还原完整密钥
- **影响**: 密钥泄露 → 账户被盗用 → 产生非预期费用
- **修复**:
  ```python
  # 改为
  logger.info(f"OpenAI client created, key suffix: ...{_GLM_API_KEY[-4:]}")
  # 或直接删除此行
  ```

### 🔴 CRITICAL-02: CORS 全开 + 凭证传递
- **文件**: `web_app.py:349`
- **代码**: `CORSMiddleware(app, allow_origins=["*"], allow_credentials=True)`
- **风险**: RFC 7235 规定 `credentials=True` 时 `origins=["*"]` 不应生效，但部分实现存在绕过
- **影响**: 恶意网页可跨域读取灵依用户的聊天记录、执行对话
- **修复**: 改为显式白名单
  ```python
  allow_origins=["http://localhost:8900", "http://127.0.0.1:8900"]
  ```

### 🟠 HIGH-01: SHA256 无盐密码校验
- **文件**: `web_app.py:288`
- **代码**: `hashlib.sha256(password.encode()).hexdigest()`
- **风险**: 无盐哈希可被彩虹表直接碰撞
- **影响**: 数据库泄露后密码可被快速还原
- **修复**: 使用 `hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)`，或迁移到 `bcrypt`

### 🟠 HIGH-02: `/api/discuss` 端点无认证
- **文件**: `web_app.py:327`
- **现状**: `api_discuss` 路由无任何 `require_auth` 装饰器
- **影响**: 任何可访问 8900 端口的人可匿名调用 LLM 接口，消耗 API 配额
- **修复**: 添加认证装饰器，或至少做 IP 白名单

### 🟠 HIGH-03: `file_read` 工具路径穿越
- **文件**: `tools.py` `_file_read` 函数
- **代码**: 直接 `open(path)` 读取文件，无路径限制
- **影响**: 可读取 `/etc/shadow`、`~/.ssh/id_rsa`、其他项目的 `presets.json` 等敏感文件
- **修复**: 添加路径白名单校验
  ```python
  ALLOWED_DIRS = ["/home/ai/LingYi", "/home/ai/LingFlow", "/tmp"]
  real = os.path.realpath(path)
  if not any(real.startswith(d) for d in ALLOWED_DIRS):
      return "Error: path outside allowed directories"
  ```

### 🟡 MEDIUM-01: SSL 验证全局关闭 (3 处)
- **文件**:
  - `council.py`: `ctx.check_hostname=False, ctx.verify_mode=ssl.CERT_NONE`
  - `lingmessage.py` `_ping_notify`: 跳过 SSL 验证
  - `bridge_client.py`: WebSocket 连接不验证证书
- **影响**: 中间人攻击可截获/篡改 LLM 通信内容
- **建议**: 内网通信可暂缓，但外网通信（如 LLM API）应启用验证

### 🟡 MEDIUM-02: 系统提示词暴露 `shell_exec` 能力
- **文件**: `web_app.py:81` (系统提示词)
- **现状**: 提示词中声明 "shell_exec" 可用，但实际工具列表中已禁用
- **风险**: LLM 可能尝试构造 shell 命令参数，利用其他工具间接执行
- **修复**: 从系统提示词中移除 `shell_exec` 的描述

### 🟡 MEDIUM-03: 无 API 速率限制
- **文件**: `web_app.py` 全局
- **现状**: 所有端点均无速率限制
- **影响**: 暴力破解密码、DDoS、API 配额耗尽
- **建议**: 添加 `slowapi` 或自定义中间件，至少对登录和 LLM 调用做限制

### 🟢 LOW-01: `user-select:none` 阻止文本复制
- **文件**: `templates/index.html:15`
- **现状**: ✅ 已在本次审计中修复

---

## 三、架构风险

### 🟠 ARCH-01: 工具定义三处重复
- **位置**:
  - `agent.py` — 12 个工具定义 (CLI 场景)
  - `tools.py` — 29 个工具定义 (Web 场景)
  - `web_app.py:81` — 系统提示词中再次描述工具能力
- **风险**: 修改一处遗忘其他 → 行为不一致；当前已出现 `shell_exec` 禁用但提示词仍声明的矛盾
- **修复**: 抽取 `tools/registry.py`，统一工具注册中心，按场景筛选

### 🟠 ARCH-02: 系统提示词三处独立维护
- **位置**:
  - `web_app.py:81` — Web 聊天 (~40 行)
  - `agent.py:460` — CLI agent (~35 行)
  - `voicecall.py:30` — 语音通话 (~30 行)
- **风险**: 角色设定、边界约束各版本不一致，难以统一更新
- **修复**: 抽取 `prompts.py`，按场景组合基础 + 场景特定片段

### 🟡 ARCH-03: 全局可变状态非线程安全
- **文件**: `llm_utils.py`
- **代码**: `_quota_exhausted = {}`、`_usage_tracker = {}` (模块级全局字典)
- **风险**: 如果将来部署多 worker (如 `gunicorn -w 4`)，状态不共享；当前单进程虽安全但架构脆弱
- **建议**: 迁移到 Redis 或 SQLite 持久化

### 🟡 ARCH-04: `sys.path` 操控副作用
- **文件**: `llm_utils.py` `_init_keys()` 函数
- **代码**: `sys.path.insert(0, "/home/ai/LingYi")`
- **风险**: 影响全局 import 解析顺序，可能遮蔽标准库
- **修复**: 使用 `importlib` 或配置 `PYTHONPATH` 环境变量

---

## 四、代码质量问题

### QC-01: 未使用的导入 (7 处)

| 文件 | 行 | 未使用导入 |
|------|-----|----------|
| `agent.py:15` | `import re` |
| `agent.py:18` | `from pathlib import Path` |
| `voicecall.py:11` | `GLM_API_KEY` |
| `voicecall.py:12` | `GLM_BASE_URL` |
| `voicecall.py:13` | `import os` |
| `config.py:1` | `from pathlib import Path` |
| `stt.py` | `import sherpa_onnx` (stubbed) |

### QC-02: `llm_utils.py` 变量作用域问题
- **F823**: `_GLM_BASE_URL` 在 `_init_keys()` 中定义，但在模块级函数 `call_llm_with_fallback()` 中引用
- 如果 `_init_keys()` 未先调用，将抛 `NameError`
- **修复**: 在模块级声明 `_GLM_BASE_URL = None`

### QC-03: 未使用的变量
- `llm_utils.py:238` — `F841` 局部变量赋值后未使用

### QC-04: LSP 警告汇总 (31 项)
- Ruff 检出 31 项警告，以 `E402` (import 不在文件顶部) 和 `F401` (未使用导入) 为主
- 主要集中在 `agent.py`、`voicecall.py`、`llm_utils.py`

---

## 五、业务逻辑问题

### BIZ-01: 议事厅去重 Bug
- **文件**: `council.py`
- **现状**: `_is_near_duplicate(last_content, "")` — 第二个参数为空字符串
- **影响**: 去重函数永远返回 `False`，形同虚设
- **修复**: 传入正确的历史内容参数

### BIZ-02: LLM JSON 解析无 Schema 校验
- **文件**: `council.py` 解析 LLM 返回 JSON 处
- **风险**: LLM 返回格式异常时 `KeyError` 导致整个投票循环崩溃
- **修复**: 添加 `try/except KeyError` + 合理默认值

---

## 六、合规问题

### COMP-01: 医疗守界 — 实现良好 ✅
- `ask.py` 的 `_is_medical_query()` 关键词过滤有效
- `connect.py` 不暴露 `中医` 分类
- **注意**: `web_app.py` 的 `/api/discuss` 可绕过此守界 — 任何人可直接问医疗问题

### COMP-02: 日志中的个人信息
- Web 聊天记录持久化于 `~/.lingyi/sessions/`，无加密
- 备忘录内容明文存储于 SQLite
- **建议**: 敏感内容标注 + 本地加密（如果设备可能被他人访问）

---

## 七、各模块健康度评分

| 模块 | 文件 | 行数 | 评分 | 说明 |
|------|------|------|------|------|
| db | `db.py` | 88 | ⭐⭐⭐⭐⭐ | 参数化查询、WAL 模式，干净 |
| models | `models.py` | 68 | ⭐⭐⭐⭐⭐ | 纯数据类，无问题 |
| config | `config.py` | 30 | ⭐⭐⭐⭐ | 多一个未用导入 |
| memo | `memo.py` | — | ⭐⭐⭐⭐ | CRUD 清晰 |
| schedule | `schedule.py` | — | ⭐⭐⭐⭐ | 功能完整 |
| tts | `tts.py` | 69 | ⭐⭐⭐⭐⭐ | 干净 |
| stt | `stt.py` | 149 | ⭐⭐⭐⭐ | sherpa-onnx stub 合理 |
| ask | `ask.py` | 130 | ⭐⭐⭐⭐⭐ | 医疗守界做得好 |
| code | `code.py` | 131 | ⭐⭐⭐⭐ | 截断保护到位 |
| briefing | `briefing.py` | 299 | ⭐⭐⭐ | 跨项目文件读取无边界 |
| llm_utils | `llm_utils.py` | 273 | ⭐⭐⭐ | 全局状态 + sys.path 操控 |
| tools | `tools.py` | 625 | ⭐⭐⭐ | path traversal 需修 |
| agent | `agent.py` | 561 | ⭐⭐⭐ | 未用导入 + 工具重复 |
| voicecall | `voicecall.py` | 475 | ⭐⭐⭐ | 未用导入 + 提示词重复 |
| council | `council.py` | 624 | ⭐⭐ | SSL 关闭 + 去重 Bug + JSON 无校验 |
| lingmessage | `lingmessage.py` | 527 | ⭐⭐⭐ | SSL 关闭 + 广播无认证 |
| bridge_client | `bridge_client.py` | 139 | ⭐⭐⭐ | SSL 关闭 |
| **web_app** | `web_app.py` | **1401** | ⭐⭐ | **最多问题：CORS、密钥日志、密码无盐、公开端点** |

---

## 八、优先修复建议 (TOP 5)

| 优先级 | 编号 | 修复内容 | 预估工作量 |
|--------|------|---------|-----------|
| **P0** | CRIT-01 | 删除 API 密钥日志行 | 1 分钟 |
| **P0** | CRIT-02 | CORS 改为白名单 | 5 分钟 |
| **P1** | HIGH-01 | 密码加 salt / 迁移 bcrypt | 30 分钟 |
| **P1** | HIGH-02 | `/api/discuss` 添加认证 | 15 分钟 |
| **P1** | HIGH-03 | `file_read` 路径白名单 | 20 分钟 |

---

## 九、审计结论

灵依的核心功能模块（memo、schedule、project、plan、session）质量扎实，遵循了项目"简单能跑"的设计哲学。问题集中在**网络服务层**（web_app.py、council.py、lingmessage.py），这些是后期新增的外向型功能，安全意识不足。

**最紧迫的三件事**：
1. 立即删除 `web_app.py:839` 的密钥日志
2. 立即修复 CORS 配置
3. 本周内为 `/api/discuss` 和 `file_read` 加固

审计过程中已直接修复 1 项：`user-select:none` CSS (index.html:15)。

---

*审计完成。以上所有发现均基于 `539f88b` 版本静态代码审查，未进行运行时渗透测试。*
