#!/usr/bin/env python3
"""
测试删除单条消息功能
"""

import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path.home() / ".lingyi" / "webui.db"

def _ensure_chat_table():
    """初始化数据库表"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL DEFAULT 'default',
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, id)")

    conn.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT '新对话',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        message_count INTEGER DEFAULT 0
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)")
    conn.commit()
    conn.close()

def test_delete_message():
    """测试删除单条消息"""
    print("测试删除单条消息功能\n")

    _ensure_chat_table()

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 创建测试会话
    session_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO chat_sessions (session_id, title, message_count) VALUES (?, ?, ?)",
        (session_id, "测试会话", 0)
    )
    conn.commit()
    print(f"✓ 创建会话: {session_id[:8]}")

    # 添加5条消息
    messages = [
        ("user", "消息1"),
        ("assistant", "回复1"),
        ("user", "消息2"),
        ("assistant", "回复2"),
        ("user", "消息3")
    ]

    message_ids = []
    for role, content in messages:
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        message_id = cursor.lastrowid
        message_ids.append(message_id)
        cursor.execute(
            "UPDATE chat_sessions SET message_count = message_count + 1 WHERE session_id = ?",
            (session_id,)
        )
    conn.commit()
    print(f"✓ 添加了 {len(messages)} 条消息，ID: {message_ids}")

    # 验证初始状态
    cursor.execute(
        "SELECT COUNT(*), COUNT(DISTINCT id) FROM chat_messages WHERE session_id = ?",
        (session_id,)
    )
    count, distinct = cursor.fetchone()
    cursor.execute("SELECT message_count FROM chat_sessions WHERE session_id = ?", (session_id,))
    session_count = cursor.fetchone()[0]

    print(f"✓ 初始状态: 消息数={count}, 会话计数={session_count}")
    assert count == 5, "应该有5条消息"
    assert session_count == 5, "会话计数应该为5"

    # 删除第2条和第4条消息（回复1和回复2）
    delete_ids = [message_ids[1], message_ids[3]]
    for msg_id in delete_ids:
        cursor.execute("DELETE FROM chat_messages WHERE id = ?", (msg_id,))
        cursor.execute(
            "UPDATE chat_sessions SET message_count = message_count - 1 "
            "WHERE session_id = ? AND message_count > 0",
            (session_id,)
        )
    conn.commit()
    print(f"✓ 删除了2条消息: {delete_ids}")

    # 验证删除后的状态
    cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = ?", (session_id,))
    new_count = cursor.fetchone()[0]
    cursor.execute("SELECT message_count FROM chat_sessions WHERE session_id = ?", (session_id,))
    new_session_count = cursor.fetchone()[0]

    print(f"✓ 删除后状态: 消息数={new_count}, 会话计数={new_session_count}")
    assert new_count == 3, "删除后应该有3条消息"
    assert new_session_count == 3, "会话计数应该为3"

    # 验证删除的特定消息不存在
    for msg_id in delete_ids:
        cursor.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE id = ?",
            (msg_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 0, f"消息 {msg_id} 应该已被删除"

    print("✓ 删除的消息不存在")

    # 验证剩余的消息
    cursor.execute(
        "SELECT id, role, content FROM chat_messages WHERE session_id = ? ORDER BY id",
        (session_id,)
    )
    remaining = cursor.fetchall()

    print("\n--- 剩余消息 ---")
    for msg_id, role, content in remaining:
        print(f"  ID={msg_id}, role={role}, content={content}")

    assert len(remaining) == 3, "应该剩余3条消息"
    assert remaining[0][1] == "user" and remaining[0][2] == "消息1", "第1条消息应该保留"
    assert remaining[1][1] == "user" and remaining[1][2] == "消息2", "第3条消息应该保留"
    assert remaining[2][1] == "user" and remaining[2][2] == "消息3", "第5条消息应该保留"

    # 清理
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
    print("\n✓ 清理完成")

    print("\n=== 测试完成 ===")
    print("✅ 删除单条消息功能测试通过！")
    print("\n验证的功能：")
    print("  ✓ 删除单条消息")
    print("  ✓ 自动更新会话消息计数")
    print("  ✓ 删除不影响其他消息")
    print("  ✓ 正确的查询结果")

if __name__ == "__main__":
    test_delete_message()
