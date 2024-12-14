from typing import Optional, List, TypeVar, Type, Callable, Any, Dict
from functools import wraps
import logging
from datetime import date
from .models import Message, User
from .base_controller import BaseController
from .message_controller import MessageController
from .user_controller import UserController
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

class DBController:
    """统一的数据库控制器"""
    
    def __init__(self, db_path: str = "data/app.db"):
        self.message_controller = MessageController(db_path)
        self.user_controller = UserController(db_path)
    
    async def init(self):
        """初始化数据库"""
        await self.message_controller.init()
        await self.user_controller.init()

    # Message operations
    @db_operation
    async def save_message(self, message: Message) -> bool:
        return await self.message_controller.save_message(message.to_dict())

    @db_operation
    async def get_message(self, message_id: int, chat_id: int) -> Optional[Message]:
        data = await self.message_controller.get_message(message_id, chat_id)
        return Message(**data) if data else None

    @db_operation
    async def get_chat_messages(self, chat_id: int, limit: int = 100) -> List[Message]:
        messages = await self.message_controller.get_chat_messages(chat_id, limit)
        return [Message(**msg) for msg in messages]

    @db_operation
    async def update_message(self, message: Message) -> bool:
        return await self.message_controller.update_message(message.to_dict())

    # User operations
    @db_operation
    async def save_user(self, user: User) -> bool:
        return await self.user_controller.save_user(user.to_dict())

    @db_operation
    async def get_user(self, user_id: int) -> Optional[User]:
        data = await self.user_controller.get_user(user_id)
        return User(**data) if data else None

    @db_operation
    async def ensure_user_exists(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        user = await self.get_user(user_id)
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            return await self.save_user(user)
        return True

    @db_operation
    async def increment_user_usage(self, user_id: int) -> Optional[User]:
        if await self.user_controller.increment_usage(user_id):
            return await self.get_user(user_id)
        return None