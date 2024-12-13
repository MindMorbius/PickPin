from openai import OpenAI
from config.settings import SILICONFLOW_API_KEY, SILICONFLOW_MODEL
from .base_service import stream_response
import logging

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url='https://api.siliconflow.cn/v1'
)

async def get_siliconflow_response(message: str, system_prompt: str):
    """处理 SiliconFlow API 的对话请求"""
    try:
        response = client.chat.completions.create(
            model=SILICONFLOW_MODEL,  # 使用 Qwen 等模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            stream=True
        )
        
        async for text, update, footer in stream_response(response):
            yield text, update, footer
            
    except Exception as e:
        logger.error(f"Error in siliconflow_response: {e}")
        yield f"SiliconFlow 服务暂时不可用，请稍后重试。错误: {str(e)}", True, "" 