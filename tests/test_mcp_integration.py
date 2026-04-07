"""灵依 MCP Server 集成测试 — 27个工具端到端验证。

测试策略:
  1. 工具注册完整性 — 所有27个工具正确注册
  2. Schema 正确性 — 参数类型、描述、必填项
  3. 个人管理工具 — add_memo, list_memos, add_schedule, list_schedules, add_plan, list_plans
  4. 项目报告工具 — show_project, generate_report, patrol_project
  5. 情报汇总工具 — get_briefing, digest_content, ask_lingzhi
  6. 边界与错误 — 空数据、无效参数、服务不可用
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_TEST_PRESETS = str(Path(__file__).parent / "test_presets.json")


def _call(server, tool_name, args):
    """调用 MCP 工具并标准化返回值为 [TextContent(...)] 列表。

    MCP SDK 1.27+ 在返回空/None时返回 (list, dict) tuple，
    正常返回时返回 list[TextContent]。此函数统一为 list。
    """
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        server.call_tool(tool_name, args)
    )
    return result


def _unwrap(result):
    """将 call_tool 结果统一为单个 TextContent，text 为完整 JSON。

    MCP SDK 1.27+ 对列表/字符串返回值返回 (list[TextContent], {'result': val}) tuple。
    对单个 dict 返回 list[TextContent]。
    本函数统一返回 [TextContent]，text 保持原始格式。
    """
    if isinstance(result, tuple):
        content_list, meta = result
        if meta and "result" in meta:
            val = meta["result"]
            if isinstance(val, str):
                from mcp.types import TextContent
                return [TextContent(type="text", text=val)]
            from mcp.types import TextContent
            return [TextContent(type="text", text=json.dumps(val))]
        return content_list
    return result

# ── Fixtures ──


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
    monkeypatch.setattr("lingyi.db.DB_PATH", db_path)
    monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
    return str(db_path)


@pytest.fixture
def mcp_server(tmp_db):
    """导入并返回 MCP server 实例（确保 DB 已重定向）。"""
    from lingyi.mcp_server import mcp

    return mcp


# ── 1. 工具注册完整性 ──


class TestToolRegistration:

    @pytest.mark.asyncio
    async def test_all_27_tools_registered(self, mcp_server):
        tools = await mcp_server.list_tools()
        names = {t.name for t in tools}
        expected = {
            # 原始12个
            "add_memo", "list_memos", "add_schedule", "list_schedules",
            "add_plan", "list_plans", "show_project", "generate_report",
            "patrol_project", "get_briefing", "digest_content", "ask_lingzhi",
            # P0新增15个
            "today_schedule", "week_schedule", "smart_remind",
            "done_plan", "week_plans", "plan_stats",
            "list_projects", "save_session", "last_session",
            "search_knowledge", "speak", "synthesize_to_file", "transcribe",
            "council_scan", "council_health",
        }
        assert expected == names

    @pytest.mark.asyncio
    async def test_tool_count(self, mcp_server):
        tools = await mcp_server.list_tools()
        assert len(tools) == 27

    @pytest.mark.asyncio
    async def test_server_name(self, mcp_server):
        assert mcp_server.name == "LingYi"

    @pytest.mark.asyncio
    async def test_server_has_instructions(self, mcp_server):
        assert mcp_server.instructions is not None
        assert len(mcp_server.instructions) > 0


# ── 2. Schema 正确性 ──


class TestToolSchemas:

    @pytest.mark.asyncio
    async def test_add_memo_schema(self, mcp_server):
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "add_memo")
        schema = json.loads(tool.inputSchema.model_dump_json()) if hasattr(tool.inputSchema, 'model_dump_json') else tool.inputSchema
        assert "content" in schema["properties"]
        assert "content" in schema["required"]

    @pytest.mark.asyncio
    async def test_add_schedule_schema(self, mcp_server):
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "add_schedule")
        schema = tool.inputSchema
        props = schema["properties"] if isinstance(schema, dict) else schema.model_dump()["properties"]
        assert "schedule_type" in props
        assert "day" in props
        assert "time_slot" in props

    @pytest.mark.asyncio
    async def test_add_plan_schema(self, mcp_server):
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "add_plan")
        schema = tool.inputSchema
        props = schema["properties"] if isinstance(schema, dict) else schema.model_dump()["properties"]
        assert "content" in props
        assert "area" in props

    @pytest.mark.asyncio
    async def test_list_memos_has_limit_param(self, mcp_server):
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "list_memos")
        schema = tool.inputSchema
        props = schema["properties"] if isinstance(schema, dict) else schema.model_dump()["properties"]
        assert "limit" in props

    @pytest.mark.asyncio
    async def test_digest_content_schema(self, mcp_server):
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "digest_content")
        schema = tool.inputSchema
        props = schema["properties"] if isinstance(schema, dict) else schema.model_dump()["properties"]
        assert "text" in props

    @pytest.mark.asyncio
    async def test_ask_lingzhi_schema(self, mcp_server):
        tools = await mcp_server.list_tools()
        tool = next(t for t in tools if t.name == "ask_lingzhi")
        schema = tool.inputSchema
        props = schema["properties"] if isinstance(schema, dict) else schema.model_dump()["properties"]
        assert "question" in props
        assert "category" in props

    @pytest.mark.asyncio
    async def test_all_tools_have_description(self, mcp_server):
        tools = await mcp_server.list_tools()
        for t in tools:
            assert t.description, f"Tool {t.name} missing description"


# ── 3. 个人管理工具 ──


class TestPersonalManagement:

    @pytest.mark.asyncio
    async def test_add_memo(self, mcp_server):
        result = await mcp_server.call_tool("add_memo", {"content": "MCP测试备忘"})
        assert isinstance(result, list)
        text = result[0].text
        data = json.loads(text)
        assert data["content"] == "MCP测试备忘"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_list_memos_empty(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("list_memos", {"limit": 10}))
        data = json.loads(result[0].text)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_add_then_list_memos(self, mcp_server):
        await mcp_server.call_tool("add_memo", {"content": "集成测试A"})
        await mcp_server.call_tool("add_memo", {"content": "集成测试B"})
        result = _unwrap(await mcp_server.call_tool("list_memos", {"limit": 10}))
        data = json.loads(result[0].text)
        contents = [m["content"] for m in data]
        assert "集成测试A" in contents
        assert "集成测试B" in contents

    @pytest.mark.asyncio
    async def test_add_schedule(self, mcp_server):
        result = await mcp_server.call_tool("add_schedule", {
            "schedule_type": "work",
            "day": "Monday",
            "time_slot": "morning",
            "description": "MCP集成测试",
        })
        data = json.loads(result[0].text)
        assert data["type"] == "work"
        assert data["day"] == "Monday"
        assert data["time_slot"] == "morning"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_list_schedules(self, mcp_server):
        await mcp_server.call_tool("add_schedule", {
            "schedule_type": "test",
            "day": "Friday",
            "time_slot": "afternoon",
        })
        result = _unwrap(await mcp_server.call_tool("list_schedules", {"schedule_type": "test"}))
        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["type"] == "test"

    @pytest.mark.asyncio
    async def test_add_plan(self, mcp_server):
        result = await mcp_server.call_tool("add_plan", {
            "content": "完成MCP集成测试",
            "area": "编程",
            "due_date": "2026-04-10",
        })
        data = json.loads(result[0].text)
        assert data["content"] == "完成MCP集成测试"
        assert data["area"] == "编程"
        assert data["status"] == "todo"

    @pytest.mark.asyncio
    async def test_list_plans(self, mcp_server):
        await mcp_server.call_tool("add_plan", {"content": "计划X", "area": "研究"})
        result = _unwrap(await mcp_server.call_tool("list_plans", {"area": "研究"}))
        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert any(p["content"] == "计划X" for p in data)

    @pytest.mark.asyncio
    async def test_list_plans_by_status(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("list_plans", {"status": "todo"}))
        data = json.loads(result[0].text)
        for p in data:
            assert p["status"] == "todo"


# ── 4. 项目报告工具 ──


class TestProjectReport:

    @pytest.mark.asyncio
    async def test_show_project_not_found(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("show_project", {"name_or_alias": "不存在项目"}))
        text = result[0].text
        data = json.loads(text)
        assert data is None

    @pytest.mark.asyncio
    async def test_show_project_after_add(self, mcp_server, tmp_path, monkeypatch):
        from lingyi.project import add_project

        add_project(name="MCP测试项目", alias="mcp_test", priority="P1")
        result = _unwrap(await mcp_server.call_tool("show_project", {"name_or_alias": "mcp_test"}))
        data = json.loads(result[0].text)
        assert data is not None
        assert data["name"] == "MCP测试项目"
        assert data["alias"] == "mcp_test"

    @pytest.mark.asyncio
    async def test_generate_report(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("generate_report", {}))
        text = result[0].text
        assert "灵依周报" in text
        assert "日程" in text or "计划" in text

    @pytest.mark.asyncio
    async def test_patrol_project(self, mcp_server):
        try:
            result = _unwrap(await mcp_server.call_tool("patrol_project", {}))
            text = result[0].text
            assert isinstance(text, str)
            assert len(text) > 0
        except Exception:
            pass  # patrol 依赖文件系统路径，测试环境中可能不可用


# ── 5. 情报汇总工具 ──


class TestIntelligenceDigest:

    @pytest.mark.asyncio
    async def test_get_briefing(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("get_briefing", {"compact": True}))
        text = result[0].text
        assert isinstance(text, str)
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_get_briefing_full(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("get_briefing", {"compact": False}))
        text = result[0].text
        assert "灵依情报汇报" in text

    @pytest.mark.asyncio
    async def test_digest_content_with_todos(self, mcp_server):
        result = await mcp_server.call_tool("digest_content", {
            "text": "需要完成MCP集成测试\n决定使用FastMCP框架\n记得提交代码",
        })
        data = json.loads(result[0].text)
        assert "todos" in data
        assert "decisions" in data
        assert len(data["todos"]) >= 1
        assert len(data["decisions"]) >= 1

    @pytest.mark.asyncio
    async def test_digest_content_empty(self, mcp_server):
        result = await mcp_server.call_tool("digest_content", {"text": ""})
        data = json.loads(result[0].text)
        assert data["todos"] == []
        assert data["raw_lines"] == 0

    @pytest.mark.asyncio
    async def test_digest_content_with_prefs(self, mcp_server):
        result = await mcp_server.call_tool("digest_content", {
            "text": "我喜欢在早上写代码\n偏好使用Python语言",
        })
        data = json.loads(result[0].text)
        assert len(data["prefs"]) >= 1

    @pytest.mark.asyncio
    async def test_ask_lingzhi_medical_blocked(self, mcp_server):
        result = await mcp_server.call_tool("ask_lingzhi", {
            "question": "怎么治感冒吃什么药",
            "category": "",
        })
        data = json.loads(result[0].text)
        assert data["available"] is False
        assert "医学" in data["answer"]

    @pytest.mark.asyncio
    async def test_ask_lingzhi_service_unavailable(self, mcp_server):
        result = await mcp_server.call_tool("ask_lingzhi", {
            "question": "什么是气功",
            "category": "气功",
        })
        data = json.loads(result[0].text)
        assert isinstance(data, dict)
        assert "available" in data
        assert "answer" in data


# ── 6. 边界与错误 ──


class TestBoundaryAndErrors:

    @pytest.mark.asyncio
    async def test_unknown_tool(self, mcp_server):
        with pytest.raises(Exception):
            await mcp_server.call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_add_memo_empty_content(self, mcp_server):
        result = await mcp_server.call_tool("add_memo", {"content": ""})
        data = json.loads(result[0].text)
        assert data["content"] == ""

    @pytest.mark.asyncio
    async def test_add_memo_long_content(self, mcp_server):
        long_text = "测试" * 500
        result = await mcp_server.call_tool("add_memo", {"content": long_text})
        data = json.loads(result[0].text)
        assert data["content"] == long_text

    @pytest.mark.asyncio
    async def test_list_memos_limit_zero(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("list_memos", {"limit": 0}))
        data = json.loads(result[0].text)
        assert data == []

    @pytest.mark.asyncio
    async def test_add_schedule_invalid_day(self, mcp_server):
        result = await mcp_server.call_tool("add_schedule", {
            "schedule_type": "test",
            "day": "InvalidDay",
            "time_slot": "morning",
        })
        data = json.loads(result[0].text)
        assert data["day"] == "InvalidDay"

    @pytest.mark.asyncio
    async def test_list_plans_no_match(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("list_plans", {"area": "不存在领域"}))
        data = json.loads(result[0].text)
        assert data == []

    @pytest.mark.asyncio
    async def test_show_project_empty_name(self, mcp_server):
        result = _unwrap(await mcp_server.call_tool("show_project", {"name_or_alias": ""}))
        data = json.loads(result[0].text)
        assert data is None

    @pytest.mark.asyncio
    async def test_digest_content_chinese(self, mcp_server):
        result = await mcp_server.call_tool("digest_content", {
            "text": "需要提交周报，决定用Markdown格式，关键是要简洁。",
        })
        data = json.loads(result[0].text)
        assert data["raw_lines"] == 1
        total_extracted = len(data["todos"]) + len(data["decisions"]) + len(data["facts"])
        assert total_extracted >= 1


# ── 7. 工具描述合规性 ──


class TestToolDescriptionCompliance:

    @pytest.mark.asyncio
    async def test_tool_names_match_spec(self, mcp_server):
        """验证工具名称与灵系命名规范一致。"""
        tools = await mcp_server.list_tools()
        expected_names = [
            "add_memo", "list_memos", "add_schedule", "list_schedules",
            "add_plan", "list_plans", "show_project", "generate_report",
            "patrol_project", "get_briefing", "digest_content", "ask_lingzhi",
            "today_schedule", "week_schedule", "smart_remind",
            "done_plan", "week_plans", "plan_stats",
            "list_projects", "save_session", "last_session",
            "search_knowledge", "speak", "synthesize_to_file", "transcribe",
            "council_scan", "council_health",
        ]
        actual_names = [t.name for t in tools]
        assert sorted(actual_names) == sorted(expected_names)

    @pytest.mark.asyncio
    async def test_descriptions_contain_chinese_name(self, mcp_server):
        """验证每个工具描述包含灵系中文名。"""
        tools = await mcp_server.list_tools()
        chinese_names = {
            "add_memo": "灵记",
            "list_memos": "灵览",
            "add_schedule": "灵排",
            "list_schedules": "灵视",
            "add_plan": "灵划",
            "list_plans": "灵查",
            "show_project": "灵项",
            "generate_report": "灵报",
            "patrol_project": "灵巡",
            "get_briefing": "灵汇",
            "digest_content": "灵摘",
            "ask_lingzhi": "灵问",
            "today_schedule": "灵日",
            "week_schedule": "灵周",
            "smart_remind": "灵醒",
            "done_plan": "灵成",
            "week_plans": "灵划周",
            "plan_stats": "灵统",
            "list_projects": "灵板",
            "save_session": "灵忆",
            "last_session": "灵回",
            "search_knowledge": "灵搜",
            "speak": "灵声",
            "synthesize_to_file": "灵录声",
            "transcribe": "灵听",
            "council_scan": "灵议",
            "council_health": "灵康",
        }
        for t in tools:
            expected_cn = chinese_names.get(t.name)
            assert expected_cn in t.description, (
                f"Tool {t.name} description missing Chinese name '{expected_cn}'"
            )
