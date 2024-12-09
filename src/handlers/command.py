import logging
from telegram import Update, Chat
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == 'private':
        if user_id == TELEGRAM_USER_ID:
            await update.message.reply_text(
                "👋 管理员你好！我是 PickPin 机器人\n\n"
                "我可以帮助你处理和投稿信息到 RKPin 频道\n\n"
                "直接发送消息给我，我会:\n"
                "1. 智能分析内容并分类\n" 
                "2. 生成适合发布的内容格式"
            )
    elif chat.id == -1001969921477:
        await update.message.reply_text(
            "👋 你好！我是 PickPin 机器人\n\n"
            "你可以直接发送消息给我:\n"
            "1. 智能分析内容并分类\n" 
            "2. 生成适合发布的内容格式"
        )

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        if user.id == TELEGRAM_USER_ID:
            await update.message.reply_text(f"你的用户 ID 是: {user.id}")
    elif chat.id == -1001969921477:
        await update.message.reply_text(
            f"群组 ID: {chat.id}\n"
            f"类型: {chat.type}\n"
            f"名称: {chat.title}\n"
            f"你的用户 ID: {user.id}"
        )