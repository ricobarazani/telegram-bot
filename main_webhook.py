import json
import logging
import re
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

BOT_TOKEN = "YOUR_BOT_TOKEN"
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"admins": [], "approved": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_group(chat_id):
    data = load_data()
    chat_id = str(chat_id)
    if chat_id not in data:
        data[chat_id] = {"admins": [], "approved": []}
        save_data(data)
    return data[chat_id]

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.reply("👋 שלום! אני בוט שמנהל קבוצות טלגרם.
"
                        "מנהלים יכולים לאשר משתמשים דרך הפקודות:
"
                        "/approve - לאשר משתמש
"
                        "/list - לראות את המאושרים
"
                        "/adminlist - רשימת מנהלים")

@dp.message(F.text == "/adminlist")
async def adminlist(message: Message):
    group = get_group(message.chat.id)
    lines = [f"• {admin}" for admin in group["admins"]]
    await message.reply("👤 מנהלים:
" + "
".join(lines))

@dp.message(F.text.startswith("/approve"))
async def approve(message: Message):
    group = get_group(message.chat.id)
    sender = message.from_user.username
    if sender not in group["admins"]:
        await message.reply("⛔ רק מנהלים יכולים לאשר משתמשים.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("📌 יש לציין את שם המשתמש לאישור.")
        return
    username = parts[1].lstrip("@")
    if username not in group["approved"]:
        group["approved"].append(username)
        save_data(load_data())
    await message.reply(f"✅ {username} אושר בהצלחה.")

@dp.message(F.text == "/list")
async def list_approved(message: Message):
    group = get_group(message.chat.id)
    approved = group.get("approved", [])
    if approved:
        await message.reply("✅ משתמשים מאושרים:
" + "
".join([f"• @{u}" for u in approved]))
    else:
        await message.reply("📭 אין משתמשים מאושרים כרגע.")

@dp.message()
async def handle_all(message: Message):
    text = message.text or ""
    chat_id = message.chat.id
    group = get_group(chat_id)
    sender = message.from_user

    if sender.username in group["admins"] or f"@{sender.username}" in group["admins"]:
        return
    if sender.username in group["approved"] or str(sender.id) in group["approved"]:
        return

    if re.search(r"(https?://|\.\w+|@\w+)", text):
        await message.delete()
        if group["admins"]:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=admin, url=f"https://t.me/{admin}")]
                for admin in group["admins"]
            ])
            await message.answer("🧻 נראה שפירסמת קישור בקבוצה. נא לפנות למנהל:", reply_markup=kb)
        else:
            await message.answer("⛔ ההודעה נמחקה. לא נמצאו מנהלים לאישור.")

async def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    await bot.set_webhook("https://telegram-bot-0269.onrender.com/webhook")
    setup_application(app, dp, bot=bot)
    return app

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
