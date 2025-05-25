import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

API_TOKEN = "7549307640:AAFZxRBWhgrK3FYbWViwMjnliysAz_Ol0sI"
WEBHOOK_HOST = "https://telegram-bot-0269.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

@router.message(F.text)
async def echo_handler(message: Message):
    await message.answer(f"👋 שלום! קיבלתי את ההודעה שלך: {message.text}")

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    await on_startup(bot)
    setup_application(app, dp, bot=bot)
    return app

if __name__ == "__main__":
    web.run_app(main(), host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
