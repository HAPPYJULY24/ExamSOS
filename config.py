# 负责加载 .env 配置
# config.py

import os
from dotenv import load_dotenv

import os
from dotenv import load_dotenv

# 尝试从本地 .env 加载
load_dotenv()

# 优先从环境变量（Streamlit Secrets 或 OS 环境）读取
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ 未检测到 OPENAI_API_KEY，请在 .env 文件中设置或在 Streamlit Secrets 添加。")

# 默认模型
DEFAULT_MODEL = "gpt-4o-mini"

