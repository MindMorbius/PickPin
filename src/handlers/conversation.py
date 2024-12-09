import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, DEFAULT_MODE
from handlers.callback import get_message_control_buttons, get_prompt_buttons
from services.ai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_PROMPT, CHAT_PROMPT, TECH_PROMPT, NEWS_PROMPT, CULTURE_PROMPT, KNOWLEDGE_PROMPT, NORMAL_PROMPT
)
import asyncio
import re
from telegram.error import NetworkError, TimedOut


logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info(f"Received message: {update}")

    if update.message.forward_signature == 'RKPin Bot':
        logger.info(f"不回复bot消息")
        return
    
    if update.message.is_automatic_forward:
        logger.info(f"不回复自动转发消息")
        return
    
    user_id = update.effective_user.id
    chat = update.effective_chat
    
    if chat.type == 'private' and user_id != TELEGRAM_USER_ID:
        return
        
    if chat.type != 'private' and chat.id != -1001969921477:
        return
    
    message = update.message
    
    # 检查群组消息是否@了机器人或者是回复bot的消息
    if chat.type != 'private':
        is_reply_to_bot = (
            message.reply_to_message and 
            message.reply_to_message.from_user and 
            message.reply_to_message.from_user.is_bot and 
            message.reply_to_message.from_user.username == 'rk_pin_bot'  # 替换为你的bot用户名
        )
        
        if not is_reply_to_bot:
            if not message.text or not message.entities:
                return
            mentioned = False
            for entity in message.entities:
                if entity.type == 'mention':
                    mention_text = message.text[entity.offset:entity.offset + entity.length]
                    if mention_text == '@rk_pin_bot':  # 替换为你的bot用户名
                        mentioned = True
                        break
            if not mentioned:
                return

    try:
        message_text = get_message_text(message)
        
        if not message_text:
            await message.reply_text("无法处理此类型的消息")
            return
            
        # 添加重试机制
        max_retries = 3
        retry_count = 0
        reply_msg = None
        
        while retry_count < max_retries:
            try:
                if not reply_msg:
                    reply_msg = await message.reply_text("正在处理消息...")
                
                last_text = ""
                async for response_text, should_update in get_ai_response(message_text, NORMAL_PROMPT):
                    if should_update and response_text:
                        try:
                            if response_text != last_text:
                                last_text = response_text
                                await reply_msg.edit_text(text=response_text)
                        except Exception as e:
                            if "message is not modified" not in str(e).lower():
                                logger.warning(f"Failed to update message: {e}")
                
                if last_text:
                    try:
                        await reply_msg.edit_text(
                            text=last_text,
                        )
                    except Exception as e:
                        if "message is not modified" not in str(e).lower():
                            logger.error(f"Failed to add buttons: {e}")
                else:
                    await reply_msg.edit_text("生成回复失败，未获得有效响应")
                
                break  # 成功完成，跳出重试循环
                
            except (NetworkError, TimedOut) as e:
                retry_count += 1
                logger.warning(f"Network error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # 等待1秒后重试
                else:
                    if reply_msg:
                        await reply_msg.edit_text("网络错误，请稍后重试")
                    else:
                        await message.reply_text("网络错误，请稍后重试")
            except Exception as e:
                logger.error(f"Failed to generate response: {e}")
                if reply_msg:
                    await reply_msg.edit_text("生成回复失败，请重试")
                break
                    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        await message.reply_text("处理消息时出现错误")

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