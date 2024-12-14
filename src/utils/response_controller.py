from typing import Optional, Dict, Any, Tuple
from telegram import Update, Message
from telegram.ext import ContextTypes
import time
from config.settings import TELEGRAM_USER_ID, GROUP_ID
from config.response_settings import RESPONSE_SETTINGS
import logging

logger = logging.getLogger(__name__)

class ResponseController:
    def __init__(self):
        self._last_response_time = {}  # 记录最后响应时间


    async def is_user_allowed(self, update: Update, is_admin: bool, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查用户是否有权限
        
        Args:
            update: 更新
            is_admin: 是否需要管理员权限
            context: 上下文，用于访问数据库
    
        Returns:
            bool: 是否允许访问
        """
        # 确保用户存在
        user = update.effective_user
        await context.bot_data['db'].ensure_user_exists(
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # 如果需要管理员权限，检查用户是否为管理员
        if is_admin:
            return await self.is_user_admin(user.id, context)
    
        # 检查用户是否被拉黑
        if await self.is_user_blacklisted(user.id, context):
            return False
            
        return True


    async def is_user_admin(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查用户是否为管理员"""
        user = await context.bot_data['db'].get_user(user_id)
        return user and user.is_admin  # 使用属性访问方式

    async def is_user_blacklisted(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查用户是否在黑名单中"""
        user = await context.bot_data['db'].get_user(user_id)
        return user and user.is_blocked  # 使用属性访问方式

    async def analyze_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, str, bool]:
        # 确保用户存在
        user = update.effective_user
        await context.bot_data['db'].ensure_user_exists(
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        """分析更新，返回是否响应、消息来源、是否为更新、消息类型"""
        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user

        # logger.info(f"类型：{chat.type}, 用户：{user}")
        
        if not message or not chat:
            return False, "unknown", False
    
        # 判断是否为更新
        is_update = update.edited_message is not None or update.edited_channel_post is not None
    
        # 使用 chat.type 来区分消息来源
        if chat.type == 'channel':
            should_respond = await self._check_channel_chat(message)
        elif chat.type == 'private':
            should_respond= await self._check_private_chat(message, user, context)
        elif chat.type in ['group', 'supergroup']:
            should_respond = await self._check_group_chat(message, user, context)
        else:
            should_respond = False

        # 增加使用次数
        if should_respond:
            await context.bot_data['db'].increment_user_usage(user.id)
    
        return should_respond, chat.type, is_update
        
    async def _check_private_chat(self, message: Message, user, context: ContextTypes.DEFAULT_TYPE) -> bool:
        settings = RESPONSE_SETTINGS['private_chat']

        # logger.info(f"用户ID: {user.id}, 用户名: {user.username}, 用户名: {user.first_name}")

        # 管理员正常响应
        if await self.is_user_admin(user.id, context):
            return True
        
        # if not settings['enabled']:
        #     return False
        
        # 检查黑名单
        if await self.is_user_blacklisted(user.id, context):
            return False

        # 检查命令权限
        if message.text and message.text.startswith('/'):
            command = message.text.split()[0][1:]
            return command in settings['allowed_commands']
        return False
   
    async def _check_group_chat(self, message: Message, user, context: ContextTypes.DEFAULT_TYPE) -> bool:
        settings = RESPONSE_SETTINGS['group_chat']
        
        if not settings['enabled']:
            return False
        
        # 检查群组权限
        if str(message.chat.id) not in settings['allowed_groups']:
            return False
        
        # 检查用户黑名单
        if await self.is_user_blacklisted(user.id, context):
            return False
        
        # 检查自动转发
        if message.is_automatic_forward and not settings['respond_to_auto_forward']:
            return False
        
        # 检查命令权限
        if message.text and message.text.startswith('/'):
            command = message.text.split()[0][1:]
            return command in settings['allowed_commands']
        
        # 检查@和回复
        is_mention = self._check_mention(message)
        is_reply = self._check_reply(message)
        
        if settings['mention_required'] and not (is_mention or is_reply):
            return False
        
        return True

    def _check_mention(self, message: Message) -> bool:
        """检查是否@机器人"""
        if not message.entities:
            return False
        
        for entity in message.entities:
            if entity.type == 'mention':
                mention = message.text[entity.offset:entity.offset + entity.length]
                if mention == '@rk_pin_bot':  # 替换为你的机器人用户名
                    return True
        return False
    
    def _check_reply(self, message: Message) -> bool:
        """检查是否回复机器人消息"""
        if not message.reply_to_message or not message.reply_to_message.from_user:
            return False
        return message.reply_to_message.from_user.username == 'rk_pin_bot'  # 替换为你的机器人用户名

    async def _check_channel_chat(self, message: Message) -> bool:
        settings = RESPONSE_SETTINGS['channel_chat']
        
        if not settings['enabled']:
            return False
        
        # 检查频道权限
        if str(message.chat.id) not in settings['allowed_channels']:
            return False
        
        return True
