import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.webhook import CheckSignatureMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://telegram-bot-0269.onrender.com{WEBHOOK_PATH}"

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()

@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.reply("שלום! 👋 קיבלתי את ההודעה שלך.")

@router.message(F.text)
async def echo_handler(message: Message):
    await message.reply(f"קיבלתי את ההודעה שלך: {message.text}")

dp.include_router(router)

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    dp.startup.register(on_startup)
    webhook_request_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_request_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    return app

if __name__ == "__main__":
    asyncio.run(main())
