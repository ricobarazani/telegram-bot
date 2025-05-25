import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.reply("שלום! קיבלתי את ההודעה שלך 👋")

@dp.message(F.text == "/list")
async def list_handler(message: Message):
    await message.reply("📋 הנה רשימת הקבוצות שלך (דוגמה)")

@dp.message(F.text == "/adminlist")
async def adminlist_handler(message: Message):
    await message.reply("👮‍♂️ הנה רשימת המנהלים שלך (דוגמה)")

async def on_startup():
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot, on_startup=on_startup)

if __name__ == "__main__":
    web.run_app(app, port=8080)