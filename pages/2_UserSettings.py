# pages/3_UserSettings.py
import streamlit as st
import json
from datetime import datetime
from modules.auth.routes_local import SessionLocal
from modules.auth.models import User
from modules.auth.user_memory import save_user_memory, load_user_memory

# ---------- 登录检测 ----------
user_info = st.session_state.get("user")

if not user_info or not isinstance(user_info, dict) or "id" not in user_info:
    st.warning("⚠️ 请先登录后再访问用户设置页面。")
    st.stop()

USER_ID = st.session_state["user"]["id"]

st.title("⚙️ 用户设置中心")

# ---------- 从数据库加载用户 ----------
db = SessionLocal()
user = db.query(User).filter(User.id == USER_ID).first()
if not user:
    st.error("❌ 无法找到用户信息，请重新登录。")
    st.stop()

# ---------- 加载用户偏好 ----------
user_memory = load_user_memory(USER_ID)
default_lang = user_memory.get("default_lang", "中文")
default_style = user_memory.get("note_style", "简洁")
auto_save = user_memory.get("auto_save", True)

# ---------- 表单区域 ----------
with st.form("user_settings_form"):
    st.subheader("👤 基本信息")
    username = st.text_input("用户名", value=user.username or "")
    email = st.text_input("邮箱", value=user.email or "")

    st.markdown("---")
    st.subheader("🧠 偏好设置")

    lang = st.selectbox(
        "笔记语言偏好",
        ["中文", "English"],
        index=0 if default_lang == "中文" else 1
    )

    style = st.selectbox(
        "笔记风格偏好",
        ["简洁", "详细", "学术风", "轻松口语化"],
        index=["简洁", "详细", "学术风", "轻松口语化"].index(default_style)
        if default_style in ["简洁", "详细", "学术风", "轻松口语化"]
        else 0
    )

    auto_save_pref = st.checkbox("自动保存笔记", value=auto_save)

    submit = st.form_submit_button("💾 保存设置")

# ---------- 提交逻辑 ----------
if submit:
    try:
        user = db.merge(user)

        # 更新基本信息
        user.username = username.strip()
        user.email = email.strip()
        user.updated_at = datetime.utcnow()

        # 保存偏好
        new_memory = {
            "default_lang": lang,
            "note_style": style,
            "auto_save": auto_save_pref
        }
        success = save_user_memory(USER_ID, new_memory)

        db.commit()

        # 更新 session_state
        st.session_state["user"]["preferences"] = new_memory

        if success:
            st.success("✅ 用户设置已保存并同步更新！")
        else:
            st.error("⚠️ 偏好保存失败，请稍后重试。")

        # ✅ 先在关闭 session 前取出纯数据
        user_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "preferences": load_user_memory(USER_ID),
        }

    except Exception as e:
        db.rollback()
        st.error(f"❌ 更新失败：{e}")
        user_data = {}
    finally:
        db.close()

# ---------- 调试信息 ----------
if "user_data" in locals() and user_data:
    with st.expander("🧩 当前用户数据（调试用）"):
        st.json(user_data)
