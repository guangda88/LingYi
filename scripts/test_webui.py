#!/usr/bin/env python3
"""灵依WebUI完整性测试脚本

测试所有页面、API和JavaScript功能。

使用方法:
    python scripts/test_webui.py              # 完整测试
    python scripts/test_webui.py --api-only   # 仅测试API
    python scripts/test_webui.py --pages-only  # 仅测试页面
"""

import argparse
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests

requests.packages.urllib3.disable_warnings()

BASE_URL = "https://100.66.1.8:8900"


def test_api_endpoints():
    """测试所有API端点"""
    print("=" * 60)
    print("API端点测试")
    print("=" * 60)

    endpoints = {
        '首页HTML': '/',
        '仪表盘': '/api/dashboard',
        '讨论列表': '/api/lingmessage?status=open',
        '讨论详情': '/api/lingmessage/disc_20260407054555',
        '日程': '/api/schedules',
        '备忘': '/api/memos',
        '项目': '/api/projects',
        '模型': '/api/models',
        '偏好': '/api/preferences',
        '简报': '/api/briefing',
        '状态': '/api/status',
        '使用情况': '/api/usage',
        '日志': '/api/logs?source=灵依&lines=5',
        'council状态': '/api/council/status',
    }

    results = []
    for name, path in endpoints.items():
        try:
            url = f"{BASE_URL}{path}"
            r = requests.get(url, timeout=10, verify=False)
            if r.status_code == 200:
                print(f"✅ {name:20s} - OK ({len(r.text)} bytes)")
                results.append((name, True, None))
            else:
                print(f"❌ {name:20s} - {r.status_code}")
                results.append((name, False, f"HTTP {r.status_code}"))
        except Exception as e:
            print(f"❌ {name:20s} - ERROR: {str(e)[:40]}")
            results.append((name, False, str(e)))

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nAPI测试: {passed}/{len(results)} 通过\n")
    return results


def test_page_elements():
    """检查HTML页面元素"""
    print("=" * 60)
    print("页面元素检查")
    print("=" * 60)

    try:
        r = requests.get(BASE_URL, timeout=10, verify=False)
        html = r.text
    except Exception as e:
        print(f"❌ 无法获取首页HTML: {e}")
        return []

    # 检查关键元素
    elements = {
        "导航按钮": 'onclick="switchPage',
        "首页": 'id="pgHome"',
        "议事厅": 'id="pgCouncil"',
        "对话": 'id="pgChat"',
        "日程": 'id="pgSched"',
        "备忘": 'id="pgMemo"',
        "项目": 'id="pgProjects"',
        "模型": 'id="pgModels"',
        "日志": 'id="pgLogs"',
        "switchPage函数": 'function switchPage',
        "loadDashboard函数": 'function loadDashboard',
        "loadCouncil函数": 'function loadCouncil',
        "loadSchedules函数": 'function loadSchedules',
        "loadMemos函数": 'function loadMemos',
        "loadProjects函数": 'function loadProjects',
        "loadModels函数": 'function loadModels',
        "loadLogs函数": 'function loadLogs',
    }

    results = []
    for name, selector in elements.items():
        if selector in html:
            print(f"✅ {name:20s} - 存在")
            results.append((name, True, None))
        else:
            print(f"❌ {name:20s} - 缺失")
            results.append((name, False, "未找到"))

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n页面元素: {passed}/{len(results)} 通过\n")
    return results


def test_data_integrity():
    """测试数据完整性"""
    print("=" * 60)
    print("数据完整性测试")
    print("=" * 60)

    results = []

    # 测试仪表盘数据
    try:
        r = requests.get(f"{BASE_URL}/api/dashboard", timeout=10, verify=False)
        data = r.json()
        required_keys = ['date', 'weekday', 'today_schedules', 'recent_memos',
                        'active_projects', 'ling_family']
        missing = [k for k in required_keys if k not in data]
        if not missing:
            print(f"✅ 仪表盘数据 - 完整")
            results.append(("仪表盘数据", True, None))
        else:
            print(f"❌ 仪表盘数据 - 缺失: {missing}")
            results.append(("仪表盘数据", False, f"缺少字段: {missing}"))
    except Exception as e:
        print(f"❌ 仪表盘数据 - ERROR: {e}")
        results.append(("仪表盘数据", False, str(e)))

    # 测试讨论数据
    try:
        r = requests.get(f"{BASE_URL}/api/lingmessage?status=open", timeout=10, verify=False)
        data = r.json()
        if isinstance(data, list):
            print(f"✅ 讨论数据 - {len(data)} 条")
            results.append(("讨论数据", True, None))
        else:
            print(f"❌ 讨论数据 - 格式错误")
            results.append(("讨论数据", False, "不是列表"))
    except Exception as e:
        print(f"❌ 讨论数据 - ERROR: {e}")
        results.append(("讨论数据", False, str(e)))

    # 测试项目数据
    try:
        r = requests.get(f"{BASE_URL}/api/projects", timeout=10, verify=False)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            print(f"✅ 项目数据 - {len(data)} 个")
            results.append(("项目数据", True, None))
        else:
            print(f"❌ 项目数据 - 为空")
            results.append(("项目数据", False, "数据为空"))
    except Exception as e:
        print(f"❌ 项目数据 - ERROR: {e}")
        results.append(("项目数据", False, str(e)))

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n数据完整性: {passed}/{len(results)} 通过\n")
    return results


def test_specific_pages():
    """测试特定页面的问题"""
    print("=" * 60)
    print("特定页面测试")
    print("=" * 60)

    results = []

    # 测试模型页面
    try:
        r = requests.get(f"{BASE_URL}/api/models", timeout=10, verify=False)
        data = r.json()
        if isinstance(data, dict):
            models = [k for k in data.keys() if k != '_meta']
            print(f"✅ 模型页面 - {len(models)} 个模型")
            for model in models[:5]:
                print(f"   - {model}")
            results.append(("模型页面", True, None))
        else:
            print(f"❌ 模型页面 - 数据格式错误")
            results.append(("模型页面", False, "数据格式错误"))
    except Exception as e:
        print(f"❌ 模型页面 - ERROR: {e}")
        results.append(("模型页面", False, str(e)))

    # 测试日志页面
    try:
        r = requests.get(f"{BASE_URL}/api/logs?source=灵依&lines=5", timeout=10, verify=False)
        data = r.json()
        if 'lines' in data and 'sources' in data:
            print(f"✅ 日志页面 - {len(data.get('lines', []))} 行日志")
            results.append(("日志页面", True, None))
        else:
            print(f"❌ 日志页面 - 数据格式错误")
            results.append(("日志页面", False, "数据格式错误"))
    except Exception as e:
        print(f"❌ 日志页面 - ERROR: {e}")
        results.append(("日志页面", False, str(e)))

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n特定页面: {passed}/{len(results)} 通过\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="灵依WebUI完整性测试")
    parser.add_argument("--api-only", action="store_true", help="仅测试API")
    parser.add_argument("--pages-only", action="store_true", help="仅测试页面元素")
    parser.add_argument("--url", default="https://100.66.1.8:8900", help="WebUI地址")

    args = parser.parse_args()
    global BASE_URL
    BASE_URL = args.url

    print(f"测试目标: {BASE_URL}")
    print()

    all_results = []

    if args.api_only:
        all_results.extend(test_api_endpoints())
    elif args.pages_only:
        all_results.extend(test_page_elements())
    else:
        all_results.extend(test_api_endpoints())
        all_results.extend(test_page_elements())
        all_results.extend(test_data_integrity())
        all_results.extend(test_specific_pages())

    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, ok, _ in all_results if ok)
    total = len(all_results)

    for name, ok, error in all_results:
        status = "✅" if ok else "❌"
        print(f"{status} {name:20s} - {'通过' if ok else '失败'}")
        if error and not ok:
            print(f"   错误: {error}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！WebUI工作正常。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要修复。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
