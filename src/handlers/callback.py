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
        try:
            # 获取原始消息和生成的内容
            original_message = query.message.reply_to_message
            generated_content = query.message.text
            
            if original_message and generated_content:
                # 先转发原始消息到频道
                original_sent = await context.bot.forward_message(
                    chat_id=-1002262761719,  # RKPin 频道
                    from_chat_id=original_message.chat_id,
                    message_id=original_message.message_id
                )
                
                try:
                    # 尝试用 Markdown 发送
                    await context.bot.send_message(
                        chat_id=-1002262761719,  # RKPin 频道
                        text=generated_content,
                        reply_to_message_id=original_sent.message_id,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    # 如果 Markdown 解析失败，就用纯文本发送
                    logger.warning(f"Failed to send with Markdown: {e}")
                    await context.bot.send_message(
                        chat_id=-1002262761719,  # RKPin 频道
                        text=generated_content,
                        reply_to_message_id=original_sent.message_id
                    )
                    
                await query.message.reply_text("投稿成功!")
            else:
                await query.message.reply_text("未找到内容，无法投稿")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await query.message.reply_text("投稿失败，请重试")

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
                    logger.error(f"Failed to generate content: {e}")
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="生成内容失败，请重试"
                    )

    elif query.data == 'delete_message':
        await query.message.delete()