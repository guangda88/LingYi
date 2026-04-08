"""情报可视化仪表板

生成 HTML 仪表板展示情报数据，包含:
- 实时数据展示
- 趋势图表
- 对比分析
- 异常检测
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from .briefing import collect_all
from .trends import TrendAnalyzer
from ._dashboard_components import (  # noqa: F401
    _build_status_cards,
    _build_lingzhi_chart,
    _build_comparison_chart,
    _build_sentiment_chart,
    _build_anomaly_list,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".lingyi" / "intelligence"
OUTPUT_DIR = DATA_DIR / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_template() -> str:
    """加载 HTML 模板"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>灵依情报仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .header .subtitle {
            font-size: 1rem;
            opacity: 0.9;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card-icon { font-size: 1.5rem; }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            margin: 10px 0;
        }
        .metric-change {
            font-size: 0.9rem;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
        }
        .metric-change.positive { background: #d4edda; color: #155724; }
        .metric-change.negative { background: #f8d7da; color: #721c24; }
        .metric-change.neutral { background: #e2e3e5; color: #383d41; }
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .chart-container h3 {
            margin-bottom: 15px;
            color: #333;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .status-online { background: #d4edda; color: #155724; }
        .status-offline { background: #f8d7da; color: #721c24; }
        .footer {
            text-align: center;
            color: white;
            opacity: 0.8;
            font-size: 0.9rem;
        }
        .anomaly-list {
            list-style: none;
        }
        .anomaly-list li {
            padding: 10px;
            margin-bottom: 8px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        .grid-2 { grid-template-columns: repeat(2, 1fr); }
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 灵依情报仪表板</h1>
            <p class="subtitle">灵字辈项目情报监控中心 • 更新时间: __UPDATE_TIME__</p>
        </div>

        <!-- 状态卡片 -->
        <div class="grid">
            __STATUS_CARDS__
        </div>

        <!-- 趋势图表 -->
        <div class="chart-container">
            <h3>📈 灵知查询量趋势</h3>
            <canvas id="lingzhiChart" height="100"></canvas>
        </div>

        <div class="grid grid-2">
            <div class="chart-container">
                <h3>📊 各平台指标对比</h3>
                <canvas id="comparisonChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>🎯 情感分布</h3>
                <canvas id="sentimentChart"></canvas>
            </div>
        </div>

        <!-- 异常检测 -->
        <div class="chart-container">
            <h3>⚠️ 异常检测</h3>
            <ul class="anomaly-list">
                __ANOMALY_LIST__
            </ul>
        </div>

        <div class="footer">
            <p>众智混元，万法灵通 • LingYi Intelligence Dashboard</p>
        </div>
    </div>

    <script>
        // 灵知趋势图
        new Chart(document.getElementById('lingzhiChart'), __CHART_LINGZHI__);

        // 平台对比图
        new Chart(document.getElementById('comparisonChart'), __CHART_COMPARISON__);

        // 情感分布图
        new Chart(document.getElementById('sentimentChart'), __CHART_SENTIMENT__);
    </script>
</body>
</html>
"""


def generate_dashboard(data: Dict = None) -> str:
    """生成仪表板 HTML"""
    if data is None:
        data = collect_all()

    analyzer = TrendAnalyzer()
    weekly_report = analyzer.analyze_weekly()
    anomalies = analyzer.detect_anomalies()

    status_cards = _build_status_cards(data, weekly_report)
    chart_lingzhi = _build_lingzhi_chart(analyzer)
    chart_comparison = _build_comparison_chart(data)
    chart_sentiment = _build_sentiment_chart(data)
    anomaly_list = _build_anomaly_list(anomalies)

    html = _load_template()
    html = html.replace("__UPDATE_TIME__", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    html = html.replace("__STATUS_CARDS__", status_cards)
    html = html.replace("__ANOMALY_LIST__", anomaly_list)
    html = html.replace("__CHART_LINGZHI__", chart_lingzhi)
    html = html.replace("__CHART_COMPARISON__", chart_comparison)
    html = html.replace("__CHART_SENTIMENT__", chart_sentiment)

    return html


def save_dashboard(output_path: Path = None) -> Path:
    """生成并保存仪表板"""
    if output_path is None:
        output_path = OUTPUT_DIR / "dashboard.html"

    html = generate_dashboard()

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"仪表板已保存: {output_path}")
    return output_path


def main():
    """CLI 入口"""
    output_path = save_dashboard()
    print(f"✅ 仪表板已生成: {output_path}")
    print(f"   在浏览器中打开: file://{output_path.absolute()}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
