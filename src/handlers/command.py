import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, DEFAULT_MODE

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != TELEGRAM_USER_ID:
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await update.message.reply_text("抱歉，你没有使用此机器人的权限。")
        return
    
    await update.message.reply_text(
        "👋 你好！我是 PickPin 的镜界信息助手\n\n"
        "直接发送消息给我，我会:\n"
        "1. 分析内容并进行分类\n"
        "2. 使用合适的解释器生成内容\n\n"
        "你也可以手动选择使用不同的解释器"
    )

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        await update.message.reply_text(f"你的用户 ID 是: {user.id}")
    else:
        await update.message.reply_text(
            f"群组/频道 ID: {chat.id}\n"
            f"类型: {chat.type}\n"
            f"名称: {chat.title}\n"
            f"你的用户 ID: {user.id}"
        )