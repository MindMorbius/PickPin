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

async def get_google_response(message: str, system_prompt: str):
    max_retries = 3
    base_delay = 1
    current_model = GOOGLE_MODEL
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                stream=True
            )
            
            async for text, update, footer in stream_response(response):
                yield text, update, footer
            return
            
        except Exception as e:
            if "429" in str(e) and current_model == GOOGLE_MODEL:
                logger.info(f"Quota exceeded for {current_model}, switching to gemini-1.5-flash")
                current_model = "gemini-1.5-flash"
                continue
                
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                yield f"抱歉，服务暂时不可用，请稍后重试。错误: {str(e)}", True, ""
                return