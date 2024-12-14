from typing import AsyncGenerator, Tuple
import logging
import time

logger = logging.getLogger(__name__)

async def stream_response(stream, accumulated_text="") -> AsyncGenerator[Tuple[str, bool, str], None]:
    last_update_time = 0
    last_text = accumulated_text
    UPDATE_INTERVAL = 1
    MIN_NEW_CHARS = 20
    start_time = time.time()
    
    try:
        model_info = None
        completion_tokens = 0
        
        for chunk in stream:
            if not model_info and hasattr(chunk, 'model'):
                model_info = chunk.model
                
            if hasattr(chunk, 'usage') and chunk.usage:
                completion_tokens = chunk.usage.completion_tokens
                
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                accumulated_text += chunk.choices[0].delta.content
                current_time = time.time()
                
                if (current_time - last_update_time >= UPDATE_INTERVAL and 
                    accumulated_text != last_text and
                    len(accumulated_text) - len(last_text) >= MIN_NEW_CHARS):
                    last_update_time = current_time
                    last_text = accumulated_text
                    yield accumulated_text, False, ""
        
        if accumulated_text:
            elapsed_time = round(time.time() - start_time, 2)
            footer = (
                f'\n'
                f'<i>💡 Generated by: {model_info}</i>\n'
                f'<i>⏱️ Response time: {elapsed_time}s</i>\n'
                f'<i>🎯 Tokens: {completion_tokens}</i>'
            )
            yield accumulated_text, True, footer
            
    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        if accumulated_text and accumulated_text != last_text:
            yield accumulated_text, True, ""
        raise