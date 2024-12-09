import logging
from telegram import Update, Chat
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, CHANNEL_ID, GROUP_ID
from services.ai_service import get_ai_response
from prompts.prompts import CLASSIFY_PROMPT, SUMMARY_PROMPT
from utils.buttons import (
    get_content_options_buttons,
    get_prompt_selection_buttons
)
from prompts.prompts import TECH_PROMPT, NEWS_PROMPT, CULTURE_PROMPT, KNOWLEDGE_PROMPT, CHAT_PROMPT
from utils.telegram_handler import TelegramMessageHandler
import re

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == 'private':
        if user_id == TELEGRAM_USER_ID:
            await handler.send_message(
                "👋 管理员你好！我是 PickPin 机器人\n\n"
                "我可以帮助你处理和投稿信息到 RKPin 频道\n\n"
                "直接发送消息给我，我会:\n"
                "1. 智能分析内容并分类\n" 
                "2. 生成适合发布的内容格式"
            )
    elif chat.id == GROUP_ID:
        await handler.send_message(
            "👋 你好！我是 PickPin 机器人\n\n"
            "你可以直接发送消息给我:\n"
            "1. 智能分析内容并分类\n" 
            "2. 生成适合发布的内容格式"
        )

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        if user.id == TELEGRAM_USER_ID:
            await handler.send_message(f"你的用户 ID 是: {user.id}")
    elif chat.id == GROUP_ID:
        await handler.send_message(
            f"群组 ID: {chat.id}\n"
            f"类型: {chat.type}\n"
            f"名称: {chat.title}\n"
            f"你的用户 ID: {user.id}"
        )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    message = update.message
    user = update.effective_user
    
    if not message.reply_to_message:
        await handler.send_message("请引用要分析的消息使用此命令")
        return
        
    if chat.type == 'private':
        if user.id != TELEGRAM_USER_ID:
            return
    elif chat.id != GROUP_ID:
        return
        
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.send_message("无法分析此类型的消息")
        return
        
    analyzing_msg = await handler.send_message("正在分析内容...")
    if not analyzing_msg:
        return
    
    try:
        last_text = ""
        prompt_type = None
        async for classification_text, should_update in get_ai_response(reply_text, CLASSIFY_PROMPT):
            if should_update:
                last_text = classification_text
                await handler.edit_message(analyzing_msg, classification_text)
                if 'TECH_PROMPT' in classification_text:
                    selected_prompt = TECH_PROMPT
                elif 'NEWS_PROMPT' in classification_text:
                    selected_prompt = NEWS_PROMPT
                elif 'CULTURE_PROMPT' in classification_text:
                    selected_prompt = CULTURE_PROMPT
                elif 'KNOWLEDGE_PROMPT' in classification_text:
                    selected_prompt = KNOWLEDGE_PROMPT
                else:
                    selected_prompt = CHAT_PROMPT
        
        context.user_data['original_message'] = message.reply_to_message
        context.user_data['classification_result'] = last_text
        context.user_data['prompt_type'] = prompt_type
        
        generated_text = ""
        generation_msg = await handler.send_message(
            "正在生成内容...",
            chat_id=user.id
        )
        
        async for content_text, should_update in get_ai_response(reply_text, selected_prompt):
            if should_update:
                generated_text = content_text
                await handler.edit_message(generation_msg, content_text)
        
        await handler.edit_message(
            generation_msg,
            generated_text,
            reply_markup=get_content_options_buttons()
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await handler.edit_message(analyzing_msg, "分析失败，请重试")

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    message = update.message
    
    if not message.reply_to_message:
        await handler.send_message("请引用要总结的消息使用此命令")
        return
        
    if chat.type == 'private':
        if update.effective_user.id != TELEGRAM_USER_ID:
            return
    elif chat.id != GROUP_ID:
        return
        
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.send_message("无法总结此类型的消息")
        return
        
    summarizing_msg = await handler.send_message("正在总结内容...")
    
    try:
        last_text = ""
        async for summary_text, should_update in get_ai_response(reply_text, SUMMARY_PROMPT):
            if should_update and summary_text != last_text:
                last_text = summary_text
                await handler.edit_message(summarizing_msg, summary_text)
                    
        if last_text != summarizing_msg.text:
            await handler.edit_message(summarizing_msg, last_text)
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        await handler.edit_message(summarizing_msg, "总结失败，请重试")