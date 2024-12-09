from typing import AsyncGenerator, Tuple
import logging

logger = logging.getLogger(__name__)

async def stream_response(stream, accumulated_text="") -> AsyncGenerator[Tuple[str, bool], None]:
    last_update_length = 0
    
    try:
        for chunk in stream:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
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
        
        if accumulated_text:
            yield accumulated_text, True
            
    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        if accumulated_text:
            yield accumulated_text, True
        raise 