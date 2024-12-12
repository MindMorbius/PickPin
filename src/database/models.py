from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, date

@dataclass
class Message:
    message_id: int
    chat_id: int
    user_id: Optional[int] = None
    text: Optional[str] = None
    type: str = ""
    chat_type: str = "bot"
    reply_to_message_id: Optional[int] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    is_blocked: bool = False
    submission_count: int = 0
    approved_count: int = 0
    total_usage_count: int = 0
    daily_usage_count: int = 0
    last_usage_date: Optional[date] = None
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @property
    def can_use(self, daily_limit: int = 50) -> bool:
        """检查用户是否可以继续使用"""
        if self.last_usage_date != date.today():
            return True
        return self.daily_usage_count < daily_limit 