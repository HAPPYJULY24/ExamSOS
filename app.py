# app.py
import streamlit as st
import modules.summary_generator as sg  # 预先导入模块

st.set_page_config(page_title="ExamSOS", layout="wide")

# ---------- 页面跳转逻辑 ----------
if "page" not in st.session_state:
    st.session_state["page"] = "home"

# ---------- 首页 ----------
if st.session_state["page"] == "home":
    st.title("📘 ExamSOS - 系统入口")
    st.markdown("请选择你要使用的功能：")

    # 功能列表
    features = [
        {
            "name": "生成重点笔记",
            "emoji": "📑",
            "desc": "从上传的文件中提取考前重点笔记，支持多语言、多风格",
            "module": "summary_generator"
        },
        # 未来可以添加更多功能
    ]

    cols = st.columns(len(features))
    for idx, feature in enumerate(features):
        with cols[idx]:
            # 正方形卡片 HTML
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

            # 点击卡片跳转
            if st.button(f"进入 {feature['name']}", key=idx):
                st.session_state["page"] = feature["module"]
                st.stop()  # 停止当前脚本，下一次渲染会显示功能模块

# ---------- 功能页面 ----------
elif st.session_state["page"] == "summary_generator":
    sg.run()  # 调用生成重点笔记模块