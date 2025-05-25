from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

@dp.message(Command(commands=["start"]))
async def start_handler(message: Message):
    await message.reply("שלום! אני בוט שמנהל קבוצות טלגרם 👋")

@dp.message(Command(commands=["list"]))
async def list_handler(message: Message):
    await message.reply("📋 הנה הרשימה שלך:")

@dp.message(Command(commands=["adminlist"]))
async def adminlist_handler(message: Message):
    await message.reply("👮‍♂️ הנה רשימת המנהלים:")

@dp.message()
async def fallback_handler(message: Message):
    await message.reply("🤖 אני לא מבין את הפקודה הזאת. נסה שוב!")

app = web.Application()
SimpleRequestHandler(dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot)

async def on_startup():
    webhook_url = "https://telegram-bot-0269.onrender.com/webhook"
    await bot.set_webhook(webhook_url)

app.on_startup.append(lambda _: on_startup())
