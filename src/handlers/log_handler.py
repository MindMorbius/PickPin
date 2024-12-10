import json
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update, Message
from typing import Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

class LogHandler:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 按日期创建日志文件
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.message_log_file = self.log_dir / f"messages_{self.date}.jsonl"
        self.bot_log_file = self.log_dir / f"bot_{self.date}.jsonl"

    def _write_log(self, data: Dict[str, Any], log_file: Path) -> None:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")

    def log_message(self, update: Update) -> None:
        """记录完整的Update对象"""
        try:
            log_data = {
                "update": update.to_dict()  # 记录完整的update对象
            }
            self._write_log(log_data, self.message_log_file)
        except Exception as e:
            logger.error(f"Failed to log message: {e}")

    def log_bot_action(self, action_type: str, message: Message, update: Update) -> None:
        """记录机器人动作的Message对象"""
        try:
            log_data = {
                "action_type": action_type,
                "message": message.to_dict(),  # 记录发送或编辑后的消息对象
                "update": update.to_dict()  # 记录完整的update对象
            }
            self._write_log(log_data, self.bot_log_file)
        except Exception as e:
            logger.error(f"Failed to log bot action: {e}") 