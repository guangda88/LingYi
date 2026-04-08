"""情报趋势分析 — 数据模型与格式化"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class TrendPoint:
    """趋势数据点"""
    timestamp: Any  # datetime
    value: float
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "label": self.label,
        }


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    metric: str
    current: float
    previous: float
    change: float
    change_percent: float
    trend: str  # up, down, stable
    data_points: List[TrendPoint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "current": self.current,
            "previous": self.previous,
            "change": self.change,
            "change_percent": self.change_percent,
            "trend": self.trend,
            "data_points": [p.to_dict() for p in self.data_points],
        }


@dataclass
class ComparisonReport:
    """对比报告"""
    period: str  # weekly, monthly
    start_date: str
    end_date: str
    previous_start: str
    previous_end: str
    metrics: Dict[str, TrendAnalysis] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "current_period": {
                "start": self.start_date,
                "end": self.end_date,
            },
            "previous_period": {
                "start": self.previous_start,
                "end": self.previous_end,
            },
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
        }

    def format_terminal(self) -> str:
        """格式化为终端输出"""
        lines = [
            f"📊 情报趋势分析 - {self._period_label()}对比",
            "=" * 50,
            "",
            f"📅 当前周期: {self.start_date} 至 {self.end_date}",
            f"📅 上期周期: {self.previous_start} 至 {self.previous_end}",
            "",
        ]

        for metric, analysis in self.metrics.items():
            trend_icon = {"up": "📈", "down": "📉", "stable": "➡️"}.get(analysis.trend, "❓")
            change_sign = "+" if analysis.change >= 0 else ""

            lines.append(f"{trend_icon} {metric}")
            lines.append(f"   当前: {analysis.current:.0f}")
            lines.append(f"   上期: {analysis.previous:.0f}")
            lines.append(f"   变化: {change_sign}{analysis.change:.0f} ({change_sign}{analysis.change_percent:.1f}%)")

        return "\n".join(lines)

    def _period_label(self) -> str:
        return {"weekly": "周", "monthly": "月"}.get(self.period, "")


def format_trend_summary(report: ComparisonReport) -> str:
    """格式化趋势摘要"""
    lines = [f"📊 {report._period_label()}趋势分析", "=" * 40]

    for metric, analysis in report.metrics.items():
        if analysis.current == 0 and analysis.previous == 0:
            continue

        trend_icon = {"up": "📈", "down": "📉", "stable": "➡️"}.get(analysis.trend, "❓")
        change_sign = "+" if analysis.change >= 0 else ""

        lines.append(f"{trend_icon} {metric}: {analysis.current:.0f} "
                    f"({change_sign}{analysis.change_percent:.1f}%)")

    return "\n".join(lines)
