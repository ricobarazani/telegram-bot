import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Missing BOT_TOKEN environment variable")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# פונקציית התחלה עם הודעת הסבר
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.reply("שלום! אני בוט שמנהל קבוצות טלגרם 👋\n\n"
                        "פקודות זמינות:\n"
                        "/list – לקבלת רשימת כל המשתמשים\n"
                        "/adminlist – לקבלת רשימת מנהלים בלבד")

# פקודת list - רשימת כל המשתמשים
@dp.message(F.text == "/list")
async def list_users(message: Message):
    chat_id = message.chat.id
    try:
        admins = await bot.get_chat_administrators(chat_id)
        members = [admin.user.full_name for admin in admins]
        await message.reply("\n".join(members))
    except Exception as e:
        await message.reply(f"שגיאה בקבלת המידע: {e}")

# פקודת adminlist - רשימת מנהלים
@dp.message(F.text == "/adminlist")
async def admin_list(message: Message):
    try:
        chat_id = message.chat.id
        admins = await bot.get_chat_administrators(chat_id)
        admin_names = [admin.user.full_name for admin in admins]
        await message.reply("מנהלים מאושרים:\n" + "\n".join(admin_names))
    except Exception as e:
        await message.reply(f"שגיאה: {e}")

# Webhook setup
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await bot.set_webhook("https://telegram-bot-0269.onrender.com/webhook")

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot, on_startup=on_startup)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(app, port=8000)
