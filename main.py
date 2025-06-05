import os
import asyncio
from aiohttp import web

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

# Создание бота и диспетчера
default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=config["bot_token"], default=default_properties)
dp = Dispatcher(storage=MemoryStorage())


async def on_startup(app: web.Application):
    log.info("🚀 Running startup tasks...")
    init_db()

    allowed_users = load_allowed_users()
    if not allowed_users:
        log.warning("⚠️ Список разрешенных пользователей пуст. Бот будет недоступен никому!")

    dp.update.middleware(AccessControlMiddleware(allowed_users))
    dp.update.middleware(DBSessionMiddleware())
    register_handlers(dp)

    # Запуск фоновой задачи
    asyncio.create_task(start_gift_parsing_loop())

    # Установка webhook
    webhook_url = f"{config['webhook_url']}/webhook"
    await bot.set_webhook(webhook_url)
    log.info(f"✅ Webhook set to {webhook_url}")


async def on_shutdown(app: web.Application):
    log.info("📴 Shutting down, removing webhook...")
    await bot.delete_webhook()


async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        await dp.feed_update(bot, data)
    except Exception as e:
        log.exception(f"❌ Failed to process update: {e}")
    return web.Response(status=200)


def create_app():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(create_app(), host="0.0.0.0", port=port)
