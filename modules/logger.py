# modules/logger.py
# 工具函数（日志 / token 追踪 / 模型价格）

import sqlite3
import datetime
import json
import os
import time
from modules.utils.path_helper import SYSTEM_DB as DB_PATH  # ✅ 统一数据库路径

# === 通用函数 ===
def ensure_database_ready():
    """确保 database 目录存在"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def connect_with_retry(db_path, retries=5, delay=0.2):
    """带重试机制的 SQLite 连接"""
    for i in range(retries):
        try:
            conn = sqlite3.connect(db_path, timeout=5, isolation_level=None)
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise
    raise sqlite3.OperationalError("Database is locked after multiple retries")


def enable_wal_mode():
    """启用 WAL 模式（支持并发读写）"""
    conn = connect_with_retry(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()


# 初始化数据库目录 + WAL
ensure_database_ready()
enable_wal_mode()

# === 日志系统 ===
VALID_STATUS = {'work', 'down', 'change', 'warning', 'done', 'success', 'info'}

def init_log_table():
    """确保 logs 表存在且结构正确"""
    conn = connect_with_retry(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            source_module TEXT,
            level TEXT,
            status TEXT CHECK(status IN (
                'work','down','change','warning','done','success','info'
            )),
            request_id TEXT,
            by_user TEXT,
            by_admin TEXT,
            things TEXT,
            remark TEXT,
            reason TEXT,
            meta TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_event(
    source_module: str,
    level: str = "INFO",
    status: str = "work",
    things: str = "",
    remark: str = "",
    reason: str = "",
    request_id: str = None,
    by_user: str = "system",
    by_admin: str = None,
    meta: dict = None
):
    """统一的日志记录函数"""
    try:
        if status not in VALID_STATUS:
            print(f"[LOGGER WARNING] 非法状态 '{status}'，已改为 'work'")
            status = "work"

        conn = connect_with_retry(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (
                created_at, source_module, level, status,
                request_id, by_user, by_admin, things,
                remark, reason, meta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.datetime.utcnow().isoformat(),
            source_module,
            level.upper(),
            status,
            request_id,
            by_user,
            by_admin,
            things,
            remark,
            reason,
            json.dumps(meta or {}, ensure_ascii=False)
        ))
        conn.commit()
        conn.close()

        print(f"[{datetime.datetime.now():%H:%M:%S}] [{source_module}] {level.upper()} - {things}")

    except Exception as e:
        print(f"[LOGGING ERROR] {e}")
        print(f"[{level}] {source_module}: {things} — {remark}")

# === Token 使用记录 ===
def init_usage_table():
    """确保 usage_records 表存在"""
    conn = connect_with_retry(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            user_id TEXT,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost REAL
        )
    """)
    conn.commit()
    conn.close()


def calculate_cost(model, total_tokens):
    """根据模型计算消耗成本"""
    price_per_1k = {
        "gpt-4o": 0.005,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.001
    }
    return round((total_tokens / 1000) * price_per_1k.get(model, 0.005), 6)


def log_token_usage(
    user_id,
    model=None,
    prompt_tokens=0,
    completion_tokens=0,
    total_tokens=0,
    model_name=None,
    cost_estimate=None,
    request_id=None,
    remark=None
):
    """记录一次 token 消耗"""
    model = model or model_name
    cost = cost_estimate or calculate_cost(model, total_tokens)

    try:
        conn = connect_with_retry(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_records (
                created_at, user_id, model,
                prompt_tokens, completion_tokens,
                total_tokens, cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.datetime.utcnow().isoformat(),
            user_id,
            model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            cost
        ))
        conn.commit()
        conn.close()

        log_event(
            source_module="token_tracker",
            level="INFO",
            status="done",
            things=f"Token usage logged: {total_tokens} tokens",
            by_user=user_id,
            remark=remark,
            meta={
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost": cost,
                "request_id": request_id
            }
        )
    except Exception as e:
        log_event(
            source_module="logger",
            level="ERROR",
            status="warning",
            things="无法写入 usage_records",
            remark=str(e),
            by_user=user_id
        )

# === 模型单价管理 ===
def init_model_price_table():
    """模型单价表"""
    conn = connect_with_retry(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT UNIQUE,
            price_per_1k REAL,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_model_price(model: str) -> float:
    """读取模型单价"""
    conn = connect_with_retry(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT price_per_1k FROM model_prices WHERE model = ?", (model,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]

    default_prices = {
        "gpt-4o": 0.005,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.001
    }
    return default_prices.get(model.lower(), 0.005)


def set_model_price(model: str, price: float):
    """更新或插入模型单价"""
    conn = connect_with_retry(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO model_prices (model, price_per_1k, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(model)
        DO UPDATE SET
            price_per_1k = excluded.price_per_1k,
            updated_at = excluded.updated_at
    """, (model, price, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ✅ 启动时初始化所有表
init_log_table()
init_usage_table()
init_model_price_table()
