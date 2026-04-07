"""灵信总线 MCP Server — 跨项目通信骨干。

只读浏览 server，列出讨论、读取内容、查看项目身份、系统统计。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="lingmessage-bus",
    instructions="灵信总线 Server — 浏览/读取/统计灵信系统",
)


@mcp.tool(name="list_discussions", description="列出灵信讨论，按更新时间倒序")
def tool_list_discussions(status: str = "") -> dict:
    """列出所有讨论，返回摘要索引。

    Args:
        status: 筛选状态 — open/closed，留空返回全部
    """
    from lingyi.lingmessage import list_discussions

    results = list_discussions(status=status or None)
    open_count = sum(1 for d in results if d.get("status") == "open")
    closed_count = sum(1 for d in results if d.get("status") == "closed")
    return {
        "total": len(results),
        "open": open_count,
        "closed": closed_count,
        "discussions": results,
    }


@mcp.tool(name="read_discussion", description="读取完整讨论内容，包含所有消息和回复关系")
def tool_read_discussion(discussion_id: str) -> dict | None:
    """读取完整讨论线程。

    Args:
        discussion_id: 讨论ID (disc_YYYYMMDDHHMMSS)
    """
    from lingyi.lingmessage import read_discussion

    return read_discussion(discussion_id)


@mcp.tool(name="init_store", description="初始化灵信存储（幂等操作，已存在时不覆盖）")
def tool_init_store() -> dict:
    """初始化灵信存储目录结构。"""
    from lingyi.lingmessage import init_store

    return init_store()


@mcp.tool(name="list_projects", description="列出灵字辈大家庭所有注册项目及其身份")
def tool_list_projects() -> dict:
    """列出灵字辈大家庭所有成员。"""
    from lingyi.lingmessage import PROJECTS

    projects = [
        {"id": pid, "name": info["name"], "role": info["role"]}
        for pid, info in PROJECTS.items()
    ]
    return {"total": len(projects), "projects": projects}


@mcp.tool(name="get_stats", description="获取灵信系统统计信息")
def tool_get_stats() -> dict:
    """获取讨论数、消息数、活跃参与者、最新活动等统计。"""
    from lingyi.lingmessage import list_discussions

    discussions = list_discussions()
    open_count = sum(1 for d in discussions if d.get("status") == "open")
    closed_count = sum(1 for d in discussions if d.get("status") == "closed")
    total_messages = sum(d.get("message_count", 0) for d in discussions)

    participant_counts: dict[str, int] = {}
    latest_activity = ""
    for d in discussions:
        for p in d.get("participants", []):
            participant_counts[p] = participant_counts.get(p, 0) + 1
        updated = d.get("updated_at", "")
        if updated > latest_activity:
            latest_activity = updated

    active = dict(
        sorted(participant_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    return {
        "total_discussions": len(discussions),
        "open_discussions": open_count,
        "closed_discussions": closed_count,
        "total_messages": total_messages,
        "active_participants": active,
        "latest_activity": latest_activity,
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
