import os
from dotenv import load_dotenv

# 指定 .env.local 文件路径
load_dotenv('.env.local')

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
HTTP_PROXY = os.getenv("HTTP_PROXY")

# 验证必需的配置
if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID]):
    raise ValueError(
        "Missing required environment variables. Please check your .env file:\n"
        "TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID are required."
    )

DEFAULT_MODE = "classify"  # 可选值: "classify" 或 "chat"

AI_PROVIDER = os.getenv("AI_PROVIDER", "google")  # 可选值: google\siliconflow\zhipu

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# SiliconFlow 配置
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# Google Gemini 配置
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-exp-1206") # gemini-2.0-flash-exp  gemini-exp-1206

# 智谱AI 配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")
ZHIPU_VISION_MODEL = os.getenv("ZHIPU_VISION_MODEL", "glm-4v-flash")

CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002262761719")) # RKPin 频道
GROUP_ID = int(os.getenv("GROUP_ID", "-1001969921477")) # RKPin 群组