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
        [InlineKeyboardButton("🗑️ 清除", callback_data='delete_message')]
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
            InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
        ]
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('prompt_'):
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
            original_message_id = query.message.reply_to_message.message_id
            async for accumulated_text, should_update in get_ai_response(original_text, prompt):
                if should_update:
                    try:
                        await query.message.delete()
                        await query.message.reply_text(
                            text=accumulated_text,
                            reply_to_message_id=original_message_id,
                            reply_markup=get_prompt_buttons()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
                        
    elif query.data == 'delete_message':
        await query.message.delete()