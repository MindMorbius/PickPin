import logging
from telegram import Update, Chat
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID
from services.ai_service import get_ai_response
from prompts.prompts import CLASSIFY_PROMPT, SUMMARY_PROMPT
from handlers.callback import get_message_control_buttons, get_prompt_buttons

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

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    
    if not message.reply_to_message:
        await message.reply_text("请引用要分析的消息使用此命令")
        return
        
    if chat.type == 'private':
        if update.effective_user.id != TELEGRAM_USER_ID:
            return
    elif chat.id != -1001969921477:
        return
        
    reply_text = ""
    if message.reply_to_message.text:
        reply_text = message.reply_to_message.text
    elif message.reply_to_message.caption:
        reply_text = message.reply_to_message.caption
        
    if not reply_text:
        await message.reply_text("无法分析此类型的消息")
        return
        
    # 发送分析中提示
    analyzing_msg = await message.reply_text("正在分析内容...")
    
    try:
        last_text = ""
        async for classification_text, should_update in get_ai_response(reply_text, CLASSIFY_PROMPT):
            if should_update:
                try:
                    last_text = classification_text
                    await analyzing_msg.edit_text(text=classification_text)
                except Exception as e:
                    logger.warning(f"Failed to update analysis: {e}")
                    
        await analyzing_msg.edit_text(
            text=last_text,
            reply_markup=get_prompt_buttons()
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await analyzing_msg.edit_text("分析失败，请重试")

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.message
    
    if not message.reply_to_message:
        await message.reply_text("请引用要总结的消息使用此命令")
        return
        
    if chat.type == 'private':
        if update.effective_user.id != TELEGRAM_USER_ID:
            return
    elif chat.id != -1001969921477:
        return
        
    reply_text = ""
    if message.reply_to_message.text:
        reply_text = message.reply_to_message.text
    elif message.reply_to_message.caption:
        reply_text = message.reply_to_message.caption
        
    if not reply_text:
        await message.reply_text("无法总结此类型的消息")
        return
        
    # 发送总结中提示
    summarizing_msg = await message.reply_text("正在总结内容...")
    
    try:
        last_text = ""
        async for summary_text, should_update in get_ai_response(reply_text, SUMMARY_PROMPT):
            if should_update:
                try:
                    last_text = summary_text
                    await summarizing_msg.edit_text(text=summary_text)
                except Exception as e:
                    logger.warning(f"Failed to update summary: {e}")
                    
        await summarizing_msg.edit_text(
            text=last_text,
        )
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        await summarizing_msg.edit_text("总结失败，请重试")