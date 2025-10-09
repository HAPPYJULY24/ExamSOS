#modules/utils/path_helper.py

# modules/utils/path_helper.py
import os

# 当前文件: modules/utils/path_helper.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 回到项目根目录（上两层）
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# 数据库目录
DB_DIR = os.path.join(ROOT_DIR, "database")

# 确保目录存在
os.makedirs(DB_DIR, exist_ok=True)

# 各数据库路径
USER_DB = os.path.join(DB_DIR, "user.db")
SYSTEM_DB = os.path.join(DB_DIR, "system.db")

def get_path(name: str):
    """根据逻辑名称返回数据库路径"""
    mapping = {
        "user": USER_DB,
        "system": SYSTEM_DB,
    }
    return mapping.get(name)

