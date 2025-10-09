# scripts/create_admin.py
"""
一次性创建 admin 用户脚本（受保护）

优先顺序：
1️⃣ 尝试从 Streamlit 环境（st.secrets 或 os.environ）读取 INITIAL_ADMIN_TOKEN
2️⃣ 若没有，再从 .env 文件读取（自动加载）
3️⃣ 若仍未找到，则要求交互确认

用法（在 shell / PowerShell 中）：
    python scripts/create_admin.py --username admin --email admin@example.com --password "StrongPass123!" --token your-token
"""

import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # ✅ 修正路径问题
# ---- 优先尝试从 Streamlit 临时环境加载 ----
try:
    import streamlit as st
    if "INITIAL_ADMIN_TOKEN" in st.secrets:
        os.environ["INITIAL_ADMIN_TOKEN"] = st.secrets["INITIAL_ADMIN_TOKEN"]
        print("🔐 从 Streamlit secrets 中加载 INITIAL_ADMIN_TOKEN")
except Exception:
    pass  # Streamlit 可能未安装或运行环境非 Streamlit，无需报错

# ---- 回退：尝试加载 .env 文件 ----
if "INITIAL_ADMIN_TOKEN" not in os.environ:
    load_dotenv()
    if "INITIAL_ADMIN_TOKEN" in os.environ:
        print("📦 从 .env 文件中加载 INITIAL_ADMIN_TOKEN")
    else:
        print("⚠️ 未检测到 INITIAL_ADMIN_TOKEN（将在执行时要求确认）")

# ---- 数据库与模型导入 ----
from modules.auth.routes_local import SessionLocal, engine, Base
from modules.auth.models import User
from modules.auth.utils import hash_password


def ensure_db():
    """确保数据库基表存在"""
    Base.metadata.create_all(bind=engine)


def create_admin(username: str, email: str, password: str, token: str = None):
    """创建或升级 admin 用户"""
    env_token = os.getenv("INITIAL_ADMIN_TOKEN")

    # --- 校验安全 token ---
    if env_token:
        if token != env_token:
            raise SystemExit("❌ ERROR: INITIAL_ADMIN_TOKEN 不匹配，脚本中止。")
    else:
        print("⚠️ 没有检测到 INITIAL_ADMIN_TOKEN —— 请确认你确实要创建 admin（y/N）")
        choice = input().strip().lower()
        if choice != "y":
            raise SystemExit("🛑 中止：未确认创建 admin。")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing:
            print(
                f"用户已存在 (id={existing.id}, username={existing.username}, email={existing.email})。将升级为 admin。"
            )
            existing.role = "admin"
            existing.updated_at = datetime.utcnow()
            db.commit()
            print("✅ 已将现有用户标记为 admin。")
            return

        admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(admin)
        db.commit()
        print(f"✅ 成功创建 admin 用户: id={admin.id}, username={admin.username}")
    except Exception as e:
        db.rollback()
        print("❌ 创建 admin 失败：", e)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--token", required=False, help="与环境变量 INITIAL_ADMIN_TOKEN 匹配（如果你已在环境中设置）")
    args = parser.parse_args()

    ensure_db()
    create_admin(args.username, args.email, args.password, args.token)
