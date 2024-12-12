from typing import Optional, List, TypeVar, Type, Callable, Any, Dict
from functools import wraps
import logging
from datetime import date
from .models import Message, User
from .base_controller import BaseController
import json

logger = logging.getLogger(__name__)
T = TypeVar('T')

def db_operation(f: Callable[..., Any]):
    """数据库操作装饰器，处理错误和日志"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            return None
    return wrapper

class DBController(BaseController):
    """统一的数据库控制器"""
    
    async def init(self):
        """初始化数据库"""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')

    # Message operations
    @db_operation
    async def save_message(self, message: Message) -> bool:
        """保存消息"""
        data = message.to_dict()
        
        # 确保 metadata 被转换为 JSON 字符串
        metadata_json = json.dumps(data.get('metadata', {}), ensure_ascii=False) if data.get('metadata') else None
        
        if await self.get_message(message.message_id, message.chat_id):
            return await self.execute(
                'UPDATE messages SET text = ?, metadata = ?, chat_type = ? WHERE message_id = ? AND chat_id = ?',
                (data.get('text'), metadata_json, data.get('chat_type'), data['message_id'], data['chat_id'])
            )
        
        return await self.execute(
            'INSERT INTO messages (message_id, chat_id, user_id, text, type, chat_type, reply_to_message_id, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                data['message_id'],
                data['chat_id'],
                data.get('user_id'),
                data.get('text'),
                data['type'],
                data.get('chat_type'),
                data.get('reply_to_message_id'),
                metadata_json
            )
        )

    @db_operation
    async def update_message(self, message: Message) -> bool:
        """更新消息内容和元数据"""
        data = message.to_dict()
        return await self.execute('''
            UPDATE messages 
            SET text = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
            WHERE message_id = ? AND chat_id = ?
        ''', (
            data.get('text'),
            json.dumps(data.get('metadata', {}), ensure_ascii=False),
            data['message_id'],
            data['chat_id']
        ))

    @db_operation
    async def get_message(self, message_id: int, chat_id: int) -> Optional[Message]:
        """获取消息"""
        data = await self.fetch_one(
            'SELECT * FROM messages WHERE message_id = ? AND chat_id = ?',
            (message_id, chat_id)
        )
        return Message(**data) if data else None

    @db_operation
    async def get_chat_messages(self, chat_id: int, limit: int = 100) -> List[Message]:
        """获取聊天消息"""
        rows = await self.fetch_all(
            'SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?',
            (chat_id, limit)
        )
        return [Message(**row) for row in rows]

    # User operations
    @db_operation
    async def save_user(self, user: User) -> bool:
        """保存用户"""
        data = user.to_dict()
        if await self.get_user(user.user_id):
            return await self.execute(
                'UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?',
                (data.get('username'), data.get('first_name'), data.get('last_name'), data['user_id'])
            )
        return await self.execute(
            'INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
            (data['user_id'], data.get('username'), data.get('first_name'), data.get('last_name'))
        )

    @db_operation
    async def get_user(self, user_id: int) -> Optional[User]:
        """获取用户"""
        data = await self.fetch_one('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return User(**data) if data else None

    @db_operation
    async def ensure_user_exists(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """确保用户存在，不存在则创建"""
        user = await self.get_user(user_id)
        if not user:
            return await self.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
            ''', (user_id, username, first_name, last_name))
        return True

    @db_operation
    async def increment_user_usage(self, user_id: int) -> Optional[User]:
        """增加用户使用次数并返回更新后的用户数据"""
        await self.execute('''
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
        return await self.get_user(user_id)

    @db_operation
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

    @db_operation
    async def get_top_users_by_usage(self, limit: int = 10) -> List[User]:
        """获取使用次数最多的用户"""
        rows = await self.fetch_all('''
            SELECT * FROM users 
            ORDER BY total_usage_count DESC 
            LIMIT ?
        ''', (limit,))
        return [User(**row) for row in rows]

    @db_operation
    async def get_active_users_today(self) -> List[User]:
        """获取今日活跃用户"""
        rows = await self.fetch_all('''
            SELECT * FROM users 
            WHERE date(last_usage_date) = date('now')
            ORDER BY daily_usage_count DESC
        ''')
        return [User(**row) for row in rows]

    @db_operation
    async def update_user_stats(self, user_id: int, *, submission: bool = False, approved: bool = False) -> bool:
        """更新用户统计"""
        updates = []
        if submission:
            updates.append("submission_count = submission_count + 1")
        if approved:
            updates.append("approved_count = approved_count + 1")
        if not updates:
            return True
            
        return await self.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
            (user_id,)
        )