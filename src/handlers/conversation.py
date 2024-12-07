import logging
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID
from handlers.callback import get_classification_keyboard
from services.openai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_PROMPT, CHAT_PROMPT
)


logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != TELEGRAM_USER_ID:
        await update.message.reply_text("抱歉，你没有使用此机器人的权限。")
        return

    try:
        mode = context.user_data.get('mode', 'chat')
        logger.info(f"Received message in {mode} mode")
        
        # 获取消息文本，只处理文本内容
        message = update.message
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

        if not message_text:
            await update.message.reply_text("抱歉，无法处理此类型的消息。请发送文本消息。")
            return

        logger.info(f"Processing message: {message_text}")
        reply_message = await update.message.reply_text("思考中...")
        
        # 保存原始文本
        context.user_data['original_text'] = message_text
        
        if mode == 'classify':
            async for accumulated_text, should_update in get_ai_response(message_text, CLASSIFY_PROMPT):
                if should_update:
                    try:
                        context.user_data['classification'] = accumulated_text
                        await reply_message.edit_text(
                            text=accumulated_text,
                            reply_markup=get_classification_keyboard()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
        else:
            async for accumulated_text, should_update in get_ai_response(message_text, CHAT_PROMPT):
                if should_update:
                    try:
                        await reply_message.edit_text(accumulated_text)
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
                    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        await update.message.reply_text("抱歉，处理您的消息时出现错误。") 