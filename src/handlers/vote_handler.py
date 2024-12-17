from telegram import Update, Message, Poll
from telegram.ext import ContextTypes
from typing import Optional
import logging
from utils.telegram_handler import TelegramMessageHandler
from config.settings import CHANNEL_ID, GROUP_ID
from utils.buttons import get_vote_buttons
from utils.response_controller import ResponseController
from database.models import Message

logger = logging.getLogger(__name__)

class VoteHandler:
    def __init__(self, handler: Optional[TelegramMessageHandler]):
        self.handler = handler
        self.vote_duration = 24 * 60 * 60  # 24小时
    
    # 暂时弃用
    async def start_vote(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        original_message: Message,
        generated_content: str,
        classification_result: str
    ) -> Optional[Message]:
        """发起投票"""
        response_controller = ResponseController()
        
        if await response_controller.is_user_blacklisted(self.handler.user_id, context):
            await self.handler.send_notification("你已被禁止发起投票", auto_delete=True)
            return None
        
        try:
            # 先将原始消息转发到群组
            forwarded = await context.bot.forward_message(
                chat_id=GROUP_ID,
                from_chat_id=original_message.chat_id,
                message_id=original_message.message_id
            )

            # 限制投票问题长度
            vote_text = (
                f"{classification_result}\n"
                f"用户 {self.handler.update.effective_user.first_name} "
                f"(@{self.handler.update.effective_user.username}) 发起了投稿"
            )

            # 使用转发后的消息ID
            vote_message = await self.handler.bot.send_poll(
                chat_id=GROUP_ID,
                question=vote_text[:300],  # 限制长度
                options=["👍 同意", "👎 反对"],
                is_anonymous=True,
                type=Poll.REGULAR,
                open_period=self.vote_duration,
                reply_to_message_id=forwarded.message_id,  # 使用转发后的消息ID
                reply_markup=get_vote_buttons(),
                explanation=f"{classification_result}\n\n{generated_content}",  # 将分类结果放在explanation中
                explanation_parse_mode='HTML'
            )

            context.chat_data['vote_message_id'] = vote_message.message_id
            context.chat_data['vote_initiator'] = self.handler.user_id
            context.chat_data['original_message_id'] = original_message.message_id  # 保存原始消息ID
            context.chat_data['forwarded_message_id'] = forwarded.message_id  # 保存转发后的消息ID

            # 记录投票日志
            vote_log_data = {
                "vote_id": vote_message.message_id,
                "initiator": {
                    "id": self.handler.user_id,
                    "username": self.handler.update.effective_user.username,
                    "first_name": self.handler.update.effective_user.first_name
                },
                "original_message": {
                    "id": original_message.message_id,
                    "chat_id": original_message.chat_id
                },
                "classification": classification_result,
                "content": generated_content,
                "status": "started",
                "duration": self.vote_duration
            }
            self.handler.log_handler.log_vote(vote_log_data)

            # 保存投票消息到数据库
            vote_message = Message(
                message_id=vote_message.message_id,
                chat_id=GROUP_ID,
                user_id=self.handler.user_id,
                text=vote_text,
                type='vote',
                reply_to_message_id=forwarded.message_id,  # 使用转发后的消息ID
                metadata={
                    'content': generated_content,
                    'classification': classification_result,
                    'status': 'started',
                    'initiator_id': self.handler.user_id,
                    'original_message_id': original_message.message_id,
                    'forwarded_message_id': forwarded.message_id
                }
            )
            await context.bot_data['db'].save_message(vote_message)

            return vote_message

        except Exception as e:
            logger.error(f"Failed to start vote: {e}")
            await self.handler.send_notification(
                "发起投票失败，请重试",
                auto_delete=True
            )
            return None

    # 保留管理员手动操作的方法
    async def admin_approve(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """管理员强制通过"""
        response_controller = ResponseController()
        
        if not await response_controller.is_user_admin(self.handler.user_id, context):
            return
        
        try:
            vote_message_id = context.chat_data.get('vote_message_id')
            vote_message = await context.bot_data['db'].get_message(vote_message_id, GROUP_ID)
            if vote_message:
                vote_message.metadata['status'] = 'approved'
                vote_message.metadata['admin_id'] = self.handler.user_id
                await context.bot_data['db'].save_message(vote_message)
            
            await self._publish_content(context)
        except Exception as e:
            logger.error(f"Failed to admin approve: {e}")

    async def admin_reject(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """管理员强制拒绝"""
        try:
            vote_message_id = context.chat_data.get('vote_message_id')
            vote_log_data = {
                "vote_id": vote_message_id,
                "status": "admin_rejected",
                "admin_id": self.handler.user_id
            }
            self.handler.log_handler.log_vote(vote_log_data)
            
            await self._reject_content(context)
            context.chat_data.clear()
        except Exception as e:
            logger.error(f"Failed to admin reject: {e}")

    # 保留原有的辅助方法
    async def _publish_content(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """发布通过的内容"""
        try:
            vote_message_id = context.chat_data.get('vote_message_id')
            vote_data = await context.bot_data['db'].get_vote_by_message(
                vote_message_id, 
                GROUP_ID
            )
            
            if not vote_data:
                logger.error("Vote data not found")
                return
            
            # 组装发布内容
            content = (
                f"<b>投稿内容</b>\n"
                f"<blockquote expandable>{vote_data.contribute}</blockquote>\n"
                f"<b>AI分析</b>\n"
                f"<blockquote expandable>{vote_data.analyse}</blockquote>"
            )
                
            try:
                # 发送内容
                sent_message = await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=content,
                    parse_mode='HTML'
                )
                
                # 通知投稿者
                await context.bot.send_message(
                    chat_id=vote_data.user_id,
                    text="✨ 恭喜！你的投稿已通过并发布"
                )
            except Exception as e:
                logger.error(f"Error sending content: {e}")
                # 降级处理
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=content,
                    parse_mode=None
                )
        except Exception as e:
            logger.error(f"Failed to publish content: {e}")

    async def _reject_content(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理被拒绝的内容"""
        try:
            user_id = context.chat_data.get('vote_initiator')
            if user_id:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="感谢你的投稿，虽然没通过，但不是你的问题哦"
                )
        except Exception as e:
            logger.error(f"Failed to handle rejected content: {e}") 