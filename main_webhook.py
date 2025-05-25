import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram import types
from aiohttp import web

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text)
async def echo_handler(message: Message):
    await message.reply(f"שָׁלוֹם! קיבלתי את ההודעה שלך: {message.text} 👋")

app = web.Application()
SimpleRequestHandler(dp, bot).register(app, path="/webhook")

async def on_startup(app: web.Application):
    webhook_url = os.getenv("WEBHOOK_URL")
    await bot.set_webhook(f"{webhook_url}/webhook")

app.on_startup.append(on_startup)
setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    web.run_app(app, port=8080)
