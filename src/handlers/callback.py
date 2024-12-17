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
from utils.response_controller import ResponseController

logger = logging.getLogger(__name__)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    response_controller = ResponseController()
    query = update.callback_query
    
    # 检查用户权限
    if query.data in ['admin_approve', 'admin_reject']:
        if not await response_controller.is_user_admin(query.from_user.id, context):
            await query.answer("仅管理员可操作", show_alert=True)
            return
    
    # 检查用户是否在黑名单
    if await response_controller.is_user_blacklisted(query.from_user.id, context):
        await query.answer("你已被禁止使用此功能", show_alert=True)
        return
        
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
        # 从forward_origin获取原始消息信息
        original_message = context.user_data.get('original_message')
        
        # 从api_kwargs中获取forward_origin信息
        forward_origin = original_message.api_kwargs.get('forward_origin') if hasattr(original_message, 'api_kwargs') else None
        
        if forward_origin and forward_origin.get('type') == 'channel':
            # 如果是从频道转发的消息
            chat_info = forward_origin.get('chat', {})
            original_chat_id = chat_info.get('id')
            original_message_id = forward_origin.get('message_id')
        elif original_message.forward_from_chat:
            # 兼容旧的转发消息格式
            original_chat_id = original_message.forward_from_chat.id
            original_message_id = original_message.forward_from_message_id
        else:
            # 普通消息
            original_chat_id = original_message.chat_id
            original_message_id = original_message.message_id
        
        # 获取投票数据
        vote_data = await context.bot_data['db'].get_vote_by_original(
            original_message_id,
            original_chat_id
        )
        
        if not vote_data:
            await handler.send_notification("投票数据不存在")
            return
        
        # 更新分析内容
        classification_result = context.user_data.get('classification_result', '新投稿')  # 添加默认值
        await context.bot_data['db'].update_vote_content(
            vote_data.vote_id,
            query.message.text,  # 分析内容
            classification_result  # 投票介绍
        )
        
        # 转发原始消息到群组
        forwarded = await context.bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=original_message.chat_id,
            message_id=original_message.message_id
        )

        result_to_text = re.sub(r'<i>.*?</i>|<blockquote expandable>|</blockquote>', '', classification_result)
        
        # 发起投票
        vote_text = (
            f"{result_to_text}\n"
            f" | [用户 @{vote_data.username} 发起了投稿]\n"
        )
        
        vote_message = await context.bot.send_poll(
            chat_id=GROUP_ID,
            question=vote_text[:300],
            options=["👍 同意", "👎 反对"],
            is_anonymous=True,
            reply_to_message_id=forwarded.message_id,
            reply_markup=get_vote_buttons(),
            explanation=vote_data.analyse,
            explanation_parse_mode='HTML'
        )
        # 清除私聊中的按钮
        text_to_html = "<blockquote expandable>\n" + query.message.text + "\n</blockquote>"
        # await query.message.edit_text(text=query.message.text, parse_mode="HTML", reply_markup=None)
        await handler.edit_message(
            query.message,
            text_to_html,
            reply_markup=None,
            parse_mode='HTML',
        )
        # 更新投票消息ID
        await context.bot_data['db'].update_vote_message(
            vote_data.vote_id,
            vote_message.message_id,
            GROUP_ID
        )

    elif query.data in ['admin_approve', 'admin_reject']:
        vote_handler = VoteHandler(handler)
        try:
            # 设置投票消息ID
            context.chat_data['vote_message_id'] = query.message.message_id
            context.chat_data['vote_initiator'] = query.message.reply_to_message.from_user.id if query.message.reply_to_message else None
            
            # 停止投票
            await context.bot.stop_poll(GROUP_ID, query.message.message_id)
            
            if query.data == 'admin_approve':
                await vote_handler.admin_approve(context)
                # 发送新消息而不是编辑
                await handler.send_message(
                    f"✅ 管理员已通过",
                    reply_to_message_id=query.message.message_id
                )
            else:
                await vote_handler.admin_reject(context)
                await handler.send_message(
                    f"❌ 管理员已拒绝",
                    reply_to_message_id=query.message.message_id
                )
        except Exception as e:
            logger.error(f"Failed to handle admin action: {e}")
            await handler.send_notification(
                "操作失败，请重试",
                auto_delete=True
            )