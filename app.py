#app.py
#程序主要入口
import streamlit as st
from modules import summary_generator as sg
from modules.auth import routes_local as auth  # ✅ 使用本地注册/登录逻辑

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 20% 20%, #0a0f1a, #000000);
    color: white;
    font-family: 'Segoe UI', sans-serif;
}

/* 登录容器 */
.login-box {
    backdrop-filter: blur(15px);
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 20px;
    padding: 40px 50px;
    width: 380px;
    margin: 120px auto;
    box-shadow: 0 0 25px rgba(0,0,0,0.4);
}

/* 标题 */
.login-box h1 {
    text-align: center;
    font-size: 28px;
    margin-bottom: 30px;
    color: #ffffff;
    font-weight: 600;
}

/* 输入框 */
.stTextInput>div>div>input {
    background-color: rgba(255, 255, 255, 0.1);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 10px;
}

/* 按钮 */
.stButton>button {
    width: 100%;
    background: linear-gradient(90deg, #0072ff, #00c6ff);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 10px;
    margin-top: 15px;
    transition: 0.25s;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #005bea, #00c6fb);
    transform: scale(1.03);
}
</style>
""", unsafe_allow_html=True)


st.set_page_config(page_title="ExamSOS", layout="wide")

# ---------- 初始化 Session 状态 ----------
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "user" not in st.session_state:
    st.session_state["user"] = None

# ---------- 用户登录页 ----------
if st.session_state["page"] == "login":
    st.title("🔐 登录 ExamSOS 账号")

    email = st.text_input("邮箱")
    password = st.text_input("密码", type="password")

    if st.button("登录"):
        user = auth.authenticate_user(email, password)

        # ✅ 安全判断逻辑
        if user is None:
            st.error("邮箱或密码错误，请重试。")
        elif "error" in user:
            st.error(user["error"])  # 显示账户被禁用提示
        else:
            st.session_state["user"] = user
            st.session_state["page"] = "home"
            st.success(f"欢迎回来，{user['username']}！")
            st.rerun()  # ✅ 关键：立即刷新页面

    st.markdown("还没有账号？")
    if st.button("注册新用户"):
        st.session_state["page"] = "register"

# ---------- 注册页 ----------
elif st.session_state["page"] == "register":
    st.title("📝 注册 ExamSOS 账号")

    username = st.text_input("创建用户名")
    email = st.text_input("邮箱")
    password = st.text_input("密码", type="password")
    confirm = st.text_input("确认密码", type="password")

    if st.button("注册"):
        if password != confirm:
            st.error("两次输入的密码不一致！")
        elif not email or not username:
            st.error("用户名和邮箱不能为空！")
        else:
            result = auth.register_user(username, email, password)
            if result["success"]:
                st.success("注册成功，请登录！")
                st.session_state["page"] = "login"  # ✅ 注册成功返回登录页
            else:
                st.error(result["message"])

    if st.button("返回登录"):
        st.session_state["page"] = "login"

# ---------- 首页 ----------
elif st.session_state["page"] == "home":
    st.title("📘 ExamSOS - 系统入口")
    user = st.session_state["user"]

    # ✅ 防御性检查，防止 user=None 或缺少 username
    if not user or "username" not in user:
        st.warning("用户信息无效，请重新登录。")
        st.session_state["page"] = "login"
        st.stop()

    st.markdown(f"👋 欢迎，**{user['username']}**")

    if st.button("🚪 登出"):
        st.session_state.clear()
        st.session_state["page"] = "login"

    st.markdown("请选择你要使用的功能：")

    features = [
        {
            "name": "生成重点笔记",
            "emoji": "📑",
            "desc": "从上传的文件中提取考前重点笔记，支持多语言、多风格",
            "module": "summary_generator"
        },
    ]

    cols = st.columns(len(features))
    for idx, feature in enumerate(features):
        with cols[idx]:
            card_html = f"""
            <div style="
                background-color:#f5f5f5;
                border-radius:15px;
                padding:30px;
                text-align:center;
                height:200px;
                display:flex;
                flex-direction:column;
                justify-content:center;
                align-items:center;
                box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
                margin-bottom:20px;
            ">
                <div style="font-size:50px;">{feature['emoji']}</div>
                <div style="font-size:20px; font-weight:bold; margin-top:10px;">{feature['name']}</div>
                <div style="margin-top:10px;">{feature['desc']}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

            if st.button(f"进入 {feature['name']}", key=idx):
                st.session_state["page"] = feature["module"]

# ---------- 功能页 ----------
elif st.session_state["page"] == "summary_generator":
    sg.run()
    if st.button("⬅ 返回首页"):
        st.session_state["page"] = "home"
