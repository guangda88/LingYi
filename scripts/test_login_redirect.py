#!/usr/bin/env python3
"""
测试登录重定向功能
验证未登录访问主页时是否正确重定向
"""

import requests
from urllib.parse import urlparse

BASE_URL = "https://100.66.1.8:8900"
PWD = "2rmjyslg"

def test_redirect_on_unauthenticated():
    """测试未登录时访问主页是否重定向"""
    print("="*60)
    print("测试1: 未登录访问主页")
    print("="*60)

    # 访问主页（无cookie）
    r = requests.get(BASE_URL, timeout=10, verify=False, allow_redirects=False)

    print(f"状态码: {r.status_code}")
    print(f"响应头:")
    for key, value in r.headers.items():
        if 'location' in key.lower() or 'refresh' in key.lower():
            print(f"  {key}: {value}")

    if r.status_code == 200:
        content = r.text
        if 'location.href="/login"' in content:
            print("✓ 正确：主页包含登录重定向脚本")
            return True
        elif '/login' in content:
            print("✓ 正确：主页包含登录链接")
            return True
        else:
            print("⚠ 页面可能没有正确重定向")
            return False
    elif r.status_code == 302:
        location = r.headers.get('Location', '')
        if '/login' in location:
            print(f"✓ 正确：HTTP 302 重定向到 {location}")
            return True
        else:
            print(f"⚠ 重定向到错误的地址: {location}")
            return False
    else:
        print(f"⚠ 意外的状态码: {r.status_code}")
        return False

def test_authenticated_access():
    """测试登录后访问主页"""
    print("\n" + "="*60)
    print("测试2: 登录后访问主页")
    print("="*60)

    # 1. 登录
    print("→ 登录...")
    login_resp = requests.post(
        f"{BASE_URL}/api/login",
        json={"password": PWD, "remember": True},
        timeout=10,
        verify=False
    )

    if not login_resp.json().get('ok'):
        print("✗ 登录失败")
        return False

    cookies = login_resp.cookies
    print(f"✓ 登录成功，获得 cookie: {cookies.get('lingyi_token', '')[:20]}...")

    # 2. 使用 cookie 访问主页
    print("\n→ 使用 cookie 访问主页...")
    r = requests.get(
        BASE_URL,
        cookies=cookies,
        timeout=10,
        verify=False
    )

    print(f"状态码: {r.status_code}")

    if r.status_code == 200:
        content = r.text
        if 'location.href="/login"' in content:
            print("✗ 错误：已登录但仍被重定向到登录页")
            return False
        elif '<title>灵依' in content and '未登录' not in content[:5000]:
            print("✓ 正确：已登录，可以正常访问主页")
            return True
        else:
            print("⚠ 页面内容异常")
            return False
    else:
        print(f"⚠ 意外的状态码: {r.status_code}")
        return False

def main():
    print("\nLingYi WebUI 登录重定向测试\n")

    test1_ok = test_redirect_on_unauthenticated()
    test2_ok = test_authenticated_access()

    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"测试1（未登录重定向）: {'✓ 通过' if test1_ok else '✗ 失败'}")
    print(f"测试2（已登录访问）: {'✓ 通过' if test2_ok else '✗ 失败'}")

    if test1_ok and test2_ok:
        print("\n✓ 所有测试通过！登录功能正常")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    exit(main())
