from openai import OpenAI
from config.settings import GOOGLE_API_KEY, GOOGLE_MODEL
from .base_service import stream_response

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

async def get_gemini_response(message: str, system_prompt: str):
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