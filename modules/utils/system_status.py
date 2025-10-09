#modules/utils/system_status.py
#专门把核心模块的状态写入system.db 的 

import sqlite3
import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "system.db")

def update_module_status(module_name: str, status: str, message: str = None, error_count: int = None):
    """
    更新或插入模块的运行状态。
    """
    conn = sqlite3.connect(DB_PATH)
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
        datetime.datetime.utcnow(),
        message,
        error_count
    ))

    conn.commit()
    conn.close()
