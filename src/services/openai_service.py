from openai import OpenAI
from config.settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

async def get_ai_response(message: str, system_prompt: str):
    accumulated_text = ""
    last_update_length = 0
    
    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
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