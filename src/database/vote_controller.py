from typing import Optional, Dict, Any, List
from .base_controller import BaseController
import json

class VoteController(BaseController):
    async def init(self):
        """初始化投票表"""
        await self.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_message_id INTEGER NOT NULL,
                original_chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                contribute TEXT,
                analyse TEXT,
                introduction TEXT,
                message_id INTEGER,
                chat_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                UNIQUE(original_message_id, original_chat_id)
            )
        ''')

    async def save_vote(self, vote_data: Dict[str, Any]) -> bool:
        """保存投票信息"""
        metadata_json = json.dumps(vote_data.get('metadata', {}), ensure_ascii=False)
        
        if await self.get_vote_by_original(vote_data['original_message_id'], vote_data['original_chat_id']):
            return await self.execute('''
                UPDATE votes 
                SET username = ?,
                    contribute = ?,
                    analyse = ?,
                    introduction = ?,
                    message_id = ?,
                    chat_id = ?,
                    status = ?,
                    metadata = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE original_message_id = ? AND original_chat_id = ?
            ''', (
                vote_data.get('username'),
                vote_data.get('contribute'),
                vote_data.get('analyse'),
                vote_data.get('introduction'),
                vote_data.get('message_id'),
                vote_data.get('chat_id'),
                vote_data.get('status', 'pending'),
                metadata_json,
                vote_data['original_message_id'],
                vote_data['original_chat_id']
            ))
        
        return await self.execute('''
            INSERT INTO votes 
            (original_message_id, original_chat_id, user_id, username, contribute,
             analyse, introduction, message_id, chat_id, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vote_data['original_message_id'],
            vote_data['original_chat_id'],
            vote_data['user_id'],
            vote_data.get('username'),
            vote_data.get('contribute'),
            vote_data.get('analyse'),
            vote_data.get('introduction'),
            vote_data.get('message_id'),
            vote_data.get('chat_id'),
            vote_data.get('status', 'pending'),
            metadata_json
        ))

    async def get_vote(self, vote_id: int) -> Optional[Dict[str, Any]]:
        """获取投票信息"""
        data = await self.fetch_one(
            'SELECT * FROM votes WHERE vote_id = ?',
            (vote_id,)
        )
        if data:
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
        return data

    async def get_vote_by_message(self, message_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """通过消息ID获取投票"""
        data = await self.fetch_one(
            'SELECT * FROM votes WHERE message_id = ? AND chat_id = ?',
            (message_id, chat_id)
        )
        if data:
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
        return data

    async def get_user_votes(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """获取用户的投票列表"""
        votes = await self.fetch_all(
            'SELECT * FROM votes WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
            (user_id, limit)
        )
        for vote in votes:
            vote['metadata'] = json.loads(vote['metadata']) if vote['metadata'] else {}
        return votes

    async def update_vote_status(self, vote_id: int, status: str) -> bool:
        """更新投票状态"""
        return await self.execute('''
            UPDATE votes 
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE vote_id = ?
        ''', (status, vote_id)) 

    async def get_vote_by_original(self, original_message_id: int, original_chat_id: int) -> Optional[Dict[str, Any]]:
        """通过原始消息ID获取投票"""
        data = await self.fetch_one(
            'SELECT * FROM votes WHERE original_message_id = ? AND original_chat_id = ?',
            (original_message_id, original_chat_id)
        )
        if data:
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
        return data

    async def update_vote_content(self, vote_id: int, analyse: str, introduction: str) -> bool:
        """更新投票内容"""
        return await self.execute('''
            UPDATE votes 
            SET analyse = ?,
                introduction = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE vote_id = ?
        ''', (analyse, introduction, vote_id))

    async def update_vote_message(self, vote_id: int, message_id: int, chat_id: int) -> bool:
        """更新投票消息ID"""
        return await self.execute('''
            UPDATE votes 
            SET message_id = ?,
                chat_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE vote_id = ?
        ''', (message_id, chat_id, vote_id)) 