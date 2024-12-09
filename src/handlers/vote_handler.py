from telegram import Update, Message, Poll
from telegram.ext import ContextTypes
from typing import Optional
import logging
from utils.telegram_handler import TelegramMessageHandler
from config.settings import CHANNEL_ID, GROUP_ID
from utils.buttons import get_vote_buttons

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
        try:
            # 保存投票相关信息
            context.chat_data['vote_content'] = generated_content
            context.chat_data['original_message'] = original_message
            context.chat_data['vote_initiator'] = self.handler.user_id

            vote_text = (
                f"{classification_result}\n\n"
                f"用户 {self.handler.update.effective_user.first_name} "
                f"(@{self.handler.update.effective_user.username}) 发起了投稿"
            ).replace('\n\n\n', '\n\n')

            # 发送投票，1小时后自动关闭
            return await self.handler.bot.send_poll(
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
        try:
            await self._publish_content(context)
            context.chat_data.clear()
        except Exception as e:
            logger.error(f"Failed to admin approve: {e}")

    async def admin_reject(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """管理员强制拒绝"""
        try:
            await self._reject_content(context)
            context.chat_data.clear()
        except Exception as e:
            logger.error(f"Failed to admin reject: {e}")

    # 保留原有的辅助方法
    async def _publish_content(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """发布通过的内容"""
        try:
            original_message = context.chat_data.get('original_message')
            generated_content = context.chat_data.get('vote_content')

            if not all([original_message, generated_content]):
                return

            # 转发原始消息到频道
            forwarded = await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=original_message.chat_id,
                message_id=original_message.message_id
            )

            if forwarded:
                try:
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=generated_content,
                        reply_to_message_id=forwarded.message_id,
                        parse_mode='Markdown'
                    )
                except Exception:
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=generated_content,
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