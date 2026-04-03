"""情报趋势分析模块

提供历史数据的趋势分析功能:
- 周/月对比
- 增长率计算
- 异常检测
- 趋势预测
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = Path.home() / ".lingyi" / "intelligence"
HISTORY_FILE = DATA_DIR / "history.jsonl"


@dataclass
class TrendPoint:
    """趋势数据点"""
    timestamp: datetime
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


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file

    def load_history(self, days: int = 90) -> List[Dict]:
        """加载历史记录

        Args:
            days: 加载最近多少天的记录

        Returns:
            历史记录列表
        """
        if not self.history_file.exists():
            logger.warning(f"历史记录文件不存在: {self.history_file}")
            return []

        records = []
        cutoff = datetime.now() - timedelta(days=days)

        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    ts = datetime.fromisoformat(record["timestamp"])
                    if ts > cutoff:
                        record["_datetime"] = ts
                        records.append(record)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.debug(f"跳过无效记录: {e}")
                    continue

        return sorted(records, key=lambda r: r["_datetime"])

    def analyze_weekly(self) -> ComparisonReport:
        """生成周对比报告"""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # 当前周
        current_end = now
        current_start = week_start

        # 上周
        previous_start = current_start - timedelta(weeks=1)
        previous_end = current_start

        return self._compare_periods(
            current_start, current_end,
            previous_start, previous_end,
            "weekly"
        )

    def analyze_monthly(self) -> ComparisonReport:
        """生成月对比报告"""
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 当前月
        current_end = now
        current_start = month_start

        # 上月 (需要计算上个月的天数)
        if month_start.month == 1:
            previous_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            previous_start = month_start.replace(month=month_start.month - 1)
        previous_end = month_start

        return self._compare_periods(
            current_start, current_end,
            previous_start, previous_end,
            "monthly"
        )

    def _compare_periods(
        self,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        period: str
    ) -> ComparisonReport:
        """对比两个时间周期

        Args:
            current_start: 当前周期开始
            current_end: 当前周期结束
            previous_start: 上期周期开始
            previous_end: 上期周期结束
            period: 周期类型

        Returns:
            对比报告
        """
        records = self.load_history()

        # 筛选记录
        current_records = [
            r for r in records
            if previous_end < r["_datetime"] <= current_end
        ]
        previous_records = [
            r for r in records
            if previous_start <= r["_datetime"] <= previous_end
        ]

        # 计算指标
        metrics = {}

        # 灵知指标
        metrics["灵知查询量"] = self._analyze_metric(
            records, current_records, previous_records, "lingzhi.total_queries"
        )
        metrics["灵知错误"] = self._analyze_metric(
            records, current_records, previous_records, "lingzhi.errors"
        )

        # 灵通指标
        metrics["灵通反馈"] = self._analyze_metric(
            records, current_records, previous_records, "lingflow.feedback_count"
        )
        metrics["灵通趋势报告"] = self._analyze_metric(
            records, current_records, previous_records, "lingflow.github_trends"
        )

        # 灵克指标
        metrics["灵克会话"] = self._analyze_metric(
            records, current_records, previous_records, "lingclaude.sessions"
        )

        # 问道指标
        metrics["问道评论"] = self._analyze_metric(
            records, current_records, previous_records, "lingtongask.total_comments"
        )
        metrics["问道粉丝"] = self._analyze_metric(
            records, current_records, previous_records, "lingtongask.unique_users"
        )

        return ComparisonReport(
            period=period,
            start_date=current_start.strftime("%Y-%m-%d"),
            end_date=current_end.strftime("%Y-%m-%d"),
            previous_start=previous_start.strftime("%Y-%m-%d"),
            previous_end=previous_end.strftime("%Y-%m-%d"),
            metrics=metrics,
        )

    def _analyze_metric(
        self,
        all_records: List[Dict],
        current_records: List[Dict],
        previous_records: List[Dict],
        path: str
    ) -> TrendAnalysis:
        """分析单个指标

        Args:
            all_records: 所有记录
            current_records: 当前周期记录
            previous_records: 上期周期记录
            path: 指标路径 (如 "lingzhi.total_queries")

        Returns:
            趋势分析结果
        """
        # 解析路径
        parts = path.split(".")
        metric_name = parts[-1]

        def get_value(record: Dict) -> float:
            value = record
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, 0)
                else:
                    return 0.0
            return float(value) if isinstance(value, (int, float)) else 0.0

        # 计算当前值和上期值
        current_values = [get_value(r) for r in current_records]
        previous_values = [get_value(r) for r in previous_records]

        current = max(current_values) if current_values else 0.0
        previous = max(previous_values) if previous_values else 0.0

        # 计算变化
        change = current - previous
        change_percent = (change / previous * 100) if previous > 0 else 0.0

        # 判断趋势
        if change_percent > 5:
            trend = "up"
        elif change_percent < -5:
            trend = "down"
        else:
            trend = "stable"

        # 构建数据点
        data_points = []
        for r in all_records:
            v = get_value(r)
            if v > 0:
                data_points.append(TrendPoint(
                    timestamp=r["_datetime"],
                    value=v,
                    label=r["_datetime"].strftime("%m-%d")
                ))

        return TrendAnalysis(
            metric=metric_name,
            current=current,
            previous=previous,
            change=change,
            change_percent=change_percent,
            trend=trend,
            data_points=data_points[-30:],  # 保留最近30个点
        )

    def detect_anomalies(self, threshold: float = 2.0) -> List[Dict]:
        """检测异常数据点

        Args:
            threshold: 标准差倍数阈值

        Returns:
            异常点列表
        """
        records = self.load_history(days=30)
        anomalies = []

        # 分析每个指标
        metrics = [
            ("lingzhi.total_queries", "灵知查询量"),
            ("lingflow.feedback_count", "灵通反馈"),
            ("lingtongask.total_comments", "问道评论"),
        ]

        for path, name in metrics:
            parts = path.split(".")

            # 提取数据
            values = []
            for r in records:
                v = r
                for part in parts:
                    if isinstance(v, dict):
                        v = v.get(part, 0)
                values.append(float(v))

            if not values or all(v == 0 for v in values):
                continue

            # 计算统计量
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5

            # 检测异常
            for i, r in enumerate(records):
                v = values[i]
                if std > 0 and abs(v - mean) > threshold * std:
                    anomalies.append({
                        "metric": name,
                        "timestamp": r["timestamp"],
                        "value": v,
                        "expected": f"{mean:.0f} ± {std:.0f}",
                        "deviation": (v - mean) / std if std > 0 else 0,
                    })

        return anomalies


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
