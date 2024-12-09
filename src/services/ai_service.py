from config.settings import AI_PROVIDER
from .openai_service import get_openai_response
from .gemini_service import get_gemini_response
import logging

logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    """转义 Markdown V2 特殊字符"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def get_ai_response(message: str, system_prompt: str):
    # 添加 Markdown V2 格式要求
    system_prompt = system_prompt + " 严格使用Markdown V2语法格式输出"
    accumulated_text = ""
    
    if AI_PROVIDER == "gemini":
        async for text, update in get_gemini_response(message, system_prompt):
            accumulated_text = text
            # 流式更新时用代码块包裹
            yield f"```\n\n{text}\n\n```", update
    else:
        async for text, update in get_openai_response(message, system_prompt):
            accumulated_text = text
            yield f"```\n\n{text}\n\n```", update
            
    # 最后一次更新发送完整格式化内容
    if accumulated_text:
        logger.info(f"Final AI response: {accumulated_text}")
        # 转义特殊字符
        formatted_text = accumulated_text
        yield formatted_text, True