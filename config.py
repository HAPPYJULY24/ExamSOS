# 负责加载 .env 配置
# config.py

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 读取环境变量
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 默认模型（你可以换成 gpt-4o-mini 或 gpt-3.5-turbo）
DEFAULT_MODEL = "gpt-4o-mini"

# === 安全检查 ===
if not OPENAI_API_KEY:
    raise ValueError("❌ 未检测到 OPENAI_API_KEY，请在 .env 文件中设置。")

# （可选）Anthropic API Key 不是必须的，所以不强制报错
