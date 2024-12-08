import os
from dotenv import load_dotenv

# 指定 .env.local 文件路径
load_dotenv('.env.local')

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
HTTP_PROXY = os.getenv("HTTP_PROXY")

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
if not OPENAI_BASE_URL.endswith("/v1"):
    OPENAI_BASE_URL = OPENAI_BASE_URL.rstrip("/") + "/v1"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# 验证必需的配置
if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, OPENAI_API_KEY]):
    raise ValueError(
        "Missing required environment variables. Please check your .env file:\n"
        "TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, and OPENAI_API_KEY are required."
    )

DEFAULT_MODE = "classify"  # 可选值: "classify" 或 "chat"

# 在现有配置后添加
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-exp-1206")

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # 可选值: openai, gemini

CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002262761719")) # RKPin 频道
GROUP_ID = int(os.getenv("GROUP_ID", "-1001969921477")) # RKPin 群组