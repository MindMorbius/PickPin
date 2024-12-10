import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from services.ai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_HELP_TEXT,
    CLASSIFY_PROMPT, TECH_PROMPT, NEWS_PROMPT, 
    CULTURE_PROMPT, KNOWLEDGE_PROMPT, CHAT_PROMPT
)
from config.settings import CHANNEL_ID, GROUP_ID, TELEGRAM_USER_ID
from handlers.conversation import TelegramMessageHandler
from utils.buttons import (
    get_content_options_buttons,
    get_vote_buttons
)
from handlers.vote_handler import VoteHandler

logger = logging.getLogger(__name__)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    query = update.callback_query
    await query.answer()

    if query.data == 'submit_content':
        try:
            original_message = query.message.reply_to_message
            generated_content = query.message.text
            
            if original_message and generated_content:
                original_sent = await handler.forward_message(
                    CHANNEL_ID,
                    original_message
                )
                
                try:
                    await handler.send_message(
                        generated_content,
                        reply_to_message_id=original_sent.message_id,
                        chat_id=CHANNEL_ID,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Failed to send with Markdown: {e}")
                    await handler.send_message(
                        generated_content,
                        reply_to_message_id=original_sent.message_id,
                        chat_id=CHANNEL_ID
                    )
                    
                await handler.send_notification("投稿成功!", auto_delete=True)
            else:
                await handler.send_notification("未找到内容，无法投稿", auto_delete=True)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await handler.send_notification("投稿失败，请重试", auto_delete=True)

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
            original_message = context.user_data.get('original_message')
            
            if original_message:
                # 发送新消息而不是编辑旧消息
                generation_message = await original_message.reply_text(
                    "正在生成内容...",
                    reply_to_message_id=original_message.message_id
                )
                
                # 保存新消息的ID用于后续更新
                context.user_data['generation_message_id'] = generation_message.message_id
                context.user_data['generation_chat_id'] = generation_message.chat_id
                
                try:
                    last_text = ""
                    async for accumulated_text, should_update in get_ai_response(original_text, prompt):
                        if should_update:
                            last_text = accumulated_text
                            await handler.edit_message(generation_message, accumulated_text, parse_mode='Markdown')
                    
                    await handler.edit_message(
                        generation_message,
                        last_text,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to generate content: {e}")
                    await handler.send_notification(
                        "生成内容失败，请重试",
                        reply_to_message_id=generation_message.message_id,
                        auto_delete=True
                    )

    elif query.data == 'delete_message':
        await query.message.delete()

    elif query.data == 'keep_content':
        await query.message.edit_text(text=query.message.text)
        
    elif query.data == 'start_vote':
        original_message = context.user_data.get('original_message')
        classification_result = context.user_data.get('classification_result')
        generated_content = query.message.text
        
        if not all([original_message, classification_result, generated_content]):
            await handler.send_notification(
                "无法发起投票，信息已失效",
                reply_to_message_id=query.message.message_id
            )
            return
        
        vote_handler = VoteHandler(handler)
        await vote_handler.start_vote(
            context,
            original_message,
            generated_content,
            classification_result
        )
        
        # 清除私聊中的按钮
        # await query.message.edit_text(text=query.message.text)

    elif query.data in ['admin_approve', 'admin_reject']:
        if query.from_user.id != TELEGRAM_USER_ID:
            await query.answer("仅管理员可操作", show_alert=True)
            return

        vote_handler = VoteHandler(handler)
        try:
            # 停止投票
            vote_message_id = context.chat_data.get('vote_message_id')
            if vote_message_id:
                await context.bot.stop_poll(GROUP_ID, vote_message_id)
            
            if query.data == 'admin_approve':
                await vote_handler.admin_approve(context)
                await query.message.edit_text(
                    f"{query.message.text}\n\n✅ 管理员已通过",
                    reply_markup=None
                )
            else:
                await vote_handler.admin_reject(context)
                await query.message.edit_text(
                    f"{query.message.text}\n\n❌ 管理员已拒绝",
                    reply_markup=None
                )
        except Exception as e:
            logger.error(f"Failed to handle admin action: {e}")
            await handler.send_notification(
                "操作失败，请重试",
                auto_delete=True
            )