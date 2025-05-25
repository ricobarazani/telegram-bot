import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply("👋 שלום! קיבלתי את ההודעה שלך: /start")

@dp.message(commands=["list"])
async def cmd_list(message: types.Message):
    await message.reply("📋 הנה הרשימה שלך: ...")

@dp.message(commands=["adminlist"])
async def cmd_adminlist(message: types.Message):
    await message.reply("👮‍♂️ הנה רשימת המנהלים: ...")

@dp.message()
async def handle_unknown(message: types.Message):
    await message.reply("❓ לא זיהיתי את הפקודה. נסה שוב.")

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    await bot.set_my_commands([
        BotCommand(command="start", description="התחל את הבוט"),
        BotCommand(command="list", description="קבל רשימה"),
        BotCommand(command="adminlist", description="רשימת מנהלים")
    ])

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot, on_startup=on_startup)