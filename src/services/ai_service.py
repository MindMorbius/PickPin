from config.settings import AI_PROVIDER
from .openai_service import get_openai_response
from .gemini_service import get_gemini_response

async def get_ai_response(message: str, system_prompt: str):
    if AI_PROVIDER == "gemini":
        async for text, update in get_gemini_response(message, system_prompt):
            yield text, update
    else:
        async for text, update in get_openai_response(message, system_prompt):
            yield text, update 