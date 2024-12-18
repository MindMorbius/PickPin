import logging
from telegram import Update, BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue, PollHandler
from telegram.error import NetworkError, TimedOut
import asyncio
from config.settings import TELEGRAM_BOT_TOKEN, HTTP_PROXY, TELEGRAM_USER_ID
from handlers.command import start_command, get_id_command, analyze_command, summarize_command, submit_command, help_command
from handlers.conversation import handle_message
from handlers.callback import handle_callback
from config.settings import AI_PROVIDER, OPENAI_MODEL, GOOGLE_MODEL, CHANNEL_ID, GROUP_ID
from database.db_controller import DBController
from datetime import datetime
import time  # 添加这个导入

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def register_commands(app: Application) -> None:
    # 清除所有作用域的命令
    for scope in [
        BotCommandScopeDefault(),
        BotCommandScopeAllPrivateChats(),
        BotCommandScopeChat(chat_id=TELEGRAM_USER_ID),
        BotCommandScopeChat(chat_id=GROUP_ID)
    ]:
        try:
            await app.bot.delete_my_commands(scope=scope)
        except Exception as e:
            logger.error(f"Error clearing commands for scope {scope}: {e}")
    
    # 定义命令
    base_commands = [
        BotCommand("start", "启动机器人"),
        BotCommand("getid", "获取用户和群组ID"),
        BotCommand("help", "查看帮助"),
    ]

    private_commands = [
        BotCommand("submit", "开始投稿"),
    ]

    public_commands = [
        BotCommand("analyze", "分析引用的消息"),
        BotCommand("summarize", "总结引用的消息"),
    ]
    
    admin_commands = base_commands + private_commands + public_commands + [
        BotCommand("user", "查看用户信息"),
        BotCommand("blacklist", "拉黑用户"),
        BotCommand("unblacklist", "解除拉黑"),
        BotCommand("admin", "查看管理员信息"),
        BotCommand("addadmin", "添加管理员"),
        BotCommand("removeadmin", "移除管理员"),
    ]

    # 注册管理员私聊命令
    await app.bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(chat_id=TELEGRAM_USER_ID)
    )

    # 注册群组命令
    await app.bot.set_my_commands(
        public_commands,
        scope=BotCommandScopeChat(chat_id=GROUP_ID)
    )
    # 注册默认命令
    await app.bot.set_my_commands(
        private_commands + base_commands,
        scope=BotCommandScopeDefault()
    )
    
    # 同时也注册到所有私聊作用域
    await app.bot.set_my_commands(
        private_commands + base_commands,
        scope=BotCommandScopeAllPrivateChats()
    )

async def post_init(app: Application) -> None:
    logger.info("Bot is starting up...")
    
    # 初始化数据库控制器
    db_controller = DBController("data/app.db")
    await db_controller.init()
    app.bot_data['db'] = db_controller
    

    # 注册命令
    await register_commands(app)
    
    # 发送启动通知
    await app.bot.send_message(
        chat_id=TELEGRAM_USER_ID,
        text="🤖 PickPin 已启动，现在时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

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

def setup_handlers(app: Application) -> None:
    # 命令处理器
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("getid", get_id_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("summarize", summarize_command))
    app.add_handler(CommandHandler("submit", submit_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # 回调处理器
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # 消息处理器 (放最后)
    app.add_handler(MessageHandler(
        filters.ALL,
        handle_message
    ))

    app.add_error_handler(error_handler)


def main() -> None:  # 改回同步函数
    # 创建 JobQueue 实例
    job_queue = JobQueue()
    
    while True:
        try:
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

            setup_handlers(application)
            application.post_init = post_init
            
            application.run_polling(  # 移除 await
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=1.0,
                timeout=30
            )
        except Exception as e:
            logger.error(f"Polling error: {e}")
            logger.info("Waiting 10 seconds before retry...")
            time.sleep(10)
            continue

if __name__ == "__main__":
    asyncio.run(main())  # 这行保持不变
  