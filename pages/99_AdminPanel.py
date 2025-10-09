# pages/99_AdminPanel.py
import streamlit as st
from datetime import datetime, timedelta
from modules.auth.routes_local import SessionLocal
from modules.auth.models import User
from modules.logger import log_event
from modules.logger import get_model_price, set_model_price
import sqlite3
import pandas as pd

# ---------- 权限检查 ----------
user_info = st.session_state.get("user")
if not user_info or user_info.get("role") != "admin":
    st.warning("仅限管理员访问。请用管理员账号登录。")
    st.stop()

st.title("🔧 Admin 控制面板")

db = SessionLocal()

# ---------- Dashboard 概览 (简单) ----------
st.subheader("仪表盘总览")
col1, col2, col3 = st.columns(3)

# 用户数量
with col1:
    total_users = db.query(User).count()
    st.metric("用户总数", total_users)

# 活跃用户（示例：最近 7 天登录）
with col2:
    since = datetime.utcnow() - timedelta(days=7)
    active_count = db.query(User).filter(User.last_login != None, User.last_login >= since).count()
    st.metric("最近 7 天活跃用户", active_count)

# 管理员数量
with col3:
    admin_count = db.query(User).filter(User.role == "admin").count()
    st.metric("管理员数量", admin_count)

st.markdown("---")

# ---------- 用户管理 ----------
st.subheader("用户管理")

# 搜索与筛选
search_email = st.text_input("按邮箱搜索用户", value="")
role_filter = st.selectbox("按角色过滤", ["all", "user", "admin", "banned"], index=0)

query = db.query(User)
if search_email:
    query = query.filter(User.email.ilike(f"%{search_email}%"))
if role_filter != "all":
    query = query.filter(User.role == role_filter)

users = query.order_by(User.id.desc()).limit(200).all()

# 显示用户表格
user_rows = []
for u in users:
    user_rows.append({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "role": u.role,
        "is_active": bool(u.is_active),
        "last_login": str(u.last_login) if u.last_login else None,
    })
st.dataframe(pd.DataFrame(user_rows))

# 操作区：选择用户并操作
st.markdown("### 操作用户")
selected_id = st.number_input("用户 ID", min_value=1, value=users[0].id if users else 1, step=1)
target_user = db.query(User).filter(User.id == selected_id).first()
if not target_user:
    st.info("请选择有效用户 ID")
else:
    st.write(f"**{target_user.username}** — {target_user.email} — role: {target_user.role}")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("禁用用户 (is_active=0)"):
            target_user.is_active = 0
            db.commit()
            log_event("admin_panel", "INFO", "change", f"禁用用户 {target_user.id}", by_user=user_info.get("username"))
            st.success("已禁用用户")
    with col_b:
        if st.button("启用用户 (is_active=1)"):
            target_user.is_active = 1
            db.commit()
            log_event("admin_panel", "INFO", "change", f"启用用户 {target_user.id}", by_user=user_info.get("username"))
            st.success("已启用用户")
    with col_c:
        if st.button("提升为 Admin"):
            target_user.role = "admin"
            db.commit()
            log_event("admin_panel", "INFO", "change", f"提升用户为 admin {target_user.id}", by_user=user_info.get("username"))
            st.success("已提升为 admin")

    # 重置密码示例（将其设置为随机临时密码）
    if st.button("重置密码 (示例)"):
        import secrets
        temp_pw = secrets.token_urlsafe(12)
        from modules.auth.utils import hash_password
        target_user.password_hash = hash_password(temp_pw)
        db.commit()
        log_event("admin_panel", "INFO", "change", f"重置密码 user {target_user.id}", by_user=user_info.get("username"))
        st.success(f"密码已重置，临时密码（请妥善通知用户）: {temp_pw}")

st.markdown("---")

# ---------- 日志查询（使用 system.db） ----------
st.subheader("🧾 系统日志查询")

import os
LOG_DB = r"D:\Personal\Project\Exam SOS\ExamSOS System\database\system.db"

try:
    conn = sqlite3.connect(LOG_DB)
    st.caption(f"日志数据库路径：{os.path.abspath(LOG_DB)}")

    # === 筛选条件 ===
    flt_module = st.text_input("模块名过滤", value="")
    flt_status = st.selectbox("状态过滤", ["", "work", "down", "change", "warning"], index=0)
    flt_level = st.selectbox("日志等级过滤", ["", "INFO", "WARNING", "ERROR", "CRITICAL", "CHANGE"], index=0)
    flt_user = st.text_input("用户/管理员名过滤", value="")
    date_from = st.date_input("开始日期", value=(datetime.utcnow() - timedelta(days=7)).date())
    date_to = st.date_input("结束日期", value=datetime.utcnow().date())

    # === 组装 SQL ===
    sql = "SELECT id, created_at, source_module, level, status, by_user, by_admin, things, remark, reason, meta FROM logs WHERE 1=1"
    conditions, params = [], []

    if flt_module:
        conditions.append("AND source_module LIKE ?")
        params.append(f"%{flt_module}%")
    if flt_status:
        conditions.append("AND status = ?")
        params.append(flt_status)
    if flt_level:
        conditions.append("AND level = ?")
        params.append(flt_level)
    if flt_user:
        conditions.append("(by_user LIKE ? OR by_admin LIKE ?)")
        params.extend([f"%{flt_user}%", f"%{flt_user}%"])
    if date_from:
        conditions.append("AND date(created_at) >= date(?)")
        params.append(date_from.isoformat())
    if date_to:
        conditions.append("AND date(created_at) <= date(?)")
        params.append(date_to.isoformat())

    final_sql = " ".join([sql] + conditions + ["ORDER BY created_at DESC LIMIT 500"])

    # === 查询执行 ===
    rows = conn.execute(final_sql, params).fetchall()

    # === 转换为 DataFrame ===
    logs_df = pd.DataFrame(
        rows,
        columns=[
            "id", "created_at", "module", "level", "status",
            "by_user", "by_admin", "things", "remark", "reason", "meta"
        ]
    )

    # === 展示结果 ===
    st.dataframe(logs_df, use_container_width=True, hide_index=True)

    # === 展开 JSON meta ===
    if not logs_df.empty and "meta" in logs_df.columns:
        st.markdown("**查看选中日志详情：**")
        selected_row = st.number_input("输入日志 ID 查看详情", min_value=1, value=int(logs_df.iloc[0]['id']) if not logs_df.empty else 1)
        row = logs_df[logs_df['id'] == selected_row]
        if not row.empty:
            st.json(row.iloc[0].to_dict())

    # === 导出 CSV ===
    st.markdown("---")
    if not logs_df.empty and st.button("📤 导出日志 CSV"):
        csv = logs_df.to_csv(index=False)
        st.download_button(
            "下载 CSV 文件",
            data=csv,
            file_name=f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

    conn.close()

except Exception as e:
    st.error(f"无法打开日志数据库: {e}")


# ---------- Token 使用情况监控 ----------
st.markdown("---")
st.subheader("💰 Token 使用情况")

from modules.logger import get_model_price, set_model_price

try:
    conn = sqlite3.connect(LOG_DB)
    cursor = conn.cursor()

    # === 模型单价管理 ===
    st.markdown("### 🔧 模型单价设置 (USD / 每 1K tokens)")
    cursor.execute("SELECT model, price_per_1k, updated_at FROM model_prices ORDER BY model ASC")
    rows = cursor.fetchall()
    existing_prices = {r[0]: r[1] for r in rows}

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        model_name = st.text_input("模型名", value="gpt-4o")
    with col_b:
        price = st.number_input("单价 (USD / 1K tokens)", value=float(existing_prices.get(model_name, 0.005)), step=0.001)
    with col_c:
        if st.button("保存单价"):
            set_model_price(model_name, price)
            st.success(f"已更新 {model_name} 的单价为 {price} USD / 1K tokens")

    st.dataframe(pd.DataFrame(rows, columns=["model", "price_per_1k", "updated_at"]), use_container_width=True)

    st.markdown("---")

   # === Token 使用记录 ===
    st.markdown("### 📊 使用记录查询")

    flt_user = st.text_input("按用户 ID 过滤 (可留空)", value="")
    flt_model = st.text_input("按模型过滤 (可留空)", value="")

    # ✅ 给每个 date_input 加唯一 key，避免与上面的“系统日志查询”冲突
    date_from = st.date_input(
        "开始日期",
        value=(datetime.utcnow() - timedelta(days=7)).date(),
        key="usage_date_from"
    )
    date_to = st.date_input(
        "结束日期",
        value=datetime.utcnow().date(),
        key="usage_date_to"
    )

    sql = """
        SELECT id, created_at, user_id, model, prompt_tokens, completion_tokens, total_tokens, cost
        FROM usage_records
        WHERE date(created_at) BETWEEN date(?) AND date(?)
    """
    params = [date_from.isoformat(), date_to.isoformat()]

    if flt_user:
        sql += " AND user_id LIKE ?"
        params.append(f"%{flt_user}%")
    if flt_model:
        sql += " AND model LIKE ?"
        params.append(f"%{flt_model}%")

    sql += " ORDER BY created_at DESC LIMIT 500"
    rows = cursor.execute(sql, params).fetchall()

    usage_df = pd.DataFrame(
        rows,
        columns=[
            "id", "created_at", "user_id", "model",
            "prompt_tokens", "completion_tokens",
            "total_tokens", "cost"
        ]
    )

    st.dataframe(usage_df, use_container_width=True, hide_index=True)

    # === 汇总统计 ===
    if not usage_df.empty:
        total_tokens = usage_df["total_tokens"].sum()
        total_cost = usage_df["cost"].sum()
        st.metric("总 Token 消耗", f"{total_tokens:,}")
        st.metric("总成本 (USD)", f"${total_cost:.4f}")

    conn.close()

except Exception as e:
    st.error(f"无法读取 usage_records: {e}")

db.close()

# ---------- 模块健康状态监控 ----------
st.markdown("---")
st.subheader("🩺 系统模块状态监控")

STATUS_DB = r"D:\Personal\Project\Exam SOS\ExamSOS System\database\system.db"

try:
    conn = sqlite3.connect(STATUS_DB)
    cursor = conn.cursor()

    # 读取所有模块状态
    cursor.execute("""
        SELECT module_name, status, last_updated, error_count, message
        FROM module_status
        ORDER BY module_name ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        st.info("暂无模块状态记录。")
    else:
        # 用不同颜色显示状态
        status_colors = {
            "active": "🟢 正常",
            "warning": "🟡 警告",
            "error": "🔴 错误",
            "down": "⚫ 已停止",
            "unknown": "⚪ 未检测"
        }

        data = []
        for module_name, status, last_updated, error_count, message in rows:
            display_status = status_colors.get(status, status)
            data.append({
                "模块名": module_name,
                "状态": display_status,
                "错误次数": error_count,
                "最后更新时间": last_updated,
                "信息": message or ""
            })

        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True
        )

        # 刷新按钮
        if st.button("🔄 刷新状态"):
            st.experimental_rerun()

except Exception as e:
    st.error(f"无法读取模块状态表: {e}")
