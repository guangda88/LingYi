"""灵信标注 MCP Server — 搜索/异常检测/自动标注。

只读分析 server，用于搜索消息、检测时间异常、自动标注消息真实性。
"""

from __future__ import annotations

import dataclasses

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="lingmessage-annotate",
    instructions="灵信标注 Server — 搜索/异常检测/自动标注灵信消息",
)


def _to_dict(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj


@mcp.tool(name="search_messages", description="搜索灵信消息，跨所有讨论全文检索")
def tool_search_messages(keyword: str) -> dict:
    """跨所有讨论搜索消息，返回匹配列表。

    Args:
        keyword: 搜索关键词（不区分大小写）
    """
    from lingyi.lingmessage import search_messages

    results = search_messages(keyword)
    return {
        "keyword": keyword,
        "total_matches": len(results),
        "results": results,
    }


@mcp.tool(name="detect_anomalies", description="检测讨论中的时间异常（不同发送者在极短时间内发消息）")
def tool_detect_anomalies(
    discussion_id: str,
    threshold_seconds: float = 2.0,
) -> dict:
    """检测讨论中的时间异常。

    当不同成员在极短时间内（默认2秒）连续发言时，标记为异常，
    可能是 AI 推演而非真实交互。

    Args:
        discussion_id: 讨论ID (disc_YYYYMMDDHHMMSS)
        threshold_seconds: 时间异常阈值（秒），默认2.0
    """
    from lingyi.lingmessage import detect_temporal_anomalies, read_discussion

    disc = read_discussion(discussion_id)
    if not disc:
        return {"error": f"讨论 {discussion_id} 不存在"}

    anomalies = detect_temporal_anomalies(disc, threshold_seconds=threshold_seconds)
    return {
        "discussion_id": discussion_id,
        "total_messages": len(disc.get("messages", [])),
        "anomaly_count": len(anomalies),
        "anomalies": [
            {"index": idx, "description": desc}
            for idx, desc in anomalies
        ],
    }


@mcp.tool(name="annotate_discussion", description="自动标注讨论中消息的 source_type（real/inferred/unverifiable）")
def tool_annotate_discussion(discussion_id: str) -> dict:
    """自动标注讨论消息的真实性。

    基于时间异常和 auto_reply 标签判断消息 source_type。
    会修改磁盘上的讨论数据。

    Args:
        discussion_id: 讨论ID
    """
    from lingyi.lingmessage import annotate_discussion

    return annotate_discussion(discussion_id)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
