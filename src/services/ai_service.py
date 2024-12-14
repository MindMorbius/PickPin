from config.settings import AI_PROVIDER
# from .openai_service import get_openai_response
from .google_service import get_google_response, get_google_vision_response
from .siliconflow_service import get_siliconflow_response
from .zhipu_service import get_zhipu_response, get_zhipu_vision_response, get_zhipu_vision_response_base64
import logging

logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    """转义 Markdown V2 特殊字符"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def get_ai_response(message: str, system_prompt: str):
    accumulated_text = ""
    
    if AI_PROVIDER == "google":
        async for text, update, footer in get_google_response(message, system_prompt):
            accumulated_text = text
            if update:  # 最终更新
                yield f"<blockquote expandable>\n{text}\n</blockquote>{footer}", update
            else:
                yield f"正在生成中：\n<blockquote expandable>\n{text}\n</blockquote>", update
                
    elif AI_PROVIDER == "siliconflow":
        async for text, update, footer in get_siliconflow_response(message, system_prompt):
            accumulated_text = text
            if update:
                yield f"<blockquote expandable>\n{text}\n</blockquote>{footer}", update
            else:
                yield f"正在生成中：\n<blockquote expandable>\n{text}\n</blockquote>", update
                
    elif AI_PROVIDER == "zhipu":
        async for text, update, footer in get_zhipu_response(message, system_prompt):
            accumulated_text = text
            if update:
                yield f"<blockquote expandable>\n{text}\n</blockquote>{footer}", update
            else:
                yield f"正在生成中：\n<blockquote expandable>\n{text}\n</blockquote>", update

async def get_vision_response(message: str, system_prompt: str, image_url: str):
    accumulated_text = ""

    if AI_PROVIDER == "zhipu":
        async for text, update, footer in get_zhipu_vision_response_base64(message, system_prompt, image_url):
            accumulated_text = text
            if update:
                yield f"<blockquote expandable>\n{text}\n</blockquote>{footer}", update
            else:
                yield f"正在生成中：\n<blockquote expandable>\n{text}\n</blockquote>", update
    elif AI_PROVIDER == "google":
        async for text, update, footer in get_google_vision_response(message, image_url, system_prompt):
            accumulated_text = text
            if update:
                yield f"<blockquote expandable>\n{text}\n</blockquote>{footer}", update
            else:
                yield f"正在生成中：\n<blockquote expandable>\n{text}\n</blockquote>", update
