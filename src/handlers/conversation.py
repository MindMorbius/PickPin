import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, DEFAULT_MODE, CHANNEL_ID, GROUP_ID
from services.ai_service import get_ai_response, get_vision_response
from prompts.prompts import (
    CLASSIFY_PROMPT, CHAT_PROMPT, TECH_PROMPT, NEWS_PROMPT, CULTURE_PROMPT, KNOWLEDGE_PROMPT, NORMAL_PROMPT
)
import asyncio
import re
from telegram.error import NetworkError, TimedOut
from utils.telegram_handler import TelegramMessageHandler
from utils.response_controller import ResponseController
from database.models import Message


logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    logger.info(f"类型：{update.message.chat.type}")

    try:
        # 保存或更新用户消息
        message = update.effective_message
        message_obj = Message(
            message_id=message.message_id,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            text=message.text or message.caption,
            type='user_message',
            chat_type=message.chat.type,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,
            metadata=update.to_dict()
        )
        await context.bot_data['db'].save_message(message_obj)
    except Exception as e:
        logger.error(f"Error saving message: {e}")  

    response_controller = ResponseController()
    
    # 分析消息并获取响应状态
    should_respond, chat_type, is_update = await response_controller.analyze_update(update, context)
    logger.info(f"should_respond: {should_respond}, chat_type: {chat_type}, is_update: {is_update}")
    
    if not should_respond:
        return
        
    message_text = get_message_text(message)
    
    # 检查原始消息和引用消息中的媒体文件
    has_media_result = has_media(message)
    reply_has_media = message.reply_to_message and has_media(message.reply_to_message)[0]
    
    if not message_text and not has_media_result[0] and not reply_has_media:
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

    # 如果引用消息包含媒体，优先处理引用消息的媒体
    if reply_has_media:
        await process_message_with_ai(message.reply_to_message, message_text, chat_type, handler, status_msg)
    else:
        await process_message_with_ai(message, message_text, chat_type, handler, status_msg)

def has_media(message) -> tuple[bool, str]:
    """
    检查消息是否包含媒体文件
    返回: (是否包含媒体, 媒体类型)
    """
    if message.photo:
        return True, "photo"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        return True, "photo"
    elif message.video:
        return True, "video"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('video/'):
        return True, "video"
    return False, ""

async def process_message_with_ai(message, message_text: str, chat_type: str, handler, status_msg) -> None:
    """处理消息并调用相应的AI服务"""
    has_media_file, media_type = has_media(message)
    
    if has_media_file:
        if media_type == "photo":
            # 获取图片文件
            if message.photo:
                file_id = message.photo[0].file_id  # 使用最小的图片
            else:
                file_id = message.document.file_id
                
            file = await handler.context.bot.get_file(file_id)
            file_url = file.file_path

            logger.info(f"图片地址 file_url: {file_url}")
            
            # 使用 vision response 处理
            prompt = CHAT_PROMPT if chat_type == 'private' else NORMAL_PROMPT
            await handler.stream_process_message(
                get_vision_response(message_text or "请分析这张图片", prompt, file_url),
                status_msg,
                parse_mode='HTML'
            )
        else:
            # 暂不支持的媒体类型
            await handler.send_notification(
                f"暂不支持处理{media_type}类型的文件",
                reply_to_message_id=message.message_id,
                auto_delete=True
            )
            return
    else:
        # 文本处理
        prompt = CHAT_PROMPT if chat_type == 'private' else NORMAL_PROMPT
        await handler.stream_process_message(
            get_ai_response(message_text, prompt),
            status_msg,
            parse_mode='HTML'
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