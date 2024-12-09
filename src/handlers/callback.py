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
                        parse_mode='Markdown',
                        chat_id=CHANNEL_ID
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
                            await handler.edit_message(generation_message, accumulated_text)
                    
                    await handler.edit_message(
                        generation_message,
                        last_text,
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
        # 获取原始消息和分类结果
        original_message = context.user_data.get('original_message')
        classification_result = context.user_data.get('classification_result')
        generated_content = query.message.text
        
        if not all([original_message, classification_result, generated_content]):
            await handler.send_notification(
                "无法发起投票，信息已失效",
                reply_to_message_id=query.message.message_id
            )
            return
            
        # 在群组中发起投票
        vote_text = (
            f"{classification_result}\n\n"
            f"用户 {query.from_user.first_name} （@{query.from_user.username}）发起了投稿\n"
            "请使用 👍 或 👎 表情回应此消息参与投票"
        )
        vote_msg = await handler.send_message(
            vote_text,
            reply_to_message_id=original_message.message_id,
            reply_markup=get_vote_buttons(),
            chat_id=GROUP_ID
        )
        
        # 保存投票相关信息到 chat_data
        context.chat_data['vote_message'] = vote_msg
        context.chat_data['vote_content'] = generated_content
        context.chat_data['vote_initiator'] = query.from_user.id
        context.chat_data['original_message'] = original_message
        
        # 清除私聊中的按钮
        await query.message.edit_text(text=query.message.text)

    elif query.data in ['admin_approve', 'admin_reject']:
        if query.from_user.id != TELEGRAM_USER_ID:
            await query.answer("仅管理员可操作", show_alert=False)
            return
            
        if query.data == 'admin_approve':
            try:
                # 从 chat_data 获取数据
                original_message = context.chat_data.get('original_message')
                generated_content = context.chat_data.get('vote_content')
                
                if not all([original_message, generated_content]):
                    await handler.send_notification(
                        "投稿数据已失效，请重新发起投稿",
                        reply_to_message_id=query.message.message_id
                    )
                    return
                    
                # 转发原始消息到频道
                original_sent = await context.bot.forward_message(
                    chat_id=CHANNEL_ID,
                    from_chat_id=original_message.chat_id,
                    message_id=original_message.message_id
                )
                
                # 发送生成的内容
                try:
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=generated_content,
                        reply_to_message_id=original_sent.message_id,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    # 如果 Markdown 解析失败，用纯文本发送
                    logger.warning(f"Failed to send with Markdown: {e}")
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=generated_content,
                        reply_to_message_id=original_sent.message_id
                    )
            except Exception as e:
                logger.error(f"Failed to publish content: {e}")
                await handler.send_notification(
                    "发布内容失败，请重试",
                    reply_to_message_id=query.message.message_id
                )
        else:
            user_id = context.chat_data.get('vote_initiator')
            if user_id:
                await context.bot.send_notification(
                    chat_id=user_id,
                    text="感谢你的投稿，虽然没成功，不是你的问题哦",
                    auto_delete=False
                )
                
        # 清理投票消息
        vote_msg = context.chat_data.get('vote_message')
        if vote_msg:
            await vote_msg.delete()
