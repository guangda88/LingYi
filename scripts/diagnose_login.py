#!/usr/bin/env python3
"""
诊断登录问题的脚本
检查 cookie、认证状态、登录流程
"""

import sys
import json
import requests
from pathlib import Path

# 配置
BASE_URL = "https://100.66.1.8:8900"
PWD = "2rmjyslg"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_server():
    """检查服务器是否在线"""
    print_section("1. 检查服务器连接")
    try:
        r = requests.get(BASE_URL, timeout=5, verify=False)
        print(f"✓ 服务器响应: {r.status_code}")
        return True
    except Exception as e:
        print(f"✗ 服务器连接失败: {e}")
        return False

def test_login():
    """测试登录功能"""
    print_section("2. 测试登录流程")

    # 第一次请求（无cookie）
    print("\n→ 发送登录请求（无cookie）")
    try:
        r = requests.post(
            f"{BASE_URL}/api/login",
            json={"password": PWD, "remember": True},
            timeout=10,
            verify=False
        )
        print(f"  状态码: {r.status_code}")
        print(f"  响应: {r.json()}")

        # 检查 cookie
        cookies = r.cookies
        print(f"\n→ Cookie 设置:")
        for cookie in cookies:
            print(f"  - {cookie.name} = {cookie.value[:20]}... (expires: {cookie.expires})")

        # 返回 cookie jar 用于后续请求
        return cookies
    except Exception as e:
        print(f"✗ 登录失败: {e}")
        return None

def check_authorized_endpoint(cookies):
    """使用 cookie 访问需要认证的端点"""
    print_section("3. 测试已认证的 API")

    if not cookies:
        print("✗ 没有 cookie，跳过测试")
        return

    # 测试 dashboard API
    print("\n→ 访问 /api/dashboard（需要认证）")
    try:
        r = requests.get(
            f"{BASE_URL}/api/dashboard",
            cookies=cookies,
            timeout=10,
            verify=False
        )
        print(f"  状态码: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  ✓ 认证成功")
            print(f"  - 今日计划: {len(data.get('plans', []))} 条")
            print(f"  - 今日日程: {len(data.get('schedules', []))} 条")
        else:
            print(f"  ✗ 认证失败: {r.text}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def check_websocket_token(cookies):
    """检查 WebSocket 连接所需的 token"""
    print_section("4. 检查 WebSocket Token")

    if not cookies:
        print("✗ 没有 cookie")
        return

    token = cookies.get('lingyi_token')
    if token:
        print(f"✓ lingyi_token 存在")
        print(f"  值: {token[:20]}...")
        print(f"\nWebSocket 连接 URL:")
        print(f"  wss://100.66.1.8:8900/ws/chat?token={token}")
        print(f"\n或者（自动读取 cookie）:")
        print(f"  wss://100.66.1.8:8900/ws/chat")
    else:
        print(f"✗ 未找到 lingyi_token cookie")
        print(f"  可用 cookies: {list(cookies.keys())}")

def check_index_page():
    """检查主页是否能正确加载"""
    print_section("5. 检查主页")

    try:
        r = requests.get(BASE_URL, timeout=10, verify=False)
        print(f"✓ 主页加载成功: {r.status_code}")
        if '<title>灵依' in r.text:
            print("✓ 页面标题正确")
        if '未登录' in r.text:
            print("⚠ 页面中包含'未登录'警告")
        else:
            print("✓ 页面无未登录警告")
    except Exception as e:
        print(f"✗ 主页加载失败: {e}")

def print_troubleshooting():
    """打印故障排查建议"""
    print_section("故障排查建议")

    print("""
如果显示"未登录"警告，请尝试以下步骤：

1. 清除浏览器缓存和 Cookie
   - Chrome: F12 → Application → Cookies → 删除所有
   - 刷新页面重新登录

2. 检查浏览器是否阻止 Cookie
   - Chrome: 设置 → 隐私和安全 → Cookie
   - 确保允许来自 100.66.1.8 的 Cookie

3. 尝试无痕模式
   - Chrome: Ctrl+Shift+N
   - 在无痕窗口中访问 https://100.66.1.8:8900

4. 确认登录成功
   - 密码: 2rmjyslg
   - 登录后应自动跳转到主页

5. 检查浏览器控制台
   - F12 → Console
   - 查看是否有 JavaScript 错误

6. 检查 WebSocket 连接
   - F12 → Network → WS
   - 查看 /ws/chat 连接状态

常见问题：
- Cookie 的 SameSite 属性可能导致问题
- IP 地址访问时，Cookie domain 设置可能不匹配
- 浏览器安全策略可能阻止跨域 Cookie
    """)

def main():
    print("\n" + "="*60)
    print("  LingYi WebUI 登录诊断工具")
    print("="*60)

    if not check_server():
        print("\n✗ 服务器不可用，请检查服务是否启动")
        return

    cookies = test_login()

    if cookies:
        check_authorized_endpoint(cookies)
        check_websocket_token(cookies)

    check_index_page()
    print_troubleshooting()

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
