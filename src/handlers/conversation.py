import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, DEFAULT_MODE
from handlers.callback import get_classification_keyboard, get_message_control_buttons
from services.openai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_PROMPT, CHAT_PROMPT
)


logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info(f"Received message: {update}")
    # 检查是否是频道消息
    if update.channel_post:
        chat = update.channel_post.chat
        # 直接处理频道消息，无需权限检查
        message = update.channel_post
    else:
        # 检查是否是自动转发的频道消息
        if update.message and update.message.is_automatic_forward:
            message = update.message
        else:
            user_id = update.effective_user.id
            if user_id != TELEGRAM_USER_ID:
                await update.message.reply_text("抱歉，你没有使用此机器人的权限。")
                return
            message = update.message

    try:
        # 获取用户设置的默认模式，如果没有则使用聊天模式
        mode = context.user_data.get('default_mode', DEFAULT_MODE)
        # 如果当前有临时模式，优先使用临时模式
        mode = context.user_data.get('mode', mode)
        # logger.info(f"Received message in {mode} mode")
        
        # 获取消息文本，只处理文本内容
        message = update.channel_post if update.channel_post else update.message
        message_text = ""
        
        # 处理文本和实体
        def process_text_with_entities(text, entities):
            if not text or not entities:
                return text
            
            # 按位置排序实体
            sorted_entities = sorted(entities, key=lambda e: e.offset)
            result = []
            last_offset = 0
            
            for entity in sorted_entities:
                # 添加实体前的文本
                result.append(text[last_offset:entity.offset])
                
                # 获取实体文本
                entity_text = text[entity.offset:entity.offset + entity.length]
                
                # 根据实体类型处理
                if entity.type == "text_link":
                    result.append(f"{entity_text}({entity.url})")
                elif entity.type == "bold":
                    result.append(f"**{entity_text}**")
                else:
                    result.append(entity_text)
                
                last_offset = entity.offset + entity.length
            
            # 添加剩余文本
            result.append(text[last_offset:])
            return "".join(result)
        
        # 优先获取文本内容
        if message.text:
            message_text = process_text_with_entities(message.text, message.entities)
        # 如果没有文本，尝试获取caption
        elif message.caption:
            message_text = process_text_with_entities(message.caption, message.caption_entities)
            
        # 如果是转发消息，添加来源信息
        if message.forward_from or message.forward_from_chat:
            if message.forward_from:
                message_text += f"\n\n转发自用户: {message.forward_from.first_name}"
            elif message.forward_from_chat:
                chat_type = message.forward_from_chat.type
                chat_title = message.forward_from_chat.title
                message_text += f"\n\n转发自{chat_type}: {chat_title}"
        
        # 处理回复消息
        if message.reply_to_message:
            reply_text = ""
            if message.reply_to_message.text:
                reply_text = process_text_with_entities(
                    message.reply_to_message.text,
                    message.reply_to_message.entities
                )
            elif message.reply_to_message.caption:
                reply_text = process_text_with_entities(
                    message.reply_to_message.caption,
                    message.reply_to_message.caption_entities
                )
            
            if reply_text:
                message_text = f"回复消息：\n{reply_text}\n\n当前消息：\n{message_text}"

        if not message_text:
            await update.message.reply_text("抱歉，无法处理此类型的消息。请发送文本消息。")
            return

        # logger.info(f"Processing message: {message_text}")
        reply_message = await update.message.reply_text("思考中...")
        
        # 保存原始文本
        context.user_data['original_text'] = message_text
        
        if mode == 'classify':
            async for accumulated_text, should_update in get_ai_response(message_text, CLASSIFY_PROMPT):
                if should_update:
                    try:
                        context.user_data['classification'] = accumulated_text
                        # 合并分类键盘和控制按钮
                        classify_keyboard = get_classification_keyboard().inline_keyboard
                        control_buttons = get_message_control_buttons().inline_keyboard
                        combined_keyboard = InlineKeyboardMarkup(classify_keyboard + control_buttons)
                        
                        await reply_message.edit_text(
                            text=accumulated_text,
                            reply_markup=combined_keyboard
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
        else:
            async for accumulated_text, should_update in get_ai_response(message_text, CHAT_PROMPT):
                if should_update:
                    try:
                        await reply_message.edit_text(
                            text=accumulated_text,
                            reply_markup=get_message_control_buttons()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
                    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        await update.message.reply_text("抱歉，处理您的消息时出现错误。") 