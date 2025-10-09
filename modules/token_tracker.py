# modules/token_tracker.py

import sqlite3
import datetime
import os
import json

from modules.utils.path_helper import DB_PATH

def log_token_usage(user_id, model, usage, request_id=None, remark=None):
    """
    记录单次调用的 Token 使用信息
    usage: response.usage 或类似格式 { "prompt_tokens": int, "completion_tokens": int, "total_tokens": int }
    """
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # 预估成本（可按实际模型价格换算）
    cost_estimate = total_tokens * 0.000002  # 假设每 token 成本约 $0.000002

    day_key = datetime.datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 写入 token_usage（原始记录）
    cur.execute("""
        INSERT INTO token_usage (user_id, model_name, prompt_tokens, completion_tokens, total_tokens, cost_estimate, request_id, remark)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, model, prompt_tokens, completion_tokens, total_tokens, cost_estimate, request_id, remark))

    # 写入 usage_records（每日汇总）
    cur.execute("""
        INSERT INTO usage_records (user_id, model, prompt_tokens, completion_tokens, total_tokens, cost, day_key)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, model, prompt_tokens, completion_tokens, total_tokens, cost_estimate, day_key))

    conn.commit()
    conn.close()
