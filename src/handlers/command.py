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
import asyncio

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == 'private':
        if user_id == TELEGRAM_USER_ID:
            await handler.reply_to_command(
                "👋 管理员你好！我是 PickPin 机器人\n\n"
                "我可以帮助你处理和投稿信息到 RKPin 频道\n\n",
                auto_delete=False
            )
    elif chat.id == GROUP_ID:
        await handler.reply_to_command(
            "👋 你好！我是 PickPin 机器人\n\n",
            auto_delete=False
        )

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        if user.id == TELEGRAM_USER_ID:
            await handler.reply_to_command(
                f"你的用户 ID 是: {user.id}",
                auto_delete=False
            )
    elif chat.id == GROUP_ID:
        await handler.reply_to_command(
            f"群组 ID: {chat.id}\n"
            f"类型: {chat.type}\n"
            f"名称: {chat.title}\n"
            f"你的用户 ID: {user.id}",
            auto_delete=False
        )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    message = update.message
    user = update.effective_user
    
    if not message.reply_to_message:
        await handler.reply_to_command(
            "请引用要分析的消息使用此命令",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    if chat.type == 'private':
        if user.id != TELEGRAM_USER_ID:
            return
    elif chat.id != GROUP_ID:
        return
        
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.reply_to_command(
            "无法分析此类型的消息",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return

    # 在群组中发送提示并删除
    if chat.id == GROUP_ID:
        await handler.reply_to_command(
            "已开始分析，请前往 @rk_pin_bot 查看",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
    
    try:
        last_text = ""
        prompt_type = None
        analyzing_msg = await handler.send_message(
            "正在分析内容...",
            chat_id=user.id
        )
        
        async for classification_text, should_update in get_ai_response(reply_text, CLASSIFY_PROMPT):
            if should_update:
                last_text = classification_text
                await handler.edit_message(analyzing_msg, classification_text, parse_mode='Markdown')
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
                await handler.edit_message(generation_msg, content_text, parse_mode='Markdown')
        
        await handler.edit_message(
            generation_msg,
            generated_text,
            reply_markup=get_content_options_buttons(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await handler.send_notification(
            "分析失败，请重试",
            chat_id=user.id,
            reply_to_message_id=message.message_id,
            auto_delete=False
        )

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    message = update.message
    
    if not message.reply_to_message:
        await handler.reply_to_command(
            "请引用要总结的消息使用此命令",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    if chat.type == 'private':
        if update.effective_user.id != TELEGRAM_USER_ID:
            return
    elif chat.id != GROUP_ID:
        return
        
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.reply_to_command(
            "无法总结此类型的消息",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    summarizing_msg = await handler.send_message("正在总结内容...", reply_to_message_id=message.reply_to_message.message_id, delete_command=True)
    
    try:
        last_text = ""
        async for summary_text, should_update in get_ai_response(reply_text, SUMMARY_PROMPT):
            if should_update and summary_text != last_text:
                last_text = summary_text
                await handler.edit_message(summarizing_msg, summary_text, parse_mode='Markdown')
                    
        if last_text != summarizing_msg.text:
            await handler.edit_message(summarizing_msg, last_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        await handler.send_notification(
            "总结失败，请重试",
            chat_id=user.id,
            reply_to_message_id=message.message_id,
            auto_delete=False
        )