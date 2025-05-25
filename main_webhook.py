import json
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import BotCommand
from aiogram.filters import Command
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="התחל להשתמש בבוט"),
        BotCommand(command="/list", description="הצג את רשימת הקבוצות"),
        BotCommand(command="/adminlist", description="הצג את רשימת המנהלים"),
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.reply("שלום! 👋 אני בוט שמנהל קבוצות טלגרם. שלח לי פקודה כדי להתחיל:")

@dp.message(Command("list"))
async def handle_list(message: Message):
    await message.reply("📋 הנה רשימת הקבוצות שלך...")

@dp.message(Command("adminlist"))
async def handle_adminlist(message: Message):
    await message.reply("👮‍♂️ הנה רשימת המנהלים שלך...")

@dp.message()
async def fallback(message: Message):
    await message.reply(f"שָׁלוֹם! קיבלתי את ההודעה שלך: {message.text}")

async def on_startup(app: web.Application):
    await set_commands(bot)

async def on_shutdown(app: web.Application):
    logging.warning("Shutting down..")

def create_app():
    app = web.Application()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    bot.set_webhook("https://telegram-bot-0269.onrender.com/webhook")
    setup_application(app, dp, bot=bot)
    return app

app = create_app()
