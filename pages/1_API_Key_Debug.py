# pages/1_🔑_API_Key_Debug.py
import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# ✅ 本地运行时加载 .env
load_dotenv()

st.title("🔑 API Key 调试工具")

def get_api_key():
    """优先从 st.secrets 获取，其次 .env / os.environ"""
    api_from_secrets = None
    try:
        if "OPENAI_API_KEY" in st.secrets:
            api_from_secrets = st.secrets["OPENAI_API_KEY"]
    except Exception:
        # 本地没有 secrets.toml 的情况，直接忽略
        pass

    api_from_env = os.getenv("OPENAI_API_KEY")

    if api_from_secrets:
        st.success("✅ 使用 st.secrets 中的 API Key")
        return api_from_secrets, "st.secrets"
    elif api_from_env:
        st.success("✅ 使用 .env / os.environ 中的 API Key")
        return api_from_env, ".env / os.environ"
    else:
        st.error("❌ 没有找到 OPENAI_API_KEY，请检查配置")
        return None, None

def test_openai_api(api_key: str):
    """测试 API 是否可用"""
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0
        )
        reply = resp.choices[0].message.content
        return f"✅ API 调用成功，模型回复: {reply}"
    except Exception as e:
        return f"❌ API 调用失败: {str(e)}"

if st.button("检查 API Key 并测试 API"):
    key, source = get_api_key()
    if key:
        st.write("🔑 当前 API 来源：", source)
        st.write("当前读取到的 Key 长度：", len(key))
        st.write("前 5 位：", key[:5], "...")
        
        result = test_openai_api(key)
        st.subheader("API 测试结果：")
        st.write(result)
