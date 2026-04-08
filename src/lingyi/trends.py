"""情报趋势分析模块

提供历史数据的趋势分析功能:
- 周/月对比
- 增长率计算
- 异常检测
- 趋势预测
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from ._trends_models import TrendPoint, TrendAnalysis, ComparisonReport, format_trend_summary  # noqa: F401

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".lingyi" / "intelligence"
HISTORY_FILE = DATA_DIR / "history.jsonl"


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file

    def load_history(self, days: int = 90) -> List[Dict]:
        """加载历史记录"""
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

        current_end = now
        current_start = week_start

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

        current_end = now
        current_start = month_start

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
        """对比两个时间周期"""
        records = self.load_history()

        current_records = [
            r for r in records
            if previous_end < r["_datetime"] <= current_end
        ]
        previous_records = [
            r for r in records
            if previous_start <= r["_datetime"] <= previous_end
        ]

        metrics = {}

        metrics["灵知查询量"] = self._analyze_metric(
            records, current_records, previous_records, "lingzhi.total_queries"
        )
        metrics["灵知错误"] = self._analyze_metric(
            records, current_records, previous_records, "lingzhi.errors"
        )
        metrics["灵通反馈"] = self._analyze_metric(
            records, current_records, previous_records, "lingflow.feedback_count"
        )
        metrics["灵通趋势报告"] = self._analyze_metric(
            records, current_records, previous_records, "lingflow.github_trends"
        )
        metrics["灵克会话"] = self._analyze_metric(
            records, current_records, previous_records, "lingclaude.sessions"
        )
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
        """分析单个指标"""
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

        current_values = [get_value(r) for r in current_records]
        previous_values = [get_value(r) for r in previous_records]

        current = max(current_values) if current_values else 0.0
        previous = max(previous_values) if previous_values else 0.0

        change = current - previous
        change_percent = (change / previous * 100) if previous > 0 else 0.0

        if change_percent > 5:
            trend = "up"
        elif change_percent < -5:
            trend = "down"
        else:
            trend = "stable"

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
            data_points=data_points[-30:],
        )

    def detect_anomalies(self, threshold: float = 2.0) -> List[Dict]:
        """检测异常数据点"""
        records = self.load_history(days=30)
        anomalies = []

        metrics = [
            ("lingzhi.total_queries", "灵知查询量"),
            ("lingflow.feedback_count", "灵通反馈"),
            ("lingtongask.total_comments", "问道评论"),
        ]

        for path, name in metrics:
            parts = path.split(".")

            values = []
            for r in records:
                v = r
                for part in parts:
                    if isinstance(v, dict):
                        v = v.get(part, 0)
                values.append(float(v))

            if not values or all(v == 0 for v in values):
                continue

            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5

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
