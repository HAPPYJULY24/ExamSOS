# modules/utils/system_status.py
# 专门把核心模块的状态写入 system.db

import os
import sqlite3
import datetime
import time
from modules.utils.path_helper import SYSTEM_DB  # ✅ 统一数据库路径

# ✅ 合法状态集合
VALID_MODULE_STATUS = {
    'work','down','change','warning','done','success','info','load','save','init'
}

# === 通用函数 ===
def ensure_database_ready():
    """确保数据库目录存在"""
    os.makedirs(os.path.dirname(SYSTEM_DB), exist_ok=True)

def connect_with_retry(db_path, retries=5, delay=0.2):
    """带重试机制的 SQLite 连接"""
    for _ in range(retries):
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
    conn = connect_with_retry(SYSTEM_DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()

# 初始化
ensure_database_ready()
enable_wal_mode()


# === 模块状态表 ===
def init_module_status_table():
    """若 module_status 表不存在则自动创建"""
    conn = connect_with_retry(SYSTEM_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS module_status (
            module_name TEXT PRIMARY KEY,
            status TEXT CHECK(status IN (
                'work','down','change','warning','done','success','info','load','save','init'
            )),
            last_updated TEXT,
            message TEXT,
            error_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def update_module_status(module_name: str, status: str, message: str = None, error_count: int = None):
    """
    更新或插入模块运行状态。
    - module_name: 模块名（如 'logger', 'auth', 'token_tracker'）
    - status: 当前状态
    - message: 状态说明
    - error_count: 错误次数，可为空则不覆盖
    """
    init_module_status_table()  # ✅ 确保表存在

    # 检查状态是否合法
    if status not in VALID_MODULE_STATUS:
        print(f"[SYSTEM WARNING] 非法状态 '{status}'，已改为 'work'")
        status = 'work'

    conn = connect_with_retry(SYSTEM_DB)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO module_status (module_name, status, last_updated, message, error_count)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(module_name)
        DO UPDATE SET 
            status = excluded.status,
            last_updated = excluded.last_updated,
            message = excluded.message,
            error_count = COALESCE(excluded.error_count, module_status.error_count);
    """, (
        module_name,
        status,
        datetime.datetime.utcnow().isoformat(),
        message,
        error_count
    ))

    conn.commit()
    conn.close()
