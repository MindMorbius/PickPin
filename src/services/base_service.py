from typing import AsyncGenerator, Tuple
import logging
import time

logger = logging.getLogger(__name__)

async def stream_response(stream, accumulated_text="") -> AsyncGenerator[Tuple[str, bool], None]:
    last_update_time = 0
    last_text = accumulated_text
    UPDATE_INTERVAL = 0.5
    
    try:
        for chunk in stream:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                accumulated_text += chunk.choices[0].delta.content
                current_time = time.time()
                
                if (current_time - last_update_time >= UPDATE_INTERVAL and 
                    accumulated_text != last_text):
                    last_update_time = current_time
                    last_text = accumulated_text
                    yield accumulated_text, True
        
        if accumulated_text and accumulated_text != last_text:
            yield accumulated_text, True
            
    except Exception as e:
        logger.error(f"Error in stream_response: {e}")
        if accumulated_text and accumulated_text != last_text:
            yield accumulated_text, True
        raise