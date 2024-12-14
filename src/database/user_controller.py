from typing import Optional, Dict, Any, List
from datetime import datetime
from .base_controller import BaseController
import json

class UserController(BaseController):
    async def init(self):
        """初始化用户表"""
        await self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_admin BOOLEAN DEFAULT FALSE,
                is_blocked BOOLEAN DEFAULT FALSE,
                submission_count INTEGER DEFAULT 0,
                approved_count INTEGER DEFAULT 0,
                total_usage_count INTEGER DEFAULT 0,
                daily_usage_count INTEGER DEFAULT 0,
                last_usage_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        data = await self.fetch_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        if data:
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
        return data

    async def save_user(self, user_data: Dict[str, Any]) -> bool:
        """保存或更新用户信息"""
        metadata_json = json.dumps(user_data.get('metadata', {}), ensure_ascii=False)
        
        if await self.get_user(user_data['user_id']):
            return await self.execute('''
                UPDATE users SET 
                    username = ?,
                    first_name = ?,
                    last_name = ?,
                    last_active_at = CURRENT_TIMESTAMP,
                    metadata = ?
                WHERE user_id = ?
            ''', (
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                metadata_json,
                user_data['user_id']
            ))
        
        return await self.execute('''
            INSERT INTO users 
            (user_id, username, first_name, last_name, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_data['user_id'],
            user_data.get('username'),
            user_data.get('first_name'),
            user_data.get('last_name'),
            metadata_json
        ))

    async def increment_usage(self, user_id: int) -> bool:
        """增加使用次数"""
        return await self.execute('''
            UPDATE users 
            SET 
                total_usage_count = total_usage_count + 1,
                daily_usage_count = CASE 
                    WHEN date(last_usage_date) = date('now') 
                    THEN daily_usage_count + 1 
                    ELSE 1 
                END,
                last_usage_date = CASE 
                    WHEN date(last_usage_date) = date('now') 
                    THEN last_usage_date 
                    ELSE date('now') 
                END,
                last_active_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,)) 