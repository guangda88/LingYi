"""灵信签署 MCP Server — 消息发送/回复/关闭。

写操作 server，用于向灵信系统发送新消息、回复讨论、关闭讨论。
"""

from __future__ import annotations

import dataclasses

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="lingmessage-signing",
    instructions="灵信签署 Server — 发送/回复/关闭灵信消息",
)


def _to_dict(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj


@mcp.tool(name="send_message", description="发送灵信消息，自动匹配已有讨论或创建新讨论")
def tool_send_message(
    from_id: str,
    topic: str,
    content: str,
    reply_to: str | None = None,
    tags: list[str] | None = None,
    source_type: str = "real",
) -> dict:
    """发送灵信消息。

    Args:
        from_id: 项目ID (lingflow/lingclaude/lingzhi/lingyi/lingtongask/lingterm/lingminopt/lingresearch/zhibridge/lingyang/guangda)
        topic: 讨论主题
        content: 消息正文
        reply_to: 回复的消息ID（可选）
        tags: 标签列表（可选）
        source_type: real/inferred/unverifiable，默认 real
    """
    from lingyi.lingmessage import send_message as _send

    msg = _send(
        from_id=from_id,
        topic=topic,
        content=content,
        reply_to=reply_to,
        tags=tags,
        source_type=source_type,
    )
    return _to_dict(msg)


@mcp.tool(name="reply_message", description="回复已有灵信讨论")
def tool_reply_message(
    discussion_id: str,
    from_id: str,
    content: str,
    reply_to: str | None = None,
    tags: list[str] | None = None,
    source_type: str = "real",
) -> dict | None:
    """回复已有讨论。讨论必须处于 open 状态。

    Args:
        discussion_id: 讨论ID (disc_YYYYMMDDHHMMSS)
        from_id: 项目ID
        content: 回复内容
        reply_to: 回复的消息ID（可选）
        tags: 标签列表（可选）
        source_type: real/inferred/unverifiable，默认 real
    """
    from lingyi.lingmessage import reply_to_discussion

    result = reply_to_discussion(
        discussion_id=discussion_id,
        from_id=from_id,
        content=content,
        reply_to=reply_to,
        tags=tags,
        source_type=source_type,
    )
    return _to_dict(result) if result else None


@mcp.tool(name="close_discussion", description="关闭灵信讨论，关闭后不可再回复")
def tool_close_discussion(discussion_id: str) -> dict:
    """关闭讨论。

    Args:
        discussion_id: 讨论ID
    """
    from lingyi.lingmessage import close_discussion

    success = close_discussion(discussion_id)
    return {"discussion_id": discussion_id, "status": "closed" if success else "not_found"}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
