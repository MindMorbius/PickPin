import logging
from telegram import Update, BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue, PollHandler
from telegram.error import NetworkError, TimedOut
import asyncio
from config.settings import TELEGRAM_BOT_TOKEN, HTTP_PROXY, TELEGRAM_USER_ID
from handlers.command import start_command, get_id_command, analyze_command, summarize_command
from handlers.conversation import handle_message
from handlers.callback import handle_callback
from config.settings import AI_PROVIDER, OPENAI_MODEL, GOOGLE_MODEL, CHANNEL_ID, GROUP_ID
from database.message_db import MessageDB

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    # 创建 JobQueue 实例
    job_queue = JobQueue()
    
    application = Application.builder()\
        .token(TELEGRAM_BOT_TOKEN)\
        .proxy(HTTP_PROXY)\
        .get_updates_proxy(HTTP_PROXY)\
        .connect_timeout(30.0)\
        .read_timeout(30.0)\
        .write_timeout(30.0)\
        .pool_timeout(30.0)\
        .job_queue(job_queue)\
        .build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("getid", get_id_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("summarize", summarize_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.CAPTION) & ~filters.COMMAND, 
        handle_message
    ))

    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        error = context.error
        logger.error(f"Error type: {type(error)}")
        
        if isinstance(error, NetworkError):
            logger.error(f"Network error occurred: {error}")
            # 网络错误，等待后重试
            await asyncio.sleep(1)
        elif isinstance(error, TimedOut):
            logger.error(f"Request timed out: {error}")
            # 超时错误，等待后重试
            await asyncio.sleep(0.5)
        else:
            logger.error(f"Update {update} caused error {error}")
            # 其他错误
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "抱歉，处理消息时出现错误，请稍后重试。"
                )
    
    application.add_error_handler(error_handler)

    async def post_init(app: Application) -> None:
        logger.info("Bot is starting up...")
        
        # 初始化消息数据库
        message_db = MessageDB()
        await message_db.init()
        app.bot_data['message_db'] = message_db
        
        # 先删除所有命令
        await app.bot.delete_my_commands()
        
        # 更新命令列表
        commands = [
            BotCommand("start", "启动机器人"),
            BotCommand("getid", "获取用户和群组ID"),
            BotCommand("analyze", "分析引用的消息"),
            BotCommand("summarize", "总结引用的消息")
        ]
        
        # 设置管理员私聊命令
        await app.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=TELEGRAM_USER_ID))
        # 设置群组命令
        await app.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=GROUP_ID))
        
        await app.bot.send_message(
            chat_id=TELEGRAM_USER_ID,
            parse_mode='Markdown',
            text="🤖 PickPin - 为RKPin频道提供信息处理和投稿服务\n\n"
                 "✅ 机器人已启动完成\n"
                 "🔑 可用命令:\n"
                 "- /start - 启动机器人\n"
                 "- /getid - 获取用户和群组ID\n"
                 "- /analyze - 分析引用的消息\n"
                 "- /summarize - 总结引用的消息\n\n"
                 f"🔌 AI提供商: {AI_PROVIDER}\n"
                 f"🤖 AI模型: {OPENAI_MODEL if AI_PROVIDER == 'openai' else GOOGLE_MODEL}"
        )
    
    application.post_init = post_init
    
    # 添加重试逻辑
    while True:
        try:
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,  # 启动时忽略积压的更新
                poll_interval=1.0,  # 轮询间隔
                timeout=30  # 轮询超时
            )
        except Exception as e:
            logger.error(f"Polling error: {e}")
            logger.info("Waiting 10 seconds before retry...")
            asyncio.sleep(10)
            continue

if __name__ == "__main__":
    main() 