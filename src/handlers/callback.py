import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from services.openai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_HELP_TEXT,
    CLASSIFY_PROMPT, TECH_PROMPT, NEWS_PROMPT, 
    CULTURE_PROMPT, KNOWLEDGE_PROMPT, CHAT_PROMPT
)

logger = logging.getLogger(__name__)

def get_message_control_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
            InlineKeyboardButton("📮 投稿", callback_data='submit_content')
        ]
    ])

def get_prompt_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("科技", callback_data='prompt_tech'),
            InlineKeyboardButton("新闻", callback_data='prompt_news'),
            InlineKeyboardButton("文化", callback_data='prompt_culture'),
        ],
        [
            InlineKeyboardButton("知识", callback_data='prompt_knowledge'), 
            InlineKeyboardButton("通用", callback_data='prompt_chat'),
        ]
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'submit_content':
        await query.answer("投稿功能开发中...", show_alert=True)
        return
        
    elif query.data.startswith('prompt_'):
        prompt_type = query.data.replace('prompt_', '')
        prompts = {
            'tech': TECH_PROMPT,
            'news': NEWS_PROMPT, 
            'culture': CULTURE_PROMPT,
            'knowledge': KNOWLEDGE_PROMPT,
            'chat': CHAT_PROMPT
        }
        prompt = prompts.get(prompt_type)
        if prompt:
            original_text = context.user_data.get('original_text', '')
            message_id = context.user_data.get('generation_message_id')
            chat_id = context.user_data.get('generation_chat_id')
            
            if message_id and chat_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="正在生成内容..."
                    )
                    
                    last_text = ""
                    async for accumulated_text, should_update in get_ai_response(original_text, prompt):
                        if should_update:
                            try:
                                last_text = accumulated_text
                                await context.bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=message_id,
                                    text=accumulated_text
                                )
                            except Exception as e:
                                logger.warning(f"Failed to update message: {e}")
                    
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=last_text,
                        reply_markup=get_message_control_buttons()
                    )
                except Exception as e:
                    logger.error(f"Error generating content: {e}")
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="生成内容时出现错误，请重试",
                        reply_markup=get_message_control_buttons()
                    )

    elif query.data == 'delete_message':
        await query.message.delete()