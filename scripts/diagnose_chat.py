#!/usr/bin/env python3
"""WebUI 聊天诊断工具"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests

requests.packages.urllib3.disable_warnings()

BASE_URL = "https://100.66.1.8:8900"


def check_service():
    """检查服务状态"""
    print("=" * 60)
    print("1. 服务状态检查")
    print("=" * 60)

    try:
        r = requests.get(BASE_URL, verify=False, timeout=5)
        if r.status_code == 200:
            print("✅ Web 服务运行正常")
            return True
        else:
            print(f"❌ Web 服务异常: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        return False


def check_models():
    """检查模型状态"""
    print("\n" + "=" * 60)
    print("2. 模型状态检查")
    print("=" * 60)

    try:
        r = requests.get(f"{BASE_URL}/api/models", verify=False)
        if r.status_code == 200:
            models = r.json()
            print("✅ 模型状态：")
            for name, info in models.items():
                if name == "_meta":
                    continue
                state = info.get("state", "unknown")
                if state == "available":
                    print(f"  ✅ {name}: 可用")
                else:
                    print(f"  ⚠️  {name}: {state}")
            print(f"\n下次重置: {models.get('_meta', {}).get('next_reset', '未知')}")
            return True
        else:
            print(f"❌ 获取模型状态失败: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ 检查模型状态异常: {e}")
        return False


def check_auth():
    """检查认证状态"""
    print("\n" + "=" * 60)
    print("3. 认证状态检查")
    print("=" * 60)

    try:
        # 尝试用错误密码
        r = requests.post(f"{BASE_URL}/api/login",
                          json={"password": "wrong"}, verify=False)
        if r.status_code == 403:
            print("✅ 认证功能正常（错误密码被拒绝）")
        elif r.status_code == 200:
            print("⚠️  认证未启用或配置异常")

        # 尝试用正确密码
        r = requests.post(f"{BASE_URL}/api/login",
                          json={"password": "2rmjyslg"}, verify=False)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                print("✅ 正确密码可以登录")
                token = r.cookies.get("lingyi_token")
                print(f"   Token: {token[:20]}..." if token else "   (无 token)")
                return token
            else:
                print(f"❌ 登录失败: {data}")
                return None
        else:
            print(f"❌ 登录请求失败: {r.status_code}")
            return None
    except Exception as e:
        print(f"❌ 认证检查异常: {e}")
        return None


def check_apis(token=None):
    """检查 API 端点"""
    print("\n" + "=" * 60)
    print("4. API 端点检查")
    print("=" * 60)

    endpoints = [
        ("仪表盘", "/api/dashboard"),
        ("模型", "/api/models"),
        ("使用情况", "/api/usage"),
        ("日程", "/api/schedules/today"),
    ]

    cookies = {"lingyi_token": token} if token else None

    for name, path in endpoints:
        try:
            r = requests.get(f"{BASE_URL}{path}",
                           cookies=cookies, verify=False, timeout=5)
            if r.status_code == 200:
                print(f"  ✅ {name}")
            else:
                print(f"  ❌ {name}: {r.status_code}")
        except Exception as e:
            print(f"  ⚠️  {name}: {str(e)[:30]}")


def check_dashboard(token=None):
    """检查仪表盘数据"""
    print("\n" + "=" * 60)
    print("5. 仪表盘数据检查")
    print("=" * 60)

    try:
        cookies = {"lingyi_token": token} if token else None
        r = requests.get(f"{BASE_URL}/api/dashboard", cookies=cookies, verify=False)
        if r.status_code == 200:
            data = r.json()
            date = data.get("date", "")
            schedules = data.get("today_schedules", [])
            memos = data.get("recent_memos", [])
            projects = data.get("active_projects", [])

            print(f"✅ 日期: {date}")
            print(f"   今日日程: {len(schedules)} 条")
            print(f"   最近备忘: {len(memos)} 条")
            print(f"   活跃项目: {len(projects)} 个")
            return True
        else:
            print(f"❌ 获取仪表盘失败: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ 仪表盘检查异常: {e}")
        return False


def print_troubleshooting():
    """打印故障排查建议"""
    print("\n" + "=" * 60)
    print("故障排查建议")
    print("=" * 60)
    print("""
如果您在浏览器中遇到聊天问题，请检查：

1. 登录状态
   - 打开 https://100.66.1.8:8900
   - 如果需要登录，密码是: 2rmjyslg
   - 登录后应该看到"灵依已上线 ✓"提示

2. 浏览器控制台
   - 按 F12 打开开发者工具
   - 查看 Console 标签是否有错误
   - 查看 Network 标签，筛选 WS/WebSocket，查看连接状态

3. 网络连接
   - 确保可以访问 https://100.66.1.8:8900
   - 如果是本地访问，尝试用 http://127.0.0.1:8900

4. 常见问题
   - ❓ 一直显示"灵依在思考..."
     → 可能是 AI 模型响应慢，请等待 10-30 秒

   - ❓ 显示"未登录"
     → 需要先登录，密码: 2rmjyslg

   - ❓ 显示"所有AI模型配额均已用完"
     → 等待配额重置（通常 5 小时一次）
     → 系统会自动降级到免费模型

   - ❓ 发送消息无响应
     → 按 F12 查看控制台错误
     → 刷新页面重试
     → 检查网络连接

5. 联系支持
   如果以上方法都无法解决，请提供：
   - 浏览器控制台截图（F12）
   - 浏览器 Network 标签截图（WebSocket 连接状态）
   - 具体的错误消息
""")


if __name__ == "__main__":
    print("🔍 LingYi WebUI 诊断工具\n")

    service_ok = check_service()
    models_ok = check_models()
    token = check_auth()

    if token:
        check_apis(token)
        check_dashboard(token)
    else:
        print("\n⚠️  无法登录，跳过需要认证的检查")

    print_troubleshooting()

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

    if service_ok and models_ok:
        print("\n✅ 后端服务正常，问题可能在前端或网络")
        print("   请使用浏览器访问: https://100.66.1.8:8900")
        print("   如果需要登录，密码是: 2rmjyslg")
    else:
        print("\n❌ 后端服务存在问题，请检查日志:")
        print("   tail -f /tmp/lingyi_web.log")
        print("   tail -f /tmp/lingyi.log")
