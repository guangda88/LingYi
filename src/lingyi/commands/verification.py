"""验证约束层 CLI 命令"""

import click
import json


@click.group()
def verification():
    """约束层验证管理"""
    pass


@verification.command()
@click.argument("member_id")
@click.argument("assertion_type")
@click.argument("content")
@click.option("--tool", help="工具调用信息 (JSON格式)")
def check(member_id: str, assertion_type: str, content: str, tool: str | None):
    """验证断言是否符合约束

    MEMBER_ID: 成员ID (lingzhi/lingflow/lingresearch)
    ASSERTION_TYPE: 断言类型 (fact/action/communication)
    CONTENT: 断言内容
    """
    from ..constraint_layer import Assertion, ConstraintLayer

    constraint = ConstraintLayer()

    # 解析工具调用信息
    tool_call = None
    if tool:
        try:
            tool_call = json.loads(tool)
        except json.JSONDecodeError:
            click.echo(f"错误: 无效的JSON格式: {tool}")
            return

    # 构造断言
    assertion = Assertion(
        member_id=member_id,
        assertion_type=assertion_type,
        content=content,
        tool_call=tool_call
    )

    # 验证
    result = constraint.verify_assertion(assertion)

    # 输出结果
    if result.passed:
        click.echo("✅ 验证通过")
    else:
        click.echo("❌ 验证失败")

    click.echo(f"原因: {result.reason}")

    if result.recommendation:
        click.echo(f"建议: {result.recommendation}")

    # 显示检查详情
    click.echo("\n检查详情:")
    for check in result.checks:
        status = "✅" if check["passed"] else "❌"
        click.echo(f"  {status} {check['name']}: {check['reason']}")
        if "detail" in check:
            click.echo(f"     详情: {check['detail']}")


@verification.command()
@click.option("--days", default=7, help="统计天数")
def stats(days: int):
    """显示验证统计"""
    from ..constraint_layer import ConstraintLayer

    constraint = ConstraintLayer()
    stats = constraint.get_verification_stats(days)

    if not stats:
        click.echo("暂无验证记录")
        return

    click.echo(f"近{days}天验证统计:")
    click.echo(f"  总数: {stats['total']}")
    click.echo(f"  通过: {stats['approved']}")
    click.echo(f"  拒绝: {stats['rejected']}")
    click.echo(f"  降级: {stats['fallback']}")
    click.echo(f"  通过率: {stats['approval_rate']}%")

    if stats['by_member']:
        click.echo("\n按成员统计:")
        for member_id, member_stats in stats['by_member'].items():
            approval_rate = round(member_stats['approved'] / member_stats['total'] * 100, 1) if member_stats['total'] > 0 else 0
            click.echo(f"  {member_id}:")
            click.echo(f"    总数: {member_stats['total']}")
            click.echo(f"    通过: {member_stats['approved']}")
            click.echo(f"    拒绝: {member_stats['rejected']}")
            click.echo(f"    通过率: {approval_rate}%")


@verification.command()
@click.option("--days", default=7, help="查询天数")
@click.option("--member", help="按成员ID筛选")
@click.option("--limit", default=20, help="显示数量")
def log(days: int, member: str | None, limit: int):
    """显示验证日志"""
    from ..constraint_layer import VerificationMonitor
    from datetime import datetime

    monitor = VerificationMonitor()
    logs = monitor._load_logs()

    # 筛选时间范围
    cutoff = datetime.now().timestamp() - days * 86400
    recent_logs = [
        log for log in logs
        if datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff
    ]

    # 按成员ID筛选
    if member:
        recent_logs = [log for log in recent_logs if log["member_id"] == member]

    # 限制数量
    recent_logs = recent_logs[:limit]

    if not recent_logs:
        click.echo("暂无验证记录")
        return

    click.echo(f"近{days}天验证日志 (显示最近{limit}条):\n")

    for log in recent_logs:
        timestamp = log["timestamp"]
        member_id = log["member_id"]
        assertion_type = log["assertion_type"]
        content = log["assertion_content"]
        result = log["verification_result"]
        action = log["action_taken"]

        # 状态图标
        status_map = {
            "approved": "✅",
            "rejected": "❌",
            "fallback": "⚠️"
        }
        status = status_map.get(action, "❓")

        click.echo(f"{status} [{timestamp}] {member_id} ({assertion_type})")
        click.echo(f"   内容: {content}")
        if not result["passed"]:
            click.echo(f"   失败原因: {result['reason']}")
        click.echo()


def register(group: click.Group):
    """注册验证命令到Click组"""
    verification_cmd = verification
    group.add_command(verification_cmd, name="verify")
