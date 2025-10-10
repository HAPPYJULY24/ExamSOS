# modules/auth/routes_local.py
# 本地登录与注册模块

import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from modules.auth.models import Base, User, UserSession
from modules.auth.utils import hash_password, verify_password, create_access_token
from modules.utils.path_helper import USER_DB  # ✅ 统一从 path_helper 获取数据库路径

# ---------- 数据库配置 ----------
# ✅ 修复语法错误：os.makedirs() 少了一个右括号
os.makedirs(os.path.dirname(USER_DB), exist_ok=True)

# ✅ 使用统一的数据库引擎配置
engine = create_engine(
    f"sqlite:///{USER_DB}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------- 初始化数据库 ----------
Base.metadata.create_all(bind=engine)


# ---------- 注册 ----------
def register_user(username: str, email: str, password: str):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return {"success": False, "message": "邮箱已被注册"}
        if db.query(User).filter(User.username == username).first():
            return {"success": False, "message": "用户名已存在"}

        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"success": True, "message": "注册成功", "user_id": new_user.id}

    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"注册失败: {e}"}
    finally:
        db.close()


# ---------- 登录 ----------
def authenticate_user(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "用户不存在"}

        if not getattr(user, "is_active", True):
            return {"error": "账户已被禁用，请联系管理员"}

        if not verify_password(password, user.password_hash):
            return {"error": "密码错误"}

        # ✅ 成功登录逻辑
        user.last_login = datetime.utcnow()
        token_data = {"user_id": user.id, "username": user.username}
        access_token = create_access_token(token_data, timedelta(hours=1))

        new_session = UserSession(
            user_id=user.id,
            access_token=access_token,
            ip_address="local_test",
            user_agent="local",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(new_session)
        db.commit()

        # ✅ 写入 Streamlit 会话状态
        st.session_state.update({
            "is_authenticated": True,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "access_token": access_token
        })

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "access_token": access_token
        }

    except Exception as e:
        db.rollback()
        return {"error": f"登录失败: {e}"}
    finally:
        db.close()
