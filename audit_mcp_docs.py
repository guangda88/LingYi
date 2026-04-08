"""灵通审计脚本

对灵字辈MCP评估报告进行全面审计
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加灵通MCP服务器路径
sys.path.insert(0, "/home/ai/LingFlow/mcp_server")


async def audit_documentation():
    """审计文档"""
    from lingflow_mcp import create_server

    # 创建服务器实例
    server = create_server()

    # 文档路径
    doc1 = "/home/ai/LingYi/docs/LING_FAMILY_MCP_ASSESSMENT.md"
    doc2 = "/home/ai/LingYi/docs/LING_FAMILY_MCP_BIDIRECTIONAL_INTEGRATION.md"

    print("=" * 80)
    print("灵通审计：灵字辈MCP评估报告")
    print("=" * 80)
    print()

    # 1. 文档1审计
    print("📋 正在审计: LING_FAMILY_MCP_ASSESSMENT.md")
    print("-" * 80)

    result1 = await server._execute_tool(
        "review_code",
        {
            "target_path": doc1,
            "dimensions": ["documentation", "style", "complexity"],
            "auto_fix": False
        }
    )

    if result1.get("success"):
        report1 = result1.get("report", {})
        print(f"✅ 审计完成")
        print(f"   - 目标: {result1.get('target')}")
        if "overall_score" in report1:
            print(f"   - 总体评分: {report1['overall_score']}/100")
        if "issues" in report1:
            print(f"   - 发现问题: {len(report1['issues'])} 个")
    else:
        print(f"❌ 审计失败: {result1.get('error', 'Unknown error')}")

    print()

    # 2. 文档2审计
    print("📋 正在审计: LING_FAMILY_MCP_BIDIRECTIONAL_INTEGRATION.md")
    print("-" * 80)

    result2 = await server._execute_tool(
        "review_code",
        {
            "target_path": doc2,
            "dimensions": ["documentation", "style", "complexity"],
            "auto_fix": False
        }
    )

    if result2.get("success"):
        report2 = result2.get("report", {})
        print(f"✅ 审计完成")
        print(f"   - 目标: {result2.get('target')}")
        if "overall_score" in report2:
            print(f"   - 总体评分: {report2['overall_score']}/100")
        if "issues" in report2:
            print(f"   - 发现问题: {len(report2['issues'])} 个")
    else:
        print(f"❌ 审计失败: {result2.get('error', 'Unknown error')}")

    print()

    # 3. 生成综合审计报告
    print("=" * 80)
    print("审计摘要")
    print("=" * 80)
    print()

    # 文档1摘要
    if result1.get("success") and "report" in result1:
        print("📄 文档1: LING_FAMILY_MCP_ASSESSMENT.md")
        report1 = result1["report"]
        if "overall_score" in report1:
            score = report1["overall_score"]
            if score >= 90:
                status = "🟢 优秀"
            elif score >= 75:
                status = "🟡 良好"
            else:
                status = "🔴 需要改进"
            print(f"   评分: {score}/100 {status}")

        if "dimension_scores" in report1:
            print("   维度评分:")
            for dim, score in report1["dimension_scores"].items():
                print(f"     - {dim}: {score}/100")

        if "issues" in report1 and report1["issues"]:
            print(f"   主要问题 ({len(report1['issues'])} 个):")
            for i, issue in enumerate(report1["issues"][:5], 1):
                print(f"     {i}. {issue.get('description', 'N/A')}")

    print()

    # 文档2摘要
    if result2.get("success") and "report" in result2:
        print("📄 文档2: LING_FAMILY_MCP_BIDIRECTIONAL_INTEGRATION.md")
        report2 = result2["report"]
        if "overall_score" in report2:
            score = report2["overall_score"]
            if score >= 90:
                status = "🟢 优秀"
            elif score >= 75:
                status = "🟡 良好"
            else:
                status = "🔴 需要改进"
            print(f"   评分: {score}/100 {status}")

        if "dimension_scores" in report2:
            print("   维度评分:")
            for dim, score in report2["dimension_scores"].items():
                print(f"     - {dim}: {score}/100")

        if "issues" in report2 and report2["issues"]:
            print(f"   主要问题 ({len(report2['issues'])} 个):")
            for i, issue in enumerate(report2["issues"][:5], 1):
                print(f"     {i}. {issue.get('description', 'N/A')}")

    print()

    # 4. 保存详细报告
    output_file = Path("/tmp/lingyi_mcp_audit_report.json")
    audit_report = {
        "timestamp": "2026-04-07",
        "documents": {
            "LING_FAMILY_MCP_ASSESSMENT.md": result1,
            "LING_FAMILY_MCP_BIDIRECTIONAL_INTEGRATION.md": result2
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, ensure_ascii=False, indent=2)

    print(f"💾 详细审计报告已保存到: {output_file}")
    print()

    # 5. 总结
    print("=" * 80)
    print("审计总结")
    print("=" * 80)
    print()

    if result1.get("success") and result2.get("success"):
        report1 = result1.get("report", {})
        report2 = result2.get("report", {})
        score1 = report1.get("overall_score", 0)
        score2 = report2.get("overall_score", 0)
        avg_score = (score1 + score2) / 2

        print(f"📊 整体评分: {avg_score:.1f}/100")
        print()

        if avg_score >= 85:
            print("🎉 审计通过！文档质量优秀，可以继续推进MCP集成计划。")
        elif avg_score >= 70:
            print("✅ 审计通过！文档质量良好，建议在推进前修复一些小问题。")
        else:
            print("⚠️  审计警告！文档质量需要改进，建议在推进前完成修复。")

    else:
        print("❌ 审计未完成！请检查错误信息并重试。")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(audit_documentation())
