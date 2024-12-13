import base64
import requests
from openai import OpenAI
from config.settings import ZHIPU_API_KEY, ZHIPU_MODEL, ZHIPU_VISION_MODEL
from .base_service import stream_response
import logging

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=ZHIPU_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

async def get_zhipu_response(message: str, system_prompt: str):
    """处理纯文本对话"""
    try:
        response = client.chat.completions.create(
            model=ZHIPU_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            stream=True
        )
        
        async for text, update, footer in stream_response(response):
            yield text, update, footer
            
    except Exception as e:
        logger.error(f"Error in zhipu_response: {e}")
        yield f"智谱AI服务暂时不可用，请稍后重试。错误: {str(e)}", True, ""

async def get_zhipu_vision_response(message: str, system_prompt: str, image_url: str):
    """处理图片分析对话"""
    try:
        response = client.chat.completions.create(
            model=ZHIPU_VISION_MODEL,  # 使用支持图片的模型
            messages=[
                # {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        },
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                }
            ],
            stream=True
        )
        
        async for text, update, footer in stream_response(response):
            yield text, update, footer
            
    except Exception as e:
        logger.error(f"Error in zhipu_vision_response: {e}")
        yield f"智谱AI图片分析服务暂时不可用，请稍后重试。错误: {str(e)}", True, ""

def image_to_base64(image_url: str) -> str:
    """将图片URL转换为base64编码"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting image to base64: {e}")
        raise

async def get_zhipu_vision_response_base64(message: str, system_prompt: str, image_url: str):
    """使用base64处理图片分析对话"""
    try:
        image_base64 = image_to_base64(image_url)
        response = client.chat.completions.create(
            model=ZHIPU_VISION_MODEL,
            messages=[
                # {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_base64}
                        },
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                }
            ],
            stream=True
        )
        
        async for text, update, footer in stream_response(response):
            yield text, update, footer
            
    except Exception as e:
        logger.error(f"Error in zhipu_vision_response_base64: {e}")
        yield f"智谱AI图片分析服务暂时不可用，请稍后重试。错误: {str(e)}", True, ""