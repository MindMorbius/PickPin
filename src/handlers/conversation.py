import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, DEFAULT_MODE, CHANNEL_ID, GROUP_ID
from services.ai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_PROMPT, CHAT_PROMPT, TECH_PROMPT, NEWS_PROMPT, CULTURE_PROMPT, KNOWLEDGE_PROMPT, NORMAL_PROMPT
)
import asyncio
import re
from telegram.error import NetworkError, TimedOut
from utils.telegram_handler import TelegramMessageHandler


logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    logger.info(f"Received message: {update}")

    # 直接跳过频道消息
    if update.channel_post or update.edited_channel_post:
        logger.info("Skipping channel post")
        return

    # 获取消息对象
    message = update.edited_message or update.message
    if not message:
        logger.info("Skipping invalid message")
        return

    # 保存或更新用户消息
    message_data = {
        'message_id': message.message_id,
        'chat_id': message.chat.id,
        'user_id': message.from_user.id,
        'text': message.text or message.caption,
        'type': 'user_message',
        'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None,
        'metadata': {
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'is_edited': update.edited_message is not None
        }
    }
    await context.bot_data['message_db'].save_message(message_data)

    # 1. 过滤自动转发和机器人消息
    if message.is_automatic_forward:
        logger.info("Skipping automatic forward message")
        return

    chat = message.chat
    
    # 2. 私聊消息只接收管理员
    if chat.type == 'private':
        if not update.effective_user or update.effective_user.id != TELEGRAM_USER_ID:
            logger.info("Skipping non-admin private message")
            return
    
    # 3. 非私聊只接收指定群组消息
    elif chat.id != GROUP_ID:
        logger.info("Skipping message from non-target group")
        return
    
    # 群组消息处理
    if chat.id == GROUP_ID:
        handler.log_handler.log_message(update)
        # 检查是否@bot或引用bot消息
        is_mention = False
        is_reply_to_bot = False
        
        # 检查@提及
        if message.entities:
            for entity in message.entities:
                if entity.type == 'mention':
                    mention = message.text[entity.offset:entity.offset + entity.length]
                    if mention == '@rk_pin_bot':
                        is_mention = True
                        break
        
        # 检查是否回复bot消息
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.username == 'rk_pin_bot':
                is_reply_to_bot = True
        
        # 如果既没有@bot也没有回复bot消息，则不处理
        if not (is_mention or is_reply_to_bot):
            return

    message_text = get_message_text(message)
    
    if not message_text:
        await handler.send_notification(
            "无法处理此类型的消息",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
    
    status_msg = await handler.send_message(
        "正在处理消息...",
        reply_to_message_id=message.message_id
    )
    if not status_msg:
        return
    
    await handler.stream_process_message(
        get_ai_response(message_text, NORMAL_PROMPT),
        status_msg,
    )

def get_message_text(message) -> str:
    """
    从消息中提取文本内容，包括引用的消息或回复的消息
    """
    text = []
    
    # 处理引用/回复的消息
    if message.reply_to_message:
        quoted_text = ""
        if message.reply_to_message.text:
            quoted_text = message.reply_to_message.text
        elif message.reply_to_message.caption:
            quoted_text = message.reply_to_message.caption
            
        if quoted_text:
            # 如果是回复bot的消息，添加标记
            if (message.reply_to_message.from_user and 
                message.reply_to_message.from_user.is_bot and 
                message.reply_to_message.from_user.username == 'rk_pin_bot'):
                text.append(f"[上文]\n{quoted_text}")
            else:
                text.append(f"[引用]\n{quoted_text}")
    
    # 处理当前消息
    current_text = ""
    if message.text:
        current_text = message.text
        # 如果是群组消息且@了机器人，移除@部分
        if message.chat.type != 'private':
            for entity in message.entities or []:
                if entity.type == 'mention':
                    mention = message.text[entity.offset:entity.offset + entity.length]
                    current_text = current_text.replace(mention, '').strip()
    elif message.caption:
        current_text = message.caption
        
    # 处理文本实体（加粗、链接等）
    if current_text and (message.entities or message.caption_entities):
        entities = message.entities or message.caption_entities
        current_text = process_text_with_entities(current_text, entities)
    
    if current_text:
        text.append(f"[当前消息]\n{current_text}")
    
    return "\n\n".join(text).strip()

def process_text_with_entities(text: str, entities: list) -> str:
    """处理带格式的文本，保留格式信息"""
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
        elif entity.type == "italic":
            result.append(f"*{entity_text}*")
        elif entity.type == "code":
            result.append(f"`{entity_text}`")
        elif entity.type == "pre":
            result.append(f"```\n{entity_text}\n```")
        elif entity.type == "mention":
            continue  # 跳过@提及
        else:
            result.append(entity_text)
        
        last_offset = entity.offset + entity.length
    
    # 添加剩余文本
    result.append(text[last_offset:])
    return "".join(result)