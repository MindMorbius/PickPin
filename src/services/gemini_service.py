from openai import OpenAI
from config.settings import GOOGLE_API_KEY, GOOGLE_MODEL
from .base_service import stream_response
import asyncio
import logging

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

async def get_gemini_response(message: str, system_prompt: str):
    max_retries = 3
    base_delay = 1  # 初始延迟1秒
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GOOGLE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                stream=True
            )
            
            async for text, update in stream_response(response):
                yield text, update
            return  # 成功则退出
            
        except Exception as e:
            delay = base_delay * (2 ** attempt)  # 指数退避
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
            
            if attempt < max_retries - 1:  # 如果不是最后一次尝试
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                yield f"抱歉，服务暂时不可用，请稍后重试。错误: {str(e)}", True
                return