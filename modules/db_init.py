# modules/db_init.py
# 用于初始化系统与用户数据库

import sqlite3
import os
from modules.db_schema import SYSTEM_TABLES, USER_TABLES

# === 数据库存放路径 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")

SYSTEM_DB_PATH = os.path.join(DB_DIR, "system.db")
USER_DB_PATH = os.path.join(DB_DIR, "user.db")


def ensure_dir(path):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path)


def init_database(db_path: str, tables: dict, db_name: str):
    """初始化数据库与数据表"""
    print(f"\n🔧 初始化数据库：{db_name}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for table_name, ddl in tables.items():
        try:
            cursor.executescript(ddl)
            print(f"✅ 表已创建：{table_name}")
        except Exception as e:
            print(f"❌ 创建表 {table_name} 时出错：{e}")

    conn.commit()
    conn.close()
    print(f"🎉 数据库初始化完成：{db_name}")


def create_indexes():
    """为日志与任务表创建索引（提升查询性能）"""
    conn = sqlite3.connect(SYSTEM_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_request_id ON logs(request_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);")
        conn.commit()
        print("📈 索引创建完成")
    except Exception as e:
        print(f"⚠️ 索引创建失败：{e}")
    finally:
        conn.close()


def main():
    """主入口"""
    print("=== 🚀 启动数据库初始化 ===")

    ensure_dir(DB_DIR)

    # 初始化系统数据库
    init_database(SYSTEM_DB_PATH, SYSTEM_TABLES, "System Database")

    # 初始化用户数据库
    init_database(USER_DB_PATH, USER_TABLES, "User Database")

    # 创建索引
    create_indexes()

    print("\n✅ 所有数据库初始化完成！")
    print(f"📂 System DB: {SYSTEM_DB_PATH}")
    print(f"📂 User DB:   {USER_DB_PATH}")


if __name__ == "__main__":
    main()
