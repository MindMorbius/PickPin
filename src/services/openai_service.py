from openai import OpenAI
from config.settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .base_service import stream_response

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

async def get_ai_response(message: str, system_prompt: str):
    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        stream=True
    )
    
    async for text, update in stream_response(stream):
        yield text, update