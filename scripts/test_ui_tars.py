#!/usr/bin/env python3
"""UI-TARS功能测试脚本

测试LingYi集成的UI-TARS视觉-操作闭环能力。

使用方法:
    python scripts/test_ui_tars.py              # 测试所有功能
    python scripts/test_ui_tars.py --screenshot # 仅测试截图
    python scripts/test_ui_tars.py --ocr        # 仅测试OCR
    python scripts/test_ui_tars.py --find       # 仅测试元素查找
"""

import argparse
import os
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_status():
    """测试UI-TARS服务状态"""
    print("=" * 50)
    print("测试1: UI-TARS服务状态")
    print("=" * 50)

    try:
        from lingyi.ui_tars import get_status
        status = get_status()

        print(f"启用: {'是' if status['enabled'] else '否'}")
        print(f"可用: {'是' if status['available'] else '否'}")
        print(f"API地址: {status['api_url']}")
        if status.get('version'):
            print(f"版本: {status['version']}")

        if status['enabled'] and not status['available']:
            print("\n⚠️ UI功能已启用但服务不可用")
            print("   请确保UI-TARS服务正在运行")
            return False

        return status['available']

    except Exception as e:
        print(f"❌ 状态查询失败: {e}")
        return False


def test_capture(url: str = "https://www.baidu.com"):
    """测试网页截图"""
    print("\n" + "=" * 50)
    print("测试2: 网页截图")
    print("=" * 50)

    try:
        from lingyi.ui_tars import capture_screenshot

        print(f"正在截图: {url}")
        result = capture_screenshot(url, width=1280, height=720)

        if result['success']:
            print(f"✅ 截图成功")
            print(f"   保存路径: {result['image_path']}")
            print(f"   尺寸: {result['width']}x{result['height']}")
            print(f"   时间戳: {result['timestamp']}")
            return result['image_path']
        else:
            print(f"❌ 截图失败")
            return None

    except Exception as e:
        print(f"❌ 截图失败: {e}")
        return None


def test_ocr(image_path: str | None = None):
    """测试OCR识别"""
    print("\n" + "=" * 50)
    print("测试3: OCR识别")
    print("=" * 50)

    if not image_path or not Path(image_path).exists():
        print("⚠️  跳过OCR测试（无有效图片）")
        return None

    try:
        from lingyi.ui_tars import ocr_image

        print(f"正在识别: {image_path}")
        result = ocr_image(image_path)

        if result['success']:
            print(f"✅ OCR识别成功")
            print(f"   置信度: {result['confidence']:.2f}")
            print(f"   识别文字:")
            print(f"   {result['text'][:200]}")

            if result.get('lines'):
                print(f"\n   前3行识别结果:")
                for i, line in enumerate(result['lines'][:3], 1):
                    print(f"   {i}. {line.get('text', '')}")

            return True
        else:
            print(f"❌ OCR识别失败")
            return False

    except Exception as e:
        print(f"❌ OCR识别失败: {e}")
        return False


def test_find_elements(image_path: str | None = None):
    """测试元素查找"""
    print("\n" + "=" * 50)
    print("测试4: UI元素查找")
    print("=" * 50)

    if not image_path or not Path(image_path).exists():
        print("⚠️  跳过元素查找测试（无有效图片）")
        return None

    try:
        from lingyi.ui_tars import find_elements

        print("正在查找按钮元素...")
        result = find_elements(image_path, element_type="button")

        if result['success']:
            print(f"✅ 元素查找成功")
            print(f"   找到 {result['count']} 个按钮")

            for i, elem in enumerate(result['elements'][:5], 1):
                bbox = elem.get('bbox', {})
                print(f"   {i}. 位置: ({bbox.get('x', 0)}, {bbox.get('y', 0)})")
                if elem.get('text'):
                    print(f"      文字: {elem['text']}")

            return True
        else:
            print(f"❌ 元素查找失败")
            return False

    except Exception as e:
        print(f"❌ 元素查找失败: {e}")
        return False


def test_analyze(image_path: str | None = None):
    """测试UI分析"""
    print("\n" + "=" * 50)
    print("测试5: UI界面分析")
    print("=" * 50)

    if not image_path or not Path(image_path).exists():
        print("⚠️  跳过UI分析测试（无有效图片）")
        return None

    try:
        from lingyi.ui_tars import analyze_ui_state

        print(f"正在分析: {image_path}")
        result = analyze_ui_state(image_path)

        if result['success']:
            print(f"✅ UI分析成功")
            print(f"   UI类型: {result['ui_type']}")
            print(f"   摘要: {result['summary'][:100]}")

            if result.get('text_content'):
                print(f"\n   主要文字（前200字符）:")
                print(f"   {result['text_content'][:200]}")

            if result.get('interactive_elements'):
                print(f"\n   可交互元素 ({len(result['interactive_elements'])} 个):")
                for elem in result['interactive_elements'][:3]:
                    print(f"   - {elem.get('type', 'unknown')}: "
                          f"{elem.get('text', elem.get('selector', ''))[:50]}")

            return True
        else:
            print(f"❌ UI分析失败")
            return False

    except Exception as e:
        print(f"❌ UI分析失败: {e}")
        return False


def test_tools():
    """测试LingYi工具集成"""
    print("\n" + "=" * 50)
    print("测试6: LingYi工具集成")
    print("=" * 50)

    try:
        from lingyi.tools import get_tools, execute_tool

        tools = get_tools()
        ui_tools = [t for t in tools if 'ui_' in t['function']['name']]

        print(f"✅ 找到 {len(ui_tools)} 个UI工具:")
        for tool in ui_tools:
            name = tool['function']['name']
            desc = tool['function']['description']
            print(f"   - {name}: {desc}")

        # 测试状态查询工具
        print("\n测试 ui_status 工具:")
        result = execute_tool("ui_status", {})
        print(result)

        return True

    except Exception as e:
        print(f"❌ 工具集成测试失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="UI-TARS功能测试")
    parser.add_argument("--screenshot", action="store_true", help="仅测试截图")
    parser.add_argument("--ocr", action="store_true", help="仅测试OCR")
    parser.add_argument("--find", action="store_true", help="仅测试元素查找")
    parser.add_argument("--analyze", action="store_true", help="仅测试UI分析")
    parser.add_argument("--tools", action="store_true", help="仅测试工具集成")
    parser.add_argument("--url", default="https://www.baidu.com", help="测试用的URL")

    args = parser.parse_args()

    # 环境检查
    if not os.environ.get("UI_TARS_ENABLED", "").lower() == "true":
        print("⚠️  UI_TARS_ENABLED未设置，测试可能会失败")
        print("   设置方法: export UI_TARS_ENABLED=true")
        print()

    # 运行测试
    results = []

    if args.screenshot or args.ocr or args.find or args.analyze or args.tools:
        # 选择性测试
        if args.screenshot:
            image_path = test_capture(args.url)
            results.append(("截图", image_path is not None))

        if args.ocr:
            image_path = test_capture(args.url)
            results.append(("OCR", test_ocr(image_path)))

        if args.find:
            image_path = test_capture(args.url)
            results.append(("元素查找", test_find_elements(image_path)))

        if args.analyze:
            image_path = test_capture(args.url)
            results.append(("UI分析", test_analyze(image_path)))

        if args.tools:
            results.append(("工具集成", test_tools()))
    else:
        # 完整测试
        print("UI-TARS功能测试\n")

        # 测试1: 服务状态
        available = test_status()
        results.append(("服务状态", available))

        if not available:
            print("\n❌ UI-TARS服务不可用，跳过后续测试")
            sys.exit(1)

        # 测试2: 截图
        image_path = test_capture(args.url)
        results.append(("截图", image_path is not None))

        # 测试3-5: 依赖截图
        if image_path:
            results.append(("OCR", test_ocr(image_path)))
            results.append(("元素查找", test_find_elements(image_path)))
            results.append(("UI分析", test_analyze(image_path)))

        # 测试6: 工具集成
        results.append(("工具集成", test_tools()))

    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
