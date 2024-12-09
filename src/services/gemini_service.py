from openai import OpenAI
from config.settings import GOOGLE_API_KEY, GOOGLE_MODEL
import logging

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

async def get_gemini_response(message: str, system_prompt: str):
    accumulated_text = ""
    last_update_length = 0

    try:
        response = client.chat.completions.create(
            model=GOOGLE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            stream=True
        )
        
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                delta_content = chunk.choices[0].delta.content
                if delta_content:  # 确保内容不为空
                    accumulated_text += delta_content
                    current_length = len(accumulated_text)
                    
                    should_update = (
                        (current_length >= 20 and last_update_length == 0) or
                        (current_length >= 100 and last_update_length < 100) or
                        (current_length >= 200 and last_update_length < 200) or
                        (current_length >= 500 and last_update_length < 500) or
                        (current_length - last_update_length >= 500)
                    )
                    
                    if should_update:
                        last_update_length = current_length
                        yield accumulated_text, True
        
        # 只在有累积文本时才产生最后的输出
        if accumulated_text:
            yield accumulated_text, True
            
    except Exception as e:
        logger.error(f"Error in get_gemini_response: {e}")
        if accumulated_text:  # 如果已经有一些文本，返回已有内容
            yield accumulated_text, True
        else:  # 如果完全没有内容，抛出异常
            raise