"""Agent 工具 JSON Schema 定义 — function calling 参数声明"""

from __future__ import annotations

_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "check_github",
            "description": "查询 GitHub 仓库信息：stars、forks、issues、最新 release。输入格式：owner/repo（如 guangda88/lingflow）",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub 仓库全名，格式 owner/repo",
                    }
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_pypi",
            "description": "查询 PyPI 包的版本和下载量信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string",
                        "description": "PyPI 包名（如 lingflow-core）",
                    }
                },
                "required": ["package"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_memos",
            "description": "列出最近的备忘录",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_memo",
            "description": "添加一条备忘录",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "备忘内容",
                    }
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_schedule",
            "description": "查看今日或本周日程安排",
            "parameters": {
                "type": "object",
                "properties": {
                    "range": {
                        "type": "string",
                        "enum": ["today", "week"],
                        "description": "查看范围：today 或 week",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_plans",
            "description": "查看计划列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "领域筛选（医疗/编程/研究/论文/学术），空字符串表示全部",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "查看灵字辈项目列表和状态",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_briefing",
            "description": "收集灵字辈生态实时状态（灵知/灵通/灵克/灵通问道的服务状态、数据统计）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lingmessage",
            "description": "查看灵信中最近的讨论线程",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "closed"],
                        "description": "筛选状态：open 或 closed，空字符串表示全部",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_lingmessage",
            "description": "读取灵信中某个讨论的完整内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_id": {
                        "type": "string",
                        "description": "讨论 ID",
                    }
                },
                "required": ["discussion_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "搜索网络获取最新信息（AI新闻、技术动态等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patrol_projects",
            "description": "巡检所有灵字辈 Git 项目的状态（最近提交、未暂存变更、分支）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
