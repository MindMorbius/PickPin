from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from services.openai_service import get_ai_response
from prompts.prompts import (
    CLASSIFY_PROMPT, TECH_PROMPT, NEWS_PROMPT, 
    CULTURE_PROMPT, KNOWLEDGE_PROMPT, CHAT_PROMPT
)

logger = logging.getLogger(__name__)

CLASSIFY_HELP_TEXT = """
📝 请发送你想要分析的内容，我会帮你进行分类：

🔬 科技类
- 新产品/发明创造
- 科学发现/突破
- 技术趋势/展望

📰 新闻类
- 重大事件/动态
- 政经社会议题
- 全球性话题

🎨 文化类
- 艺术/创作/表达
- 思潮/现象/趋势
- 人文/传统/习俗

📚 知识类
- 学术/理论/研究
- 专业领域知识
- 跨学科内容

我会分析内容类型、复杂度，并提取核心信息。
"""

def get_classification_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 确定分类", callback_data='confirm_classify'),
            InlineKeyboardButton("🔄 重新分类", callback_data='reclassify'),
        ],
        [InlineKeyboardButton("❌ 取消输入", callback_data='cancel_input')]
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'classify':
        await query.edit_message_text(CLASSIFY_HELP_TEXT)
        context.user_data['mode'] = 'classify'
        
    elif query.data == 'chat':
        await query.edit_message_text(
            "💬 已进入通用聊天模式，请随意发送消息。"
        )
        context.user_data['mode'] = 'chat'
        
    elif query.data == 'settings':
        await query.edit_message_text(
            "⚙️ 设置功能正在开发中...\n"
            "请使用其他功能。"
        )
    
    elif query.data == 'confirm_classify':
        original_text = context.user_data.get('original_text', '')
        classification = context.user_data.get('classification', '')
        
        logger.info(f"Confirming classification for text: {original_text[:100]}...")
        logger.info(f"Full classification result: {classification}")
        
        # 修改正则表达式以匹配方括号中的处理器名称
        import re
        prompt_match = re.search(r'处理器：\[(\w+_PROMPT)\]', classification)
        if prompt_match:
            prompt_name = prompt_match.group(1)
            logger.info(f"Extracted prompt name: {prompt_name}")
            
            # 从 prompts 模块获取对应的 prompt
            prompts = {
                'TECH_PROMPT': TECH_PROMPT,
                'NEWS_PROMPT': NEWS_PROMPT,
                'CULTURE_PROMPT': CULTURE_PROMPT,
                'KNOWLEDGE_PROMPT': KNOWLEDGE_PROMPT
            }
            prompt = prompts.get(prompt_name, CHAT_PROMPT)
            logger.info(f"Selected prompt: {prompt_name}")
            if prompt == CHAT_PROMPT:
                logger.warning(f"Fallback to CHAT_PROMPT for unknown prompt name: {prompt_name}")
        else:
            prompt = CHAT_PROMPT
            logger.warning("No prompt identifier found in classification, using CHAT_PROMPT")
            
        logger.info(f"Using prompt text: {prompt[:100]}...")
        async for accumulated_text, should_update in get_ai_response(original_text, prompt):
            if should_update:
                try:
                    await query.edit_message_text(accumulated_text)
                except Exception as e:
                    logger.warning(f"Failed to update message: {e}")
    
    elif query.data == 'reclassify':
        original_text = context.user_data.get('original_text', '')
        async for accumulated_text, should_update in get_ai_response(original_text, CLASSIFY_PROMPT):
            if should_update:
                try:
                    await query.edit_message_text(
                        text=accumulated_text,
                        reply_markup=get_classification_keyboard()
                    )
                except Exception as e:
                    logger.warning(f"Failed to update message: {e}")
    
    elif query.data == 'cancel_input':
        await query.message.delete() 