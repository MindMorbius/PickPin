from typing import Optional, Dict, Any, List
from datetime import datetime
from .base_controller import BaseController

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
        return await self.fetch_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )

    async def save_user(self, user_data: Dict[str, Any]) -> bool:
        """保存或更新用户信息"""
        user = await self.get_user(user_data['user_id'])
        
        if user:
            # 更新现有用户
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
                user_data.get('metadata'),
                user_data['user_id']
            ))
        else:
            # 创建新用户
            return await self.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('metadata')
            ))

    async def update_stats(self, user_id: int, submission: bool = False, approved: bool = False) -> bool:
        """更新用户统计信息"""
        updates = []
        params = []
        
        if submission:
            updates.append("submission_count = submission_count + 1")
        if approved:
            updates.append("approved_count = approved_count + 1")
            
        if not updates:
            return True
            
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        params.append(user_id)
        
        return await self.execute(query, tuple(params))

    async def set_admin_status(self, user_id: int, is_admin: bool) -> bool:
        """设置管理员状态"""
        return await self.execute(
            'UPDATE users SET is_admin = ? WHERE user_id = ?',
            (is_admin, user_id)
        )

    async def set_block_status(self, user_id: int, is_blocked: bool) -> bool:
        """设置封禁状态"""
        return await self.execute(
            'UPDATE users SET is_blocked = ? WHERE user_id = ?',
            (is_blocked, user_id)
        )

    async def get_active_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取活跃用户列表"""
        return await self.fetch_all('''
            SELECT * FROM users 
            WHERE last_active_at >= datetime('now', ?) 
            ORDER BY last_active_at DESC
        ''', (f'-{days} days',))

    async def get_top_contributors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取贡献榜"""
        return await self.fetch_all('''
            SELECT * FROM users 
            ORDER BY approved_count DESC, submission_count DESC 
            LIMIT ?
        ''', (limit,)) 

    async def increment_usage(self, user_id: int) -> bool:
        """增加使用次数，自动处理每日计数重置"""
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
                    ELSE CURRENT_TIMESTAMP 
                END,
                last_active_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))

    async def get_usage_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户使用统计"""
        return await self.fetch_one('''
            SELECT 
                total_usage_count,
                CASE 
                    WHEN date(last_usage_date) = date('now') 
                    THEN daily_usage_count 
                    ELSE 0 
                END as daily_usage_count,
                last_usage_date
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))

    async def reset_daily_usage(self) -> bool:
        """重置所有用户的每日使用次数（可选用于定时任务）"""
        return await self.execute('''
            UPDATE users 
            SET daily_usage_count = 0 
            WHERE date(last_usage_date) < date('now')
        ''') 