# 审计报告自审计补遗 (v0.15 报告的质量校验)

> **校验日期**: 2026-04-05  
> **校验方法**: 逐条复验原报告每项发现的行号、代码、严重性评级、上下文描述，并扫描原报告遗漏的盲区

---

## 一、原报告错误与修正

### ❌ 修正 1: HIGH-01 严重性评级偏高 — SHA256 密码并非设计缺陷

**原报告说**: "SHA256 无盐密码校验" (HIGH)

**实际代码** (`web_app.py:261-288`):
```
密码策略是三层递进：
1. bcrypt (首选，rounds=12)
2. pbkdf2_hmac sha256 + salt + 100k iterations (bcrypt 不可用时的回退)
3. sha256 无盐 (仅用于兼容旧数据，代码注释明确标注"迁移后应删除")
```

**裁定**: SHA256 回退是有意的兼容设计，非安全疏忽。当前新密码必然走 bcrypt/pbkdf2。严重性应从 **HIGH 降级为 LOW**（技术债：应设置迁移截止日并删除旧代码）。

---

### ❌ 修正 2: QC-03 行号错误

**原报告说**: "`llm_utils.py:238` — F841 局部变量赋值后未使用"

**实际代码**: 未使用变量在 **第 76 行** (`next_reset = _next_reset_time()`)，非第 238 行。第 238 行是一个 `if` 条件判断，非赋值。

---

### ❌ 修正 3: tools.py 工具数量错误

**原报告说**: "tools.py — 29 个工具定义"

**实际**: tools.py 注册了 **28 个活跃工具**（shell_exec 的 `_register` 已注释掉，不计入）。agent.py 有 **12 个工具**。原报告说 "重叠定义" 是对的，但数量不精确。

---

### ⚠️ 修正 4: MEDIUM-01 SSL 关闭的风险上下文不完整

**原报告说**: "SSL 验证全局关闭 (3 处)"，暗示外部通信不安全

**实际**: 所有 SSL 关闭仅用于 **localhost 通信** (`127.0.0.1`)。council.py 和 lingmessage.py 的端点全是本地服务间调用。关闭原因是自签名证书。原报告未说明这一重要上下文，可能导致过度恐慌。

**裁定**: 对内网通信而言应为 **LOW**（技术债），非 MEDIUM。但如果将来有外网部署，应重新评估。

---

### ⚠️ 修正 5: `/api/discuss` 公开访问的影响面描述不完整

**原报告说**: "允许匿名 LLM API 使用"

**实际影响面更大**: 
- `/api/discuss` 不仅消耗 API 配额，它还**直接调用 LLM 生成回复并返回**
- 攻击者可构造 prompt 注入（传入恶意 `topic`/`context`/`question`），使灵依的身份发出任意内容
- `/api/lingmessage/notify` 也同为公开端点，可被外部伪造通知消息

---

## 二、原报告遗漏的发现

### 🔴 NEW-CRIT-01: `_GLM_BASE_URL` 的 `global` 声明缺失 — 静默 Bug

- **文件**: `llm_utils.py:42`
- **代码**: `_GLM_BASE_URL = get_key("GLM_BASE_URL") or _GLM_BASE_URL`
- **问题**: 函数内赋值 `_GLM_BASE_URL` 但未声明 `global _GLM_BASE_URL`，Python 将其视为**局部变量**。由于右侧也引用 `_GLM_BASE_URL`（此时被认为是局部变量），Ruff 报 **F823: Local variable referenced before assignment**。
- **影响**: `get_key("GLM_BASE_URL")` 获取的自定义 base URL **永远不生效**。如果用户在密钥库中配置了非默认的 GLM API 端点，系统会静默使用默认值 `https://open.bigmodel.cn/api/paas/v4`。
- **严重性**: **MEDIUM**（功能缺陷，非安全漏洞，但用户完全不知道配置无效）

### 🟠 NEW-HIGH-01: WebSocket Token 在 URL 参数中暴露

- **文件**: `web_app.py:746`
- **代码**: `raw_token = websocket.query_params.get("token", "")`
- **问题**: WebSocket 认证 token 通过 URL query parameter 传递（`/ws/chat?token=xxx`），这意味着：
  - Token 出现在服务器访问日志中
  - Token 出现在浏览器历史/Referrer header 中
  - 若通过 HTTP（非 HTTPS），token 被明文传输
- **严重性**: **MEDIUM**（当前仅内网使用，若外网部署则升级为 HIGH）

### 🟠 NEW-HIGH-02: 登录端点无暴力破解防护

- **文件**: `web_app.py:361-379`
- **代码**: `/api/login` 端点无任何尝试次数限制、延迟、或锁定机制
- **影响**: 攻击者可无限次尝试密码
- **原报告提到**: 是（MEDIUM-03 "无速率限制"），但未单独指出登录场景的特殊严重性

### 🟠 NEW-HIGH-03: `dashboard.py` HTML 注入 (XSS 向量)

- **文件**: `dashboard.py:236-240`
- **问题**: 使用 `str.replace()` 将数据直接注入 HTML 模板，无转义处理。若情报数据包含 `<script>` 等 HTML 标签，生成 dashboard.html 后浏览将触发 XSS
- **严重性**: **MEDIUM**（dashboard 通过文件系统访问，非 HTTP 服务；但如果通过 web server 提供访问则升级）

### 🟡 NEW-MED-01: 会话存储无上限 — 内存泄漏风险

- **文件**: `web_app.py:174`
- **代码**: `_SESSIONS: dict[str, datetime] = {}`
- **问题**: 无最大会话数限制，无主动清理循环。仅依赖惰性清理（`_check_auth` 时删除过期 token）。如果大量登录请求（正常或恶意），内存将持续增长
- **严重性**: **LOW**（个人工具，用户量极小）

### 🟡 NEW-MED-02: `web.py` (legacy) — WebSocket 无认证

- **文件**: `web.py:68-157`
- **问题**: 旧版 web UI 的 WebSocket 端点完全无认证，session key 仅基于客户端 IP
- **严重性**: **MEDIUM**（若 legacy web.py 仍在使用）

### 🟡 NEW-MED-03: `commands/web.py` 密码通过命令行参数传递

- **文件**: `commands/web.py:12`
- **问题**: `--password` 作为 CLI 参数，在 `ps aux` 中可见
- **严重性**: **LOW**（单用户个人机器）

### 🟡 NEW-MED-04: `dashboard.py` 加载外部 CDN 资源无 SRI

- **文件**: `dashboard.py:36`
- **问题**: 加载 `cdn.jsdelivr.net` 的 Chart.js，无 Subresource Integrity hash
- **严重性**: **LOW**（供应链风险，实际被利用概率极低）

---

## 三、原报告遗漏的文件

| 文件 | 行数 | 原报告是否覆盖 | 关键发现 |
|------|------|----------------|---------|
| `dashboard.py` | 478 | ❌ 未覆盖 | HTML 注入、CDN 无 SRI |
| `trends.py` | 402 | ❌ 未覆盖 | 纯数据处理，无安全问题 |
| `web.py` (legacy) | 318 | ❌ 未覆盖 | WebSocket 无认证、无输入校验 |
| `templates/chat.html` | 280 | ❌ 未覆盖 | XSS 安全（textContent），低风险 |
| `templates/login.html` | 56 | ❌ 未覆盖 | 密码明文传输（依赖 HTTPS）、无 CSRF |
| `commands/council.py` | 83 | ❌ 未覆盖 | 纯 CLI 分发，无风险 |
| `commands/web.py` | 19 | ❌ 未覆盖 | CLI 密码泄漏风险 |

**总结**: 原报告覆盖了 ~5,400 行代码中的 ~4,300 行 (80%)，遗漏了 7 个文件共 ~1,100 行。其中 `dashboard.py` 和 `web.py` 有实际安全问题。

---

## 四、严重性评级校准

| 编号 | 原评级 | 校准评级 | 理由 |
|------|--------|----------|------|
| CRIT-01 (密钥日志) | 🔴 CRITICAL | 🔴 CRITICAL | ✅ 正确，行号/代码准确 |
| CRIT-02 (CORS 全开) | 🔴 CRITICAL | 🔴 CRITICAL | ✅ 正确 |
| HIGH-01 (SHA256 密码) | 🟠 HIGH | 🟢 LOW | 有 bcrypt/pbkdf2 主路径，SHA256 仅兼容旧数据 |
| HIGH-02 (discuss 公开) | 🟠 HIGH | 🟠 HIGH | ✅ 正确，且影响面比原报告描述更大 |
| HIGH-03 (file_read 穿越) | 🟠 HIGH | 🟠 HIGH | ✅ 正确 |
| MEDIUM-01 (SSL 关闭) | 🟡 MEDIUM | 🟢 LOW | 仅限 localhost 通信 |
| MEDIUM-02 (shell_exec 提示) | 🟡 MEDIUM | 🟡 MEDIUM | ✅ 正确 |
| MEDIUM-03 (无限速) | 🟡 MEDIUM | 🟡 MEDIUM | ✅ 正确，但应单独强调登录场景 |
| LOW-01 (user-select) | 🟢 LOW | ✅ 已修复 | |
| ARCH-01 (工具重复) | 🟠 HIGH | 🟡 MEDIUM | 是代码质量问题而非紧急安全风险 |
| ARCH-02 (提示词重复) | 🟠 HIGH | 🟡 MEDIUM | 同上 |

---

## 五、校准后的问题总表

| 严重性 | 数量 | 说明 |
|--------|------|------|
| 🔴 CRITICAL | **2** | 密钥日志、CORS 全开 |
| 🟠 HIGH | **3** | discuss 公开、file_read 穿越、登录无暴力防护 |
| 🟡 MEDIUM | **6** | shell_exec 幽灵提示、无限速、_GLM_BASE_URL bug、WS token 暴露、dashboard XSS、legacy web.py |
| 🟢 LOW | **9** | SHA256 兼容代码、SSL localhost、会话无上限、CLI 密码、CDN 无 SRI、未用导入等 |
| **合计** | **20** | 比原报告 25 项少 5 项（合并重复、降级过评项） |

---

## 六、审计报告自身的质量问题

| 问题 | 说明 |
|------|------|
| **行号错误 1 处** | QC-03 说 `llm_utils.py:238`，实际是第 76 行 |
| **数据不精确 1 处** | tools.py 工具数量说 29，实际 28 |
| **上下文缺失 2 处** | SHA256 兼容设计的上下文、SSL 仅限 localhost |
| **文件覆盖 80%** | 遗漏 7 个文件，其中 2 个有安全问题 |
| **新发现 Bug 1 个** | `_GLM_BASE_URL` global 声明缺失 — 静默功能性 Bug |
| **严重性偏差 3 处** | HIGH-01 偏高、ARCH-01/02 偏高、MEDIUM-01 偏高 |

---

## 七、最终结论

原审计报告的**核心发现准确**（2 个 CRITICAL 确实是 CRITICAL），但存在以下系统性偏差：

1. **过度评级倾向** — 对已知的兼容设计（SHA256 回退）和内网场景（SSL localhost）给予过高严重性
2. **上下文缺失** — 未充分描述代码的设计意图，可能误导修复优先级
3. **覆盖盲区** — 遗漏了 `dashboard.py`（有 XSS 向量）和 legacy `web.py`（无认证）
4. **遗漏 1 个实际 Bug** — `_GLM_BASE_URL` 的 global 声明缺失导致自定义 API 端点配置永远不生效

**建议修正优先级不变**: P0 仍是密钥日志和 CORS，但 P1 应加入 `_GLM_BASE_URL` global Bug（功能性修复，1 行代码）。

---

*自审计完成。原报告经校验后可信度约 85%，核心结论成立，细节需以上述修正为准。*
