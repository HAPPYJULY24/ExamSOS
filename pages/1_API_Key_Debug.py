# pages/1_🔑_API_Key_Debug.py
import os
import streamlit as st

st.title("🔑 API Key 调试工具")

def check_api_key():
    # 1. 从 Streamlit Secrets 读取
    st.write("🔍 尝试从 st.secrets 读取...")
    api_from_secrets = st.secrets.get("OPENAI_API_KEY") if "OPENAI_API_KEY" in st.secrets else None
    st.write(f"st.secrets['OPENAI_API_KEY'] = {api_from_secrets}")

    # 2. 从环境变量读取
    st.write("🔍 尝试从 os.environ 读取...")
    api_from_env = os.getenv("OPENAI_API_KEY")
    st.write(f"os.environ['OPENAI_API_KEY'] = {api_from_env}")

    # 3. 判断优先使用哪一个
    if api_from_secrets:
        st.success("✅ 正在使用 st.secrets 中的 API Key")
        return api_from_secrets
    elif api_from_env:
        st.success("✅ 正在使用 os.environ 中的 API Key")
        return api_from_env
    else:
        st.error("❌ 没有找到 OPENAI_API_KEY，请检查配置")
        return None

if st.button("检查 API Key"):
    key = check_api_key()
    if key:
        st.write("当前读取到的 Key 长度：", len(key))
        st.write("前 5 位：", key[:5], "...")
