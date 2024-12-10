from telegram import Update, Message, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import NetworkError, TimedOut
import logging
import asyncio
from typing import Optional, Tuple, AsyncGenerator, Any
from handlers.log_handler import LogHandler

logger = logging.getLogger(__name__)

class TelegramMessageHandler:
    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.update = update
        self.context = context
        self.bot = context.bot
        self.message = update.effective_message
        self.chat_id = self.message.chat.id if self.message else None
        # 只在非频道消息时获取用户ID
        self.user_id = update.effective_user.id if update.effective_user else None
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.notification_delay = 10  # seconds for auto-delete notifications
        self.command_notification_delay = 5  # seconds for command response notifications
        self.log_handler = LogHandler()

    async def send_message(
        self, 
        text: str, 
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None,
        chat_id: Optional[int] = None,
        delete_command: bool = False,
        log_action: bool = True

    ) -> Optional[Message]:
        """发送消息，带重试机制"""

        if delete_command and self.message:
            await self.delete_message(self.message)
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                sent_message = await self.bot.send_message(
                    chat_id=chat_id or self.chat_id,
                    text=text,
                    reply_to_message_id=reply_to_message_id,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                if sent_message and log_action:
                    self.log_handler.log_bot_action("send", sent_message, self.update)
                return sent_message
            except (NetworkError, TimedOut) as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    logger.error(f"Failed to send message after {self.max_retries} attempts: {e}")
                    return None
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return None

    async def edit_message(
        self,
        message: Message,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None
    ) -> bool:
        """编辑消息，带重试机制和更新检测"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # 检查是否需要更新
                if (message.text == text and 
                    message.reply_markup == reply_markup and 
                    message.parse_mode == parse_mode):
                    logger.info("No changes detected, skipping update.")
                    return True

                edited_message = await message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                if edited_message:
                    self.log_handler.log_bot_action("edit", edited_message, self.update)
                return True
            except (NetworkError, TimedOut) as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    logger.error(f"Failed to edit message after {self.max_retries} attempts: {e}")
                    return False
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    logger.error(f"Error editing message: {e}")
                return False

    async def forward_message(
        self,
        to_chat_id: int,
        message: Message
    ) -> Optional[Message]:
        """转发消息，带重试机制"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                return await self.bot.forward_message(
                    chat_id=to_chat_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id
                )
            except (NetworkError, TimedOut) as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    logger.error(f"Failed to forward message after {self.max_retries} attempts: {e}")
                    return None
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Error forwarding message: {e}")
                return None

    async def delete_message(self, message: Message) -> bool:
        """删除消息，带重试机制"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                await message.delete()
                return True
            except (NetworkError, TimedOut) as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    logger.error(f"Failed to delete message after {self.max_retries} attempts: {e}")
                    return False
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                return False

    async def stream_process_message(
        self,
        processor: AsyncGenerator[Tuple[str, bool], Any],
        status_message: Message,
        final_markup: Optional[InlineKeyboardMarkup] = None
    ) -> Optional[str]:
        """处理流式响应并更新消息，使用兜底策略"""
        last_text = ""
        try:
            async for response_text, should_update in processor:
                if should_update and response_text != last_text:
                    last_text = response_text
                    success = await self.edit_message(status_message, response_text)
                    if not success:
                        return None

            if last_text and final_markup:
                await self.edit_message(status_message, last_text, reply_markup=final_markup)
            return last_text
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            # 使用兜底策略，发送错误提示和最后的有效信息
            fallback_text = f"{last_text}\n\n处理失败，请重试" if last_text else "处理失败，请重试"
            await self.edit_message(status_message, fallback_text)
            return None 

    async def send_notification(
        self,
        text: str,
        reply_to_message_id: Optional[int] = None,
        auto_delete: bool = True,
        delete_command: bool = False,
        chat_id: Optional[int] = None,
    ) -> Optional[Message]:
        """发送通知消息，可选自动删除
    
        Args:
            text: 通知文本
            reply_to_message_id: 要回复的消息ID
            auto_delete: 是否自动删除通知消息
            delete_command: 是否删除触发消息（仅用于命令场景）
            chat_id: 指定聊天ID
        """
        try:
            notify_msg = await self.send_message(
                text=text,
                reply_to_message_id=reply_to_message_id,
                chat_id=chat_id,
                log_action=False
            )
            
            if auto_delete:
                await asyncio.sleep(self.notification_delay)
                if notify_msg:
                    await self.delete_message(notify_msg)
                if delete_command and self.message:
                    await self.delete_message(self.message)
                    
            return notify_msg
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return None

    async def reply_to_command(
        self,
        text: str,
        reply_to_message_id: Optional[int] = None,
        auto_delete: bool = True,
        delete_command: bool = True,
        delete_delay: Optional[int] = None,
        chat_id: Optional[int] = None,
    ) -> Optional[Message]:
        """专门用于回复命令的消息
        
        Args:
            text: 回复文本
            auto_delete: 是否自动删除
            delete_delay: 自定义删除延迟时间（秒）
        """
        try:
            reply_msg = await self.send_message(
                text=text,
                reply_to_message_id=reply_to_message_id,
                chat_id=chat_id,
                log_action=False
            )
            
            if auto_delete:
                delay = delete_delay or self.command_notification_delay
                await asyncio.sleep(delay)
                if reply_msg:
                    await self.delete_message(reply_msg)
                if delete_command and self.message:
                    await self.delete_message(self.message)
                    
            return reply_msg
        except Exception as e:
            logger.error(f"Failed to reply to command: {e}")
            return None