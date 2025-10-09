#modules/auth/models.py
#用户系统的核心数据模型层，主要负责定义数据库表结构、用户身份与数据之间的关系。

from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()  # ✅ 自定义 Base

# ---------------- 用户模型 ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password_hash = Column(String)
    google_id = Column(String)
    github_id = Column(String)
    role = Column(String, default="user")
    default_note_style = Column(String)
    default_lang = Column(String)
    quota_plan = Column(String, default="free")
    preferences = Column(Text)  # JSON 字符串：用户个性化设置 / 记忆
    is_active = Column(Integer, default=1)
    last_login = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

    # ORM 关系
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("UserNote", back_populates="user", cascade="all, delete-orphan")


# ---------------- 用户会话模型 ----------------
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(TIMESTAMP)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


# ---------------- 用户笔记 / 记忆模型 ----------------
class UserNote(Base):
    __tablename__ = "user_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    note_title = Column(String)
    note_content = Column(Text)
    note_metadata = Column(Text)  # 用户的习惯 / 参数记录
    feedback = Column(Text)  # 用户的反馈行为
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

    user = relationship("User", back_populates="notes")
