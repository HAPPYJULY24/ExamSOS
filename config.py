# config.py
import os
from dotenv import load_dotenv

# 尝试加载本地 .env（仅本地调试时有用）
load_dotenv()

OPENAI_API_KEY = None
key_source = None

try:
    import streamlit as st
    # ✅ 先判断 st.secrets 是否真的有东西
    if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
        key_source = "Streamlit Secrets"
except Exception:
    # 本地环境直接跳过
    pass

# 如果没取到，就用环境变量
if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    key_source = "os.environ"

# Anthropic Key（可选）
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ===== 校验 API Key =====
if not OPENAI_API_KEY:
    raise ValueError("❌ 未检测到 OPENAI_API_KEY，请在 .env、环境变量 或 Streamlit Secrets 中设置。")

# 打印调试信息（不会暴露完整 Key）
print(f"✅ 正在使用 {key_source} 中的 OPENAI_API_KEY")
print(f"当前读取到的 Key 长度：{len(OPENAI_API_KEY)}")
print(f"前 5 位：{OPENAI_API_KEY[:5]}...")

# 默认模型
DEFAULT_MODEL = "gpt-4o-mini"
