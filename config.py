# config.py
# 负责加载配置，包括本地 .env 和 Streamlit Secrets / 系统环境变量

import os
from dotenv import load_dotenv

# 尝试加载本地 .env（本地运行可用）
load_dotenv()

# 优先从环境变量（Streamlit Secrets 或系统环境变量）读取
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# 校验 API Key
if not OPENAI_API_KEY:
    raise ValueError(
        "❌ 未检测到 OPENAI_API_KEY，请在本地 .env 文件或 Streamlit Secrets 中设置。"
    )

# 默认模型（可修改为 gpt-4o-mini / gpt-4o / gpt-3.5-turbo）
DEFAULT_MODEL = "gpt-4o-mini"
