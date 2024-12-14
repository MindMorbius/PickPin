import base64
from openai import OpenAI
from config.settings import GOOGLE_API_KEY, GOOGLE_MODEL
from .base_service import stream_response
import asyncio
import logging
import requests

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def image_to_base64(image_url: str) -> str:
    """将图片URL转换为base64编码"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting image to base64: {e}")
        raise

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

def image_to_base64(image_url: str) -> str:
    """将图片URL转换为base64编码"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting image to base64: {e}")
        raise


async def get_google_vision_response(message: str, image_url: str, system_prompt: str):
    max_retries = 3
    base_delay = 1
    
    image_base64 = image_to_base64(image_url)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GOOGLE_MODEL,
                messages=[
                    # {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                stream=True
            )
            
            async for text, update, footer in stream_response(response):
                yield text, update, footer
            return
            
        except Exception as e:
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                yield f"抱歉，服务暂时不可用，请稍后重试。错误: {str(e)}", True, ""
                return