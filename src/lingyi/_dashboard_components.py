"""情报可视化仪表板 — HTML组件构建"""

import html as _html
import json
import logging
from typing import Dict, List

from .trends import TrendAnalyzer, TrendAnalysis

logger = logging.getLogger(__name__)


def _e(value) -> str:
    """HTML转义辅助函数"""
    return _html.escape(str(value))


def _format_change(trend: TrendAnalysis) -> str:
    """格式化变化显示"""
    if not trend or trend.previous == 0:
        return '<span class="metric-change neutral">无历史数据</span>'

    change = trend.change_percent
    sign = "+" if change >= 0 else ""
    css_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"

    return f'<span class="metric-change {css_class}">周环比 {sign}{change:.1f}%</span>'


def _build_status_cards(data: Dict, weekly_report) -> str:
    """构建状态卡片"""
    cards = []

    # 灵知
    lingzhi = data.get("lingzhi", {})
    available = lingzhi.get("available", False)
    queries = lingzhi.get("total_queries", 0)
    trend = weekly_report.metrics.get("灵知查询量")

    cards.append(f"""
        <div class="card">
            <div class="card-title">
                <span class="card-icon">🔮</span>
                灵知知识系统
                <span class="status-badge {'status-online' if available else 'status-offline'}">
                    {'在线' if available else '离线'}
                </span>
            </div>
            <div class="metric-value">{_e(queries)}</div>
            <div>累计查询</div>
            {_format_change(trend)}
        </div>
    """)

    # 灵通
    lingflow = data.get("lingflow", {})
    available = lingflow.get("available", False)
    feedbacks = lingflow.get("feedback_count", 0)
    trends = lingflow.get("github_trends", 0)
    daily = lingflow.get("daily_reports", 0)

    cards.append(f"""
        <div class="card">
            <div class="card-title">
                <span class="card-icon">🔧</span>
                灵通开发平台
                <span class="status-badge {'status-online' if available else 'status-offline'}">
                    {'在线' if available else '离线'}
                </span>
            </div>
            <div class="metric-value">{_e(feedbacks)}</div>
            <div>反馈 / 趋势报告: {_e(trends)} / 每日简报: {_e(daily)}</div>
        </div>
    """)

    # 灵克
    lingclaude = data.get("lingclaude", {})
    available = lingclaude.get("available", False)
    sessions = lingclaude.get("sessions", 0)

    cards.append(f"""
        <div class="card">
            <div class="card-title">
                <span class="card-icon">💻</span>
                灵克编程助手
                <span class="status-badge {'status-online' if available else 'status-offline'}">
                    {'在线' if available else '离线'}
                </span>
            </div>
            <div class="metric-value">{_e(sessions)}</div>
            <div>会话记录</div>
        </div>
    """)

    # 问道
    lingtongask = data.get("lingtongask", {})
    available = lingtongask.get("available", False)
    comments = lingtongask.get("total_comments", 0)
    users = lingtongask.get("unique_users", 0)
    sentiment = lingtongask.get("sentiment", {})
    positive = sentiment.get("positive", 0)
    negative = sentiment.get("negative", 0)

    cards.append(f"""
        <div class="card">
            <div class="card-title">
                <span class="card-icon">🎙️</span>
                灵通问道
                <span class="status-badge {'status-online' if available else 'status-offline'}">
                    {'在线' if available else '离线'}
                </span>
            </div>
            <div class="metric-value">{_e(comments)}</div>
            <div>评论 / 粉丝: {_e(comments)} / {_e(users)}</div>
            <div style="margin-top: 8px;">
                <span style="color: #28a745;">积极 {_e(positive)}</span> •
                <span style="color: #dc3545;">消极 {_e(negative)}</span>
            </div>
        </div>
    """)

    return "\n".join(cards)


def _build_lingzhi_chart(analyzer: TrendAnalyzer) -> str:
    """构建灵知趋势图表配置"""
    records = analyzer.load_history(days=30)

    labels = []
    data = []

    for r in records[-14:]:
        labels.append(r["_datetime"].strftime("%m-%d"))
        data.append(r.get("lingzhi", {}).get("total_queries", 0))

    return json.dumps({
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "查询量",
                "data": data,
                "borderColor": "#667eea",
                "backgroundColor": "rgba(102, 126, 234, 0.1)",
                "fill": True,
                "tension": 0.4
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False}},
            "scales": {"y": {"beginAtZero": True}}
        }
    })


def _build_comparison_chart(data: Dict) -> str:
    """构建平台对比图表配置"""
    return json.dumps({
        "type": "bar",
        "data": {
            "labels": ["灵知", "灵通", "灵克", "问道"],
            "datasets": [{
                "label": "当前值",
                "data": [
                    data.get("lingzhi", {}).get("total_queries", 0),
                    data.get("lingflow", {}).get("feedback_count", 0),
                    data.get("lingclaude", {}).get("sessions", 0),
                    data.get("lingtongask", {}).get("total_comments", 0),
                ],
                "backgroundColor": ["#667eea", "#f093fb", "#4facfe", "#43e97b"]
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False}}
        }
    })


def _build_sentiment_chart(data: Dict) -> str:
    """构建情感分布图表配置"""
    sentiment = data.get("lingtongask", {}).get("sentiment", {})
    return json.dumps({
        "type": "doughnut",
        "data": {
            "labels": ["积极", "中性", "消极"],
            "datasets": [{
                "data": [
                    sentiment.get("positive", 0),
                    sentiment.get("neutral", 0),
                    sentiment.get("negative", 0),
                ],
                "backgroundColor": ["#28a745", "#6c757d", "#dc3545"]
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"position": "bottom"}}
        }
    })


def _build_anomaly_list(anomalies: List[Dict]) -> str:
    """构建异常列表"""
    if not anomalies:
        return '<li style="background: #d4edda; border-color: #28a745;">✅ 未检测到异常数据</li>'

    items = []
    for a in anomalies:
        items.append(
            f"<li>{_e(a['metric'])}: {a['value']:.0f} "
            f"(预期: {_e(a['expected'])}, 偏差: {a['deviation']:.1f}σ)</li>"
        )
    return "\n".join(items)
