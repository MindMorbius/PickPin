import aiosqlite
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class MessageDB:
    def __init__(self):
        self.db_path = Path("data/messages.db")
        self.db_path.parent.mkdir(exist_ok=True)
        
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER,
                    text TEXT,
                    type TEXT NOT NULL,
                    reply_to_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    PRIMARY KEY (message_id, chat_id)
                )
            ''')
            await db.commit()

    async def save_message(self, message_data: Dict[str, Any]) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # 检查消息是否已存在
                async with db.execute(
                    'SELECT metadata FROM messages WHERE message_id = ? AND chat_id = ?',
                    (message_data['message_id'], message_data['chat_id'])
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        # 如果消息存在，只更新text和metadata
                        metadata = json.loads(row[0]) if row[0] else {}
                        if 'metadata' in message_data:
                            metadata.update(message_data['metadata'])
                        
                        await db.execute('''
                            UPDATE messages 
                            SET text = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE message_id = ? AND chat_id = ?
                        ''', (
                            message_data.get('text'),
                            json.dumps(metadata, ensure_ascii=False),
                            message_data['message_id'],
                            message_data['chat_id']
                        ))
                    else:
                        # 如果消息不存在，插入新记录
                        await db.execute('''
                            INSERT INTO messages 
                            (message_id, chat_id, user_id, text, type, reply_to_message_id, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            message_data['message_id'],
                            message_data['chat_id'],
                            message_data.get('user_id'),
                            message_data.get('text'),
                            message_data['type'],
                            message_data.get('reply_to_message_id'),
                            json.dumps(message_data.get('metadata', {}), ensure_ascii=False)
                        ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False

    async def get_message(self, message_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM messages WHERE message_id = ? AND chat_id = ?',
                    (message_id, chat_id)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        data = dict(row)
                        data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                        return data
                    return None
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None 