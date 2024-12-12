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
    
    async def start_vote(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        original_message: Message,
        generated_content: str,
        classification_result: str
    ) -> Optional[Message]:
        """发起投票"""
        response_controller = ResponseController()
        
        # 检查发起投票的用户权限
        if response_controller.is_user_blacklisted(self.handler.user_id):
            await self.handler.send_notification("你已被禁止发起投票", auto_delete=True)
            return None
        
        try:
            vote_text = (
                f"{classification_result}\n\n"
                f"用户 {self.handler.update.effective_user.first_name} "
                f"(@{self.handler.update.effective_user.username}) 发起了投稿"
            ).replace('\n\n\n', '\n\n')

            # 发送投票，24小时后自动关闭
            vote_message = await self.handler.bot.send_poll(
                chat_id=GROUP_ID,
                question=vote_text,
                options=["👍 同意", "👎 反对"],
                is_anonymous=True,
                type=Poll.REGULAR,
                open_period=self.vote_duration,
                reply_to_message_id=original_message.message_id,
                reply_markup=get_vote_buttons(),  # 保留管理员操作按钮
                explanation=generated_content,
                explanation_parse_mode='HTML'
            )

            # 在发送投票后保存投票消息ID到context
            context.chat_data['vote_message_id'] = vote_message.message_id
            context.chat_data['vote_initiator'] = self.handler.user_id

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
                reply_to_message_id=original_message.message_id,
                metadata={
                    'content': generated_content,
                    'classification': classification_result,
                    'status': 'started',
                    'initiator_id': self.handler.user_id
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
        
        if not response_controller.is_user_admin(self.handler.user_id):
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
            if not vote_message_id:
                return

            # 从数据库获取投票信息
            vote_data = await context.bot_data['db'].get_message(vote_message_id, GROUP_ID)
            if not vote_data:
                logger.error("Vote data not found in database")
                return

            # 获取原始消息ID和生成的内容
            metadata = vote_data.get('metadata', {})
            reply_to_message_id = vote_data.get('reply_to_message_id')
            generated_content = metadata.get('content')

            if not all([reply_to_message_id, generated_content]):
                logger.error("Missing required vote data")
                return

            # 转发原始消息到频道
            forwarded = await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=GROUP_ID,
                message_id=reply_to_message_id
            )

            if forwarded:
                try:
                    # 发送生成的内容
                    sent_message = await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=generated_content,
                        reply_to_message_id=forwarded.message_id,
                        parse_mode='Markdown'
                    )
                    
                    # 通知投稿者
                    initiator_id = metadata.get('initiator_id')
                    if initiator_id:
                        await context.bot.send_message(
                            chat_id=initiator_id,
                            text="✨ 恭喜！你的投稿已通过并发布"
                        )
                except Exception as e:
                    logger.error(f"Error sending content: {e}")
                    # 发送失败时的降级处理
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=generated_content,
                        parse_mode=None,
                        reply_to_message_id=forwarded.message_id
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