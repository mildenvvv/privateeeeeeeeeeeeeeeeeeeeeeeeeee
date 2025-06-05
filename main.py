import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import load_config
from bot.handlers import register_handlers
from bot.middlewares.db_session_middleware import DBSessionMiddleware
from db import init_db
from utils.logger import log
from utils.gift_parser import start_gift_parsing_loop

from utils.access_manager import load_allowed_users
from bot.middlewares.acl import AccessControlMiddleware

config = load_config()

default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=config["bot_token"], default=default_properties)
dp = Dispatcher(storage=MemoryStorage())


async def on_startup_tasks():
    log.info("Initializing database...")
    init_db()
    log.info("Database initialized successfully")

    log.info("Starting gift parsing loop...")
    asyncio.create_task(start_gift_parsing_loop())


async def main():
    log.info("Starting bot...")

    allowed_users = load_allowed_users()
    if not allowed_users:
        log.warning("Список разрешенных пользователей пуст. Бот будет недоступен никому!")
    await on_startup_tasks()
    dp.update.middleware(AccessControlMiddleware(allowed_users))
    dp.update.middleware(DBSessionMiddleware())
    register_handlers(dp)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log.exception(f"Bot stopped due to an error: {e}")