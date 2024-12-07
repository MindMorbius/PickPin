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
        logger.info(f"Received message in {mode} mode: {update.message.text}")
        reply_message = await update.message.reply_text("思考中...")
        
        # 保存原始文本，用于后续重新分类
        context.user_data['original_text'] = update.message.text
        
        if mode == 'classify':
            async for accumulated_text, should_update in get_ai_response(update.message.text, CLASSIFY_PROMPT):
                if should_update:
                    try:
                        # 保存分类结果
                        context.user_data['classification'] = accumulated_text
                        await reply_message.edit_text(
                            text=accumulated_text,
                            reply_markup=get_classification_keyboard()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
        else:
            async for accumulated_text, should_update in get_ai_response(update.message.text, CHAT_PROMPT):
                if should_update:
                    try:
                        await reply_message.edit_text(accumulated_text)
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
                    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        await update.message.reply_text("抱歉，处理您的消息时出现错误。") 