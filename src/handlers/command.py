import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != TELEGRAM_USER_ID:
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await update.message.reply_text("抱歉，你没有使用此机器人的权限。")
        return
        
    main_keyboard = [
        [
            InlineKeyboardButton("信息分类", callback_data='classify'),
            InlineKeyboardButton("通用聊天", callback_data='chat'),
        ],
        [InlineKeyboardButton("设置菜单", callback_data='settings')],
        [
            InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
            InlineKeyboardButton("📝 反馈", callback_data='feedback'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(main_keyboard)
    
    await update.message.reply_text(
        "👋 你好！我是一个 AI 助手，请选择以下功能：\n\n"
        "🔍 信息分类：帮你分析新闻、咨询、热点等内容\n"
        "💭 通用聊天：随意聊天，回答问题\n"
        "⚙️ 设置菜单：调整机器人配置",
        reply_markup=reply_markup
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