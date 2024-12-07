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

def get_message_control_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
            InlineKeyboardButton("📝 反馈", callback_data='feedback'),
        ]
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'classify':
        keyboard = [
            [InlineKeyboardButton("↩️ 返回主菜单", callback_data='back_to_main')],
            [
                InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
                InlineKeyboardButton("📝 反馈", callback_data='feedback'),
            ]
        ]
        await query.edit_message_text(
            CLASSIFY_HELP_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['mode'] = 'classify'
        
    elif query.data == 'chat':
        keyboard = [
            [InlineKeyboardButton("↩️ 返回主菜单", callback_data='back_to_main')],
            [
                InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
                InlineKeyboardButton("📝 反馈", callback_data='feedback'),
            ]
        ]
        await query.edit_message_text(
            "💬 已进入通用聊天模式，请随意发送消息。",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['mode'] = 'chat'
        
    elif query.data == 'settings':
        keyboard = [
            [
                InlineKeyboardButton("🔍 默认分类模式", callback_data='set_mode_classify'),
                InlineKeyboardButton("💭 默认聊天模式", callback_data='set_mode_chat'),
            ],
            [InlineKeyboardButton("↩️ 返回主菜单", callback_data='back_to_main')],
            [
                InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
                InlineKeyboardButton("📝 反馈", callback_data='feedback'),
            ]
        ]
        await query.edit_message_text(
            "⚙️ 设置\n\n"
            "请选择机器人的默认回复模式：\n"
            "• 分类模式：自动分析和分类信息\n"
            "• 聊天模式：直接对话交流",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('set_mode_'):
        mode = query.data.replace('set_mode_', '')
        context.user_data['default_mode'] = mode
        keyboard = [
            [InlineKeyboardButton("↩️ 返回设置", callback_data='settings')],
            [
                InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
                InlineKeyboardButton("📝 反馈", callback_data='feedback'),
            ]
        ]
        await query.edit_message_text(
            f"✅ 已设置默认模式为: {'分类模式' if mode == 'classify' else '聊天模式'}\n\n"
            "你可以随时在设置中更改此选项。",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == 'back_to_main':
        keyboard = [
            [
                InlineKeyboardButton("信息分类", callback_data='classify'),
                InlineKeyboardButton("通用聊天", callback_data='chat'),
            ],
            [InlineKeyboardButton("设置菜单", callback_data='settings')],
            [
                InlineKeyboardButton("🗑️ 清除", callback_data='delete_message'),
                InlineKeyboardButton("📝 反馈", callback_data='feedback'),
            ]
        ]
        await query.edit_message_text(
            "👋 你好！我是PickPin的镜界信息助手，请选择以下功能：\n\n"
            "🔍 信息分类：帮你分析新闻、咨询、热点，转化为镜界内容\n"
            "💭 通用聊天：随意聊天，回答问题\n"
            "⚙️ 设置菜单：调整机器人默认模式，当前默认为聊天模式",
            reply_markup=InlineKeyboardMarkup(keyboard)
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
    
    elif query.data == 'delete_message':
        await query.message.delete()
    
    elif query.data == 'feedback':
        # 预留反馈功能
        await query.answer("反馈功能开发中...")