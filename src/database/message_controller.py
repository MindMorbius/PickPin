from typing import Optional, Dict, Any, List
import json
from .base_controller import BaseController

class MessageController(BaseController):
    async def init(self):
        """初始化消息表"""
        await self.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                user_id INTEGER,
                text TEXT,
                type TEXT NOT NULL,
                chat_type TEXT,
                reply_to_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                PRIMARY KEY (message_id, chat_id)
            )
        ''')
            
    async def get_message(self, message_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """获取单条消息"""
        data = await self.fetch_one(
            'SELECT * FROM messages WHERE message_id = ? AND chat_id = ?',
            (message_id, chat_id)
        )
        if data:
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
        return data

    async def save_message(self, message_data: Dict[str, Any]) -> bool:
        """保存或更新消息"""
        metadata_json = json.dumps(message_data.get('metadata', {}), ensure_ascii=False)
        
        if await self.get_message(message_data['message_id'], message_data['chat_id']):
            return await self.execute('''
                UPDATE messages 
                SET text = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ? AND chat_id = ?
            ''', (
                message_data.get('text'),
                metadata_json,
                message_data['message_id'],
                message_data['chat_id']
            ))
        
        return await self.execute('''
            INSERT INTO messages 
            (message_id, chat_id, user_id, text, type, chat_type, reply_to_message_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_data['message_id'],
            message_data['chat_id'],
            message_data.get('user_id'),
            message_data.get('text'),
            message_data['type'],
            message_data.get('chat_type'),
            message_data.get('reply_to_message_id'),
            metadata_json
        ))

    async def get_chat_messages(self, chat_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指定聊天的消息列表"""
        messages = await self.fetch_all(
            'SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?',
            (chat_id, limit)
        )
        for message in messages:
            message['metadata'] = json.loads(message['metadata']) if message['metadata'] else {}
        return messages

    async def get_thread_messages(self, chat_id: int, thread_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指定主题的消息列表"""
        messages = await self.fetch_all('''
            WITH RECURSIVE thread_messages AS (
                SELECT * FROM messages 
                WHERE message_id = ? AND chat_id = ?
                
                UNION ALL
                
                SELECT m.* FROM messages m
                INNER JOIN thread_messages t 
                ON m.reply_to_message_id = t.message_id
                WHERE m.chat_id = ?
            )
            SELECT * FROM thread_messages
            ORDER BY created_at DESC
            LIMIT ?
        ''', (thread_id, chat_id, chat_id, limit))
        
        for message in messages:
            message['metadata'] = json.loads(message['metadata']) if message['metadata'] else {}
        return messages 

    async def update_message(self, message_data: Dict[str, Any]) -> bool:
        """更新消息内容"""
        metadata_json = json.dumps(message_data.get('metadata', {}), ensure_ascii=False)
        
        return await self.execute('''
            UPDATE messages 
            SET text = ?,
                metadata = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE message_id = ? AND chat_id = ?
        ''', (
            message_data.get('text'),
            metadata_json,
            message_data['message_id'],
            message_data['chat_id']
        ))