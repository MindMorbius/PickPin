from openai import OpenAI
from config.settings import GOOGLE_API_KEY, GOOGLE_MODEL

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

async def get_gemini_response(message: str, system_prompt: str):

    accumulated_text = ""
    last_update_length = 0

    response = client.chat.completions.create(
        model=GOOGLE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        stream=True
    )
    
    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content'):
            accumulated_text += chunk.choices[0].delta.content
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
    
    yield accumulated_text, True 