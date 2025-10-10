# modules/token_tracker.py
# 记录 token 使用信息，并写入 system.db

import sqlite3
import datetime
import json
import os
from modules.utils.path_helper import SYSTEM_DB # ✅ 改成统一从 path_helper 获取 system.db

def log_token_usage(user_id, model, usage, request_id=None, remark=None):
    """
    记录单次调用的 Token 使用信息
    usage: response.usage 或类似格式 { "prompt_tokens": int, "completion_tokens": int, "total_tokens": int }
    """
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # ✅ 成本估算
    cost_estimate = total_tokens * 0.000002  # 假设每 token 成本约 $0.000002
    day_key = datetime.datetime.now().strftime("%Y-%m-%d")

    # ✅ 确保数据库路径存在
    os.makedirs(os.path.dirname(SYSTEM_DB), exist_ok=True)

    conn = sqlite3.connect(SYSTEM_DB)
    cur = conn.cursor()

    # ✅ 确保必要表存在（以防未初始化）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT,
            model_name TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost_estimate REAL,
            request_id TEXT,
            remark TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_key TEXT,
            user_id TEXT,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost REAL
        )
    """)

    # ✅ 写入 token_usage（原始记录）
    cur.execute("""
        INSERT INTO token_usage (user_id, model_name, prompt_tokens, completion_tokens, total_tokens, cost_estimate, request_id, remark)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, model, prompt_tokens, completion_tokens, total_tokens, cost_estimate, request_id, remark))

    # ✅ 写入 usage_records（每日汇总）
    cur.execute("""
        INSERT INTO usage_records (day_key, user_id, model, prompt_tokens, completion_tokens, total_tokens, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (day_key, user_id, model, prompt_tokens, completion_tokens, total_tokens, cost_estimate))

    conn.commit()
    conn.close()
