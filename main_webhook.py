import re
import asyncio
import json
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

DATA_FILE = "group_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_group(chat_id):
    data = load_data()
    return data.get(str(chat_id), {"admins": [], "approved": []})

def set_group(chat_id, group):
    data = load_data()
    data[str(chat_id)] = group
    save_data(data)

@router.message(Command("start"))
async def start_handler(message: Message):
    text = (
        "🤖 שלום! אני בוט שמנהל קבוצות טלגרם.

"
        "📌 הנה הפקודות הזמינות:
"
        "/adminlist - רשימת מנהלים
"
        "/approve <id> - לאשר משתמש
"
        "/list - רשימת משתמשים מאושרים

"
        "👮🏼‍♂️ רק מנהלים יכולים לבצע שינויים."
    )
    await message.answer(text)

@router.message(Command("adminlist"))
async def adminlist_handler(message: Message):
    chat_id = message.chat.id
    group = get_group(chat_id)
    lines = [f"<code>{admin}</code>" for admin in group["admins"]]
    if not lines:
        await message.reply("אין מנהלים רשומים.")
        return
    await message.reply("👮🏼‍♂️ הנה רשימת המנהלים:
" + "\n".join(lines))

@router.message(Command("list"))
async def approved_list_handler(message: Message):
    chat_id = message.chat.id
    group = get_group(chat_id)
    lines = [f"<code>{uid}</code>" for uid in group["approved"]]
    if not lines:
        await message.reply("⚠️ אין משתמשים מאושרים.")
        return
    await message.reply("✅ משתמשים מאושרים:
" + "\n".join(lines))

@router.message()
async def handle_message(message: Message):
    text = message.text or ""
    chat_id = message.chat.id
    sender = message.from_user
    group = get_group(chat_id)

    if sender.username and f"@{sender.username}" in group["admins"]:
        return
    if str(sender.id) in group["approved"] or sender.username in group["approved"]:
        return

    if re.search(r"(https?://|t\.me/|@\w+)", text):
        await message.delete()
        if group["admins"]:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=admin, url=f"https://t.me/{admin[1:]}")]
                    for admin in group["admins"]
                ]
            )
            await message.answer("⚠️ פרסמת קישור בקבוצה, מי לאשר את ההודעה שלך?", reply_markup=kb)
        else:
            await message.answer("🚫 ההודעה נחסמה. לא הוגדרו מנהלים לאישור.")

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook("https://telegram-bot-0269.onrender.com/webhook")

def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot, on_startup=on_startup)
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_webhook:main", host="0.0.0.0", port=8000, reload=True)
