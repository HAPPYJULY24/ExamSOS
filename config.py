# config.py
# 负责加载配置，包括本地 .env 和 Streamlit Secrets / 系统环境变量

import os
from dotenv import load_dotenv

# 尝试加载本地 .env（仅本地调试时有用）
load_dotenv()

# ========== 优先级 ==========
# 1. Streamlit Secrets
# 2. 系统环境变量
# 3. 本地 .env
# ===========================
try:
    import streamlit as st
    if "OPENAI_API_KEY" in st.secrets:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
        key_source = "Streamlit Secrets"
    else:
        OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        key_source = "os.environ"
except ImportError:
    # 如果不是在 Streamlit 环境中运行
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    key_source = "os.environ"

# Anthropic Key（可选）
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ===== 校验 API Key =====
if not OPENAI_API_KEY:
    raise ValueError("❌ 未检测到 OPENAI_API_KEY，请在 .env、环境变量 或 Streamlit Secrets 中设置。")

# 打印调试信息（不会暴露完整 Key）
print(f"✅ 正在使用 {key_source} 中的 OPENAI_API_KEY")
print(f"当前读取到的 Key 长度：{len(OPENAI_API_KEY)}")
print(f"前 5 位：{OPENAI_API_KEY[:5]}...")

# 默认模型（可修改为 gpt-4o-mini / gpt-4o / gpt-3.5-turbo）
DEFAULT_MODEL = "gpt-4o-mini"

