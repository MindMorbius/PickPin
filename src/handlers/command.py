import logging
from telegram import Update, Chat
from telegram.ext import ContextTypes
from config.settings import TELEGRAM_USER_ID, CHANNEL_ID, GROUP_ID
from services.ai_service import get_ai_response
from prompts.prompts import CLASSIFY_PROMPT, SUMMARY_PROMPT
from utils.buttons import (
    get_content_options_buttons,
    get_prompt_selection_buttons
)
from prompts.prompts import TECH_PROMPT, NEWS_PROMPT, CULTURE_PROMPT, KNOWLEDGE_PROMPT, CHAT_PROMPT
from utils.telegram_handler import TelegramMessageHandler
import re
import asyncio
from utils.response_controller import ResponseController
from database.models import Vote

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    user_id = update.effective_user.id
    await handler.reply_to_command(
        "👋 你好！我是 PickPin 机器人\n\n"
        "我可以帮助你处理和投稿信息到 RKPin 频道\n\n"
        "🤖 PickPin 投稿指南\n\n"
        "1. 先将投稿内容发送给机器人\n"
        "2. 使用 /submit 命令 回复需要投稿的内容\n"
        "3. 机器人会根据内容分析，并生成投稿内容\n"
        "4. 如果觉得内容不错，点击“投个稿”按钮\n"
        "5. 机器人会将投稿内容发送到群组 @rk_pin_bus 进行审核\n\n"
        "⚠️ 注意事项:\n"
        "- 内容需要符合 RKPin 频道的要求\n"
        "- 禁止推广/黑产/刷屏/色情/NSFW\n"
        "- 禁止黄赌毒/宗教/政治/键政\n",
        auto_delete=False
    )

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type == 'private':
        await handler.reply_to_command(
            f"你的用户 ID 是: {user.id}",
            reply_to_message_id=update.message.message_id,
            auto_delete=False
        )
    elif chat.id == GROUP_ID:
        await handler.reply_to_command(
            f"群组 ID: {chat.id}\n"
            f"类型: {chat.type}\n"
            f"名称: {chat.title}\n"
            f"你的用户 ID: {user.id}",
            reply_to_message_id=update.message.message_id,
            auto_delete=False
        )
async def submit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    response_controller = ResponseController()
    
    if not await response_controller.is_user_allowed(update, False, context):
        return
        
    message = update.message
    user = update.effective_user
    
    if not message.reply_to_message:
        await handler.reply_to_command(
            "请引用要投稿的消息使用此命令",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    # 获取原始消息信息
    original_message = message.reply_to_message
    
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

    # 保存基础投票数据
    vote = Vote(
        original_message_id=original_message_id,
        original_chat_id=original_chat_id,
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        contribute=original_message.text or original_message.caption
    )
    
    if not await context.bot_data['db'].save_vote(vote):
        await handler.reply_to_command("保存投票失败")
        return

    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.reply_to_command(
            "无法处理此类型的消息",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return

    try:
        last_text = ""
        prompt_type = None
        analyzing_msg = await handler.send_message(
            "正在分析内容...",
            reply_to_message_id=message.reply_to_message.message_id
        )
        
        async for classification_text, should_update in get_ai_response(reply_text, CLASSIFY_PROMPT):
            if should_update:
                try:
                    cleaned_text = classification_text
                    await handler.edit_message(analyzing_msg, cleaned_text, parse_mode='HTML')
                    last_text = cleaned_text
                except Exception as e:
                    await handler.edit_message(analyzing_msg, classification_text, parse_mode=None)
                    last_text = classification_text
                
                if 'TECH_PROMPT' in classification_text:
                    selected_prompt = TECH_PROMPT
                elif 'NEWS_PROMPT' in classification_text:
                    selected_prompt = NEWS_PROMPT
                elif 'CULTURE_PROMPT' in classification_text:
                    selected_prompt = CULTURE_PROMPT
                elif 'KNOWLEDGE_PROMPT' in classification_text:
                    selected_prompt = KNOWLEDGE_PROMPT
                else:
                    selected_prompt = CHAT_PROMPT
        
        context.user_data['original_message'] = message.reply_to_message
        context.user_data['classification_result'] = last_text
        context.user_data['prompt_type'] = prompt_type
        
        generated_text = ""
        generation_msg = await handler.send_message(
            "正在生成内容...",
            reply_to_message_id=message.reply_to_message.message_id
        )
        
        async for content_text, should_update in get_ai_response(reply_text, selected_prompt):
            if should_update:
                try:
                    cleaned_text = content_text
                    await handler.edit_message(generation_msg, cleaned_text, parse_mode='HTML')
                    generated_text = cleaned_text
                except Exception as e:
                    await handler.edit_message(generation_msg, content_text, parse_mode=None)
                    generated_text = content_text
        
        await handler.edit_message(
            generation_msg,
            generated_text,
            reply_markup=get_content_options_buttons(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await handler.send_notification(
            "分析失败，请重试",
            reply_to_message_id=message.message_id,
            auto_delete=False
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    await handler.reply_to_command(
        "🤖 PickPin 投稿指南\n\n"
        "1. 先将投稿内容发送给机器人\n"
        "2. 使用 /submit 命令 回复需要投稿的内容\n"
        "3. 机器人会根据内容分析，并生成投稿内容\n"
        "4. 如果觉得内容不错，点击“投个稿”按钮\n"
        "5. 机器人会将��稿内容发送到群组 @rk_pin_bus 进行审核\n\n"

        "如果需要帮助，请在群组：@rk_pin_bus 中联系管理员。",
        auto_delete=False
    )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    response_controller = ResponseController()
    
    if not await response_controller.is_user_allowed(update, False, context):
        return
        
    chat = update.effective_chat
    message = update.message
    user = update.effective_user
    
    if not message.reply_to_message:
        await handler.reply_to_command(
            "请引用要分析的消息使用此命令",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.reply_to_command(
            "无法分析此类型的消息",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return

    # 在群组中发送提示并删除
    if chat.id == GROUP_ID:
        await handler.reply_to_command(
            "已开始分析，请前往 @rk_pin_bot 查看",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        
        # 转发原文到私聊
        forwarded = await handler.forward_message(
            user.id,
            message.reply_to_message
        )
        if not forwarded:
            return
        
    
    try:
        last_text = ""
        prompt_type = None
        analyzing_msg = await handler.send_message(
            "正在分析内容...",
            chat_id=user.id,
            reply_to_message_id=forwarded.message_id
        )
        
        async for classification_text, should_update in get_ai_response(reply_text, CLASSIFY_PROMPT):
            if should_update:
                try:
                    # 尝试清理和修复 Markdown
                    cleaned_text = classification_text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    await handler.edit_message(analyzing_msg, cleaned_text, parse_mode='Markdown')
                    last_text = cleaned_text
                except Exception as e:
                    # 如果 Markdown 解析失败，尝试不使用解析发送
                    await handler.edit_message(analyzing_msg, classification_text, parse_mode=None)
                    last_text = classification_text
                
                if 'TECH_PROMPT' in classification_text:
                    selected_prompt = TECH_PROMPT
                elif 'NEWS_PROMPT' in classification_text:
                    selected_prompt = NEWS_PROMPT
                elif 'CULTURE_PROMPT' in classification_text:
                    selected_prompt = CULTURE_PROMPT
                elif 'KNOWLEDGE_PROMPT' in classification_text:
                    selected_prompt = KNOWLEDGE_PROMPT
                else:
                    selected_prompt = CHAT_PROMPT
        
        context.user_data['original_message'] = message.reply_to_message
        context.user_data['classification_result'] = last_text
        context.user_data['prompt_type'] = prompt_type
        
        generated_text = ""
        generation_msg = await handler.send_message(
            "正在生成内容...",
            chat_id=user.id,
            reply_to_message_id=forwarded.message_id
        )
        
        async for content_text, should_update in get_ai_response(reply_text, selected_prompt):
            if should_update:
                try:
                    cleaned_text = content_text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
                    await handler.edit_message(generation_msg, cleaned_text, parse_mode='Markdown')
                    generated_text = cleaned_text
                except Exception as e:
                    await handler.edit_message(generation_msg, content_text, parse_mode=None)
                    generated_text = content_text
        
        await handler.edit_message(
            generation_msg,
            generated_text,
            reply_markup=get_content_options_buttons(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await handler.send_notification(
            "分析失败，请重试",
            chat_id=user.id,
            reply_to_message_id=message.message_id,
            auto_delete=False
        )

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handler = TelegramMessageHandler(update, context)
    response_controller = ResponseController()

    if not await response_controller.is_user_allowed(update, False, context):
        return
        
    chat = update.effective_chat
    message = update.message
    
    if not message.reply_to_message:
        await handler.reply_to_command(
            "请引用要总结的消息使用此命令",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        await handler.reply_to_command(
            "无法总结此类型的消息",
            reply_to_message_id=message.message_id,
            auto_delete=True
        )
        return
        
    summarizing_msg = await handler.send_message("正在总结内容...", reply_to_message_id=message.reply_to_message.message_id, delete_command=True)
    
    try:
        last_text = ""
        async for summary_text, should_update in get_ai_response(reply_text, SUMMARY_PROMPT):
            if should_update and summary_text != last_text:
                last_text = summary_text
                await handler.edit_message(summarizing_msg, summary_text, parse_mode='Markdown')
                    
        if last_text != summarizing_msg.text:
            await handler.edit_message(summarizing_msg, last_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        await handler.send_notification(
            "总结失败，请重试",
            chat_id=user.id,
            reply_to_message_id=message.message_id,
            auto_delete=False
        )