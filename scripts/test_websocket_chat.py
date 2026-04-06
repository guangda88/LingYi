#!/usr/bin/env python3
"""测试 WebSocket 聊天功能"""

import asyncio
import json
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import websockets
import requests

requests.packages.urllib3.disable_warnings()

BASE_URL = "https://100.66.1.8:8900"
WS_URL = "wss://100.66.1.8:8900/ws/chat"


async def test_chat():
    """测试聊天功能"""
    print("=" * 60)
    print("WebSocket 聊天测试")
    print("=" * 60)

    # 1. 先登录获取 token
    print("\n1. 登录中...")
    try:
        r = requests.post(f"{BASE_URL}/api/login",
                          json={"password": "2rmjyslg"}, verify=False)
        if r.status_code != 200:
            print(f"❌ 登录失败: {r.status_code}")
            print(r.text)
            return

        login_data = r.json()
        if not login_data.get("ok"):
            print(f"❌ 登录失败: {login_data}")
            return

        print("✅ 登录成功")
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return

    # 2. 获取 cookie
    cookies = r.cookies.get_dict()
    token = cookies.get("lingyi_token")
    print(f"Token: {token[:20] if token else 'None'}...")

    # 3. 连接 WebSocket
    print("\n2. 连接 WebSocket...")
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        # 使用 URL 参数传递 token
        ws_url_with_token = f"{WS_URL}?token={token}"
        async with websockets.connect(
            ws_url_with_token,
            ssl=ssl_context
        ) as ws:
            print("✅ WebSocket 已连接")

            # 4. 接收历史消息
            print("\n3. 接收历史消息...")
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    print(f"收到: {data.get('type')}")

                    if data.get('type') == 'history':
                        messages = data.get('messages', [])
                        print(f"✅ 收到 {len(messages)} 条历史消息")
                        break
                except asyncio.TimeoutError:
                    print("⚠️ 等待历史消息超时")
                    break

            # 5. 发送测试消息
            print("\n4. 发送测试消息...")
            test_msg = {"type": "text", "text": "你好", "no_tts": True}
            await ws.send(json.dumps(test_msg))
            print("✅ 已发送: '你好'")

            # 6. 接收回复
            print("\n5. 等待回复...")
            for i in range(30):  # 等待最多30秒
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1)
                    data = json.loads(msg)
                    msg_type = data.get('type')

                    if msg_type == 'ping':
                        continue

                    if msg_type == 'reply':
                        print(f"✅ 收到回复: {data.get('text', '')[:100]}...")
                        if data.get('audio'):
                            print(f"   (音频: {len(data['audio'])} bytes)")
                        break

                    print(f"收到消息: {msg_type}")

                except asyncio.TimeoutError:
                    continue

            print("\n6. 发送第二条消息...")
            test_msg2 = {"type": "text", "text": "今天有什么安排？", "no_tts": True}
            await ws.send(json.dumps(test_msg2))

            print("7. 等待第二条回复...")
            for i in range(30):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1)
                    data = json.loads(msg)
                    msg_type = data.get('type')

                    if msg_type == 'ping':
                        continue

                    if msg_type == 'reply':
                        print(f"✅ 收到回复: {data.get('text', '')[:100]}...")
                        break

                except asyncio.TimeoutError:
                    continue

            print("\n✅ 测试完成")

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket 错误: {e}")
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_chat())
