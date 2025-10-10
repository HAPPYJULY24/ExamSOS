# modules/utils/path_helper.py
# 用于统一管理所有数据库路径

import os

# 项目根目录（自动向上两层找到主目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 数据库主目录
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

# 各个数据库路径
SYSTEM_DB = os.path.join(DB_DIR, "system.db")
USER_DB = os.path.join(DB_DIR, "user.db")
LOG_DB = os.path.join(DB_DIR, "log.db")  # ✅ 这行是关键！

# （可选）调试时打印路径
if __name__ == "__main__":
    print("SYSTEM_DB:", SYSTEM_DB)
    print("USER_DB:", USER_DB)
    print("LOG_DB:", LOG_DB)
