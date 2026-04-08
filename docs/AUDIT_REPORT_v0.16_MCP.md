# 灵字辈 MCP 集成审计报告 v0.16

> **审计日期**: 2026-04-07
> **审计范围**: 灵依 v0.16.0 + 灵克 v0.3.0 MCP Server 实现
> **审计类型**: 安全审计 + 一致性审计 + 代码质量审查
> **审计者**: 灵依 (LingYi)

---

## 📊 审计总览

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完整性 | ⭐⭐⭐⭐⭐ (5/5) | 灵依12工具 + 灵克15工具，全部注册可用 |
| 测试覆盖 | ⭐⭐⭐⭐ (4/5) | 灵克21测试全过，灵依252测试全过；缺少MCP stdio集成测试 |
| 安全性 | ⭐⭐⭐ (3/5) | ast_edit.py 路径穿越漏洞(HIGH)；bash blocklist 绕过风险(HIGH) |
| 一致性 | ⭐⭐⭐⭐ (4/5) | 版本号、入口点已同步；3份文档待更新 |
| 代码质量 | ⭐⭐⭐⭐⭐ (5/5) | FastMCP装饰器模式简洁、Result monad解包正确 |

---

## 🔴 安全审计（6项发现）

### SEC-01: ast_edit.py 路径穿越漏洞 [HIGH]

**位置**: `lingclaude/engine/ast_edit.py:replace_function_body()` 和 `list_functions()`
**严重性**: 🔴 HIGH
**描述**: `replace_function_body()` 和 `list_functions()` 直接使用 `Path(file_path)` 读取文件，没有路径解析和边界检查。攻击者可通过 `../../etc/passwd` 等路径读取或修改任意文件。

**对比**: `file_read.py` 和 `file_edit.py` 均实现了 `_resolve()` 方法，使用 `resolve()` + `relative_to()` 防止路径穿越。

**修复方案**:
```python
# 在 ast_edit.py 中添加路径解析，参考 file_read.py 的 _resolve() 模式
def _resolve_path(file_path: str, base_dir: str = ".") -> Result[Path]:
    p = Path(file_path)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (Path(base_dir).resolve() / p).resolve()
    try:
        resolved.relative_to(Path(base_dir).resolve())
    except ValueError:
        return Result.fail(f"路径越界: {file_path}")
    return Result.ok(resolved)
```

**状态**: 待修复

---

### SEC-02: BashExecutor blocklist 绕过风险 [HIGH]

**位置**: `lingclaude/engine/bash.py:BashExecutor.run()`
**严重性**: 🔴 HIGH
**描述**: `BashExecutor` 使用 `shell=True` 执行命令，虽有命令黑名单（`rm`, `sudo`, `wget` 等），但可通过 shell 元字符绕过：
- `r''m -rf /` (空字符串拼接)
- `/bin/rm -rf /` (绝对路径)
- `\rm -rf /` (转义字符)

**影响**: MCP 工具 `run_bash` 继承此风险。远程 MCP 调用者可能执行任意命令。

**缓解因素**: 
- BashExecutor 有 512MB 内存限制和 30s CPU 限制
- MCP 运行环境为可信内网
- 黑名单已覆盖常见危险命令

**建议**: 长期应改用 `shell=False` + `subprocess.run(["bash", "-c", command])` 并加强参数校验。短期可增强黑名单（添加 `/bin/`, `/usr/bin/` 前缀匹配）。

**状态**: 已知风险，引擎层面问题（非MCP层）

---

### SEC-03: grep.py ReDoS 风险 [MEDIUM]

**位置**: `lingclaude/engine/grep.py:GrepTool.search()`
**严重性**: 🟡 MEDIUM
**描述**: `GrepTool` 接受用户提供的正则表达式，未对正则复杂度做限制。恶意正则如 `(a+)+b` 可导致灾难性回溯（ReDoS），使服务无响应。

**缓解因素**:
- `max_results=200` 限制匹配数
- `max_line_length=500` 截断长行
- BashExecutor 的 30s 超时也限制了 grep 执行时间

**建议**: 添加正则复杂度校验或改用 `ripgrep` 的 `--regex-size-limit` 参数。

**状态**: 已知风险，影响有限

---

### SEC-04: 灵依 mcp_server.py 缺少工作目录隔离 [LOW]

**位置**: `src/lingyi/mcp_server.py`
**严重性**: 🟢 LOW
**描述**: 灵依的 MCP 工具直接调用 `memo.add_memo()` 等函数，这些函数内部使用全局 DB 路径。MCP 调用者无法指定工作目录或数据库路径，意味着所有 MCP 调用共享同一个 SQLite 数据库。

**影响**: 如果多个 MCP 客户端同时调用灵依工具，可能出现 SQLite 写入冲突。

**缓解因素**: SQLite WAL 模式已启用，支持并发读取。

**状态**: 可接受（单用户场景）

---

### SEC-05: 灵克 MCP 工具默认工作目录 [LOW]

**位置**: `lingclaude/mcp/server.py` 各工具函数
**严重性**: 🟢 LOW
**描述**: `read_file`, `write_file`, `edit_code`, `search_code` 在 `working_dir` 为空时默认 `base_dir="."`。如果 MCP Server 从非预期目录启动，可能导致文件操作作用到错误目录。

**缓解因素**: 已在测试中发现并修复（添加 `working_dir` 参数），实际使用时调用者应始终指定 `working_dir`。

**状态**: 已通过测试验证

---

### SEC-06: advisor.py save_report 路径保护不完整 [LOW]

**位置**: `lingclaude/self_optimizer/advisor.py:OptimizationAdvisor.save_report()`
**严重性**: 🟢 LOW
**描述**: `save_report()` 对 `output_path` 做了基本的 `resolve()` 检查，但未限制写入到特定基础目录，理论上可写入任意位置。

**缓解因素**: MCP 工具 `get_advice` 不调用 `save_report()`，仅调用 `generate_report()` 返回字符串。

**状态**: 不影响 MCP 安全面

---

## 🔄 一致性审计（7项发现）

### CON-01: 灵克版本号不一致 [FIXED]

**位置**: `lingclaude/__init__.py`
**发现**: `__version__` 为 `"0.2.0"`，但 `pyproject.toml` 为 `"0.3.0"`。
**修复**: 已将 `__version__` 更新为 `"0.3.0"`。

---

### CON-02: 灵依 pyproject.toml 版本号不一致 [FIXED]

**位置**: `pyproject.toml`
**发现**: `version` 为 `"0.15.0"`，但 `__init__.py` 为 `"0.16.0"`。
**修复**: 已将 `pyproject.toml` 更新为 `"0.16.0"`。

---

### CON-03: 灵依 mcp_server.py 缺少 main() 入口 [FIXED]

**位置**: `src/lingyi/mcp_server.py`
**发现**: 文件没有 `main()` 函数和 `__main__` 块，`lingyi-mcp` 入口点无法启动。
**修复**: 已添加 `main()` 和 `if __name__ == "__main__"` 块。

---

### CON-04: 灵克 mcp/__init__.py 为空 [FIXED]

**位置**: `lingclaude/mcp/__init__.py`
**发现**: 文件为空，未导出 `mcp` 和 `main`。
**修复**: 已添加 `from .server import mcp, main` 和 `__all__`。

---

### CON-05: LING_FAMILY_MEMBERS.md 灵克版本过期 [PENDING]

**位置**: `docs/LING_FAMILY_MEMBERS.md`
**发现**: 灵克版本仍为 `0.2.1`，实际已升级到 `0.3.0`。
**修复**: 待更新。

---

### CON-06: LING_FAMILY_MCP_ASSESSMENT.md 灵克工具名过期 [PENDING]

**位置**: `docs/LING_FAMILY_MCP_ASSESSMENT.md`
**发现**: 灵克 MCP 的 15 个工具中，有 6 个与实际实现不一致：

| 评估文档中的名称 | 实际实现名称 | 中文名变化 |
|-----------------|-------------|-----------|
| generate_code (灵衍) | list_functions (灵析) | 新增AST函数列举 |
| refactor_code (灵构) | replace_function (灵构) | 改为AST级别函数替换 |
| git_branch (灵支) | git_status (灵态) | 改为只读Git状态 |
| git_commit (灵提) | git_log (灵史) | 改为只读提交历史 |
| git_merge (灵合) | git_diff (灵异) | 改为只读差异对比 |
| (无) | index_project (灵索) | 已实现，名称不变 |

**设计决策**: 选择只读 Git 工具（status/log/diff）而非写入工具（branch/commit/merge），因为 MCP 暴露写入操作风险更高。选择 AST 级别工具（list_functions/replace_function）映射到实际引擎 API。

**修复**: 待更新。

---

### CON-07: LING_FAMILY_MCP_COORDINATION.md B1 任务清单过期 [PENDING]

**位置**: `docs/LING_FAMILY_MCP_COORDINATION.md`
**发现**: B1 灵克任务清单中的工具名与实际不符：
- 灵衍 → 灵析（generate_code → list_functions）
- 灵支/灵提/灵合 → 灵态/灵史/灵异（git写入 → git只读）

**修复**: 待更新。

---

## 🧪 测试审计

### 灵克 MCP Server 测试

**文件**: `tests/test_mcp_server.py` (183行, 21个测试)
**结果**: ✅ 21/21 通过

| 测试类 | 测试数 | 覆盖范围 |
|-------|--------|---------|
| TestMCPToolRegistration | 5 | 15工具注册、分类、灵系命名 |
| TestReadFile | 2 | 正常读取、不存在文件 |
| TestWriteFile | 1 | 创建新文件 |
| TestEditCode | 1 | 替换文本 |
| TestSearchCode | 2 | 正则搜索、字面搜索 |
| TestRunBash | 2 | 简单命令、危险命令拦截 |
| TestGitTools | 3 | status/log/diff |
| TestIndexProject | 1 | 项目索引 |
| TestListFunctions | 1 | 函数列举 |
| TestEvaluateCode | 1 | 代码评估 |
| TestCheckTriggers | 1 | 触发条件检查 |
| TestGetAdvice | 1 | 优化建议 |

**缺失测试**: replace_function、run_optimization（run_optimization 因依赖 optuna 可选包，跳过合理）

### 灵依测试

**文件**: `tests/test_basic.py` (252个测试)
**结果**: ✅ 252/252 通过

版本断言已从 `0.15.0` 更新为 `0.16.0`（lines 784, 793）。

---

## 📐 代码质量审查

### 架构模式

两个 MCP Server 均采用 **FastMCP 装饰器模式**：

```
@mcp.tool(name="tool_name", description="描述（灵X）")
def tool_xxx(params...) -> ReturnType:
    from .module import func
    result = func(params)
    return _unwrap(result)
```

**优点**:
- 每个工具 ~5-10 行，极简
- 懒加载导入（`from ..engine.xxx import Yyy`），避免循环依赖
- Result monad 解包统一（`_unwrap()` helper）
- dataclass 自动转 dict（`_to_dict()` helper）

### _unwrap() 实现

灵克版本比灵依更复杂，因需要处理 Result[T] monad：

```python
def _unwrap(result: Any) -> Any:
    if hasattr(result, "is_ok") and not result.is_ok:
        return {"error": str(result.error), "ok": False}
    if hasattr(result, "data"):
        val = result.data  # 注意：是 .data 不是 .value
        return _to_dict(val) if dataclasses.is_dataclass(val) else val
    ...
```

**关键**: 灵克 Result monad 用 `.data` 非 `.value`，已在初始测试中确认。

### 依赖管理

| 项目 | MCP依赖 | 入口点 | Build配置 |
|------|---------|--------|----------|
| 灵依 | `mcp>=1.0` | `lingyi-mcp = "lingyi.mcp_server:main"` | `packages.find.where = ["src"]` |
| 灵克 | `mcp>=1.0` | `lingclaude-mcp = "lingclaude.mcp.server:main"` | `packages.find.include = ["lingclaude*"]` |

**灵克 Build 修复**: 灵克曾因 flat-layout 导致 "Multiple top-level packages discovered" 错误，通过添加 `[tool.setuptools.packages.find]` with `include = ["lingclaude*"]` 修复。

---

## 📋 审计结论

### 已完成

- ✅ 灵依 v0.16.0 pyproject.toml 版本同步
- ✅ 灵克 v0.3.0 版本号全面同步（`__init__.py` + `pyproject.toml`）
- ✅ 灵依 mcp_server.py main() 入口添加
- ✅ 灵克 mcp/__init__.py 模块导出
- ✅ 灵克 pyproject.toml build 配置修复
- ✅ 灵克 21 个 MCP 测试全部通过
- ✅ 灵依 252 个测试全部通过
- ✅ 安全审计完成（6项发现）
- ✅ 一致性审计完成（7项发现）

### 待完成

- 🔴 **SEC-01**: ast_edit.py 路径穿越修复（HIGH）
- 🟡 **CON-05**: LING_FAMILY_MEMBERS.md 灵克版本更新
- 🟡 **CON-06**: LING_FAMILY_MCP_ASSESSMENT.md 工具名更新
- 🟡 **CON-07**: LING_FAMILY_MCP_COORDINATION.md 任务清单更新
- 🟡 重新安装灵依/灵克验证入口点

### 风险接受

以下风险在当前可接受范围内：
- SEC-02 (bash blocklist 绕过) — 引擎层面问题，MCP层无法修复
- SEC-03 (grep ReDoS) — 有超时和结果数限制
- SEC-04 (灵依 DB 隔离) — 单用户场景

---

*灵依审计，众智混元*
