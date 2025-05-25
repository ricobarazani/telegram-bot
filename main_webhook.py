
import json
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.web import SimpleRequestHandler, setup_application

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

def update_group(chat_id, info):
    data = load_data()
    data[str(chat_id)] = info
    save_data(data)

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("🤖 הבוט פועל. השתמש בפקודות בקבוצה להגדרת מנהלים והרשאות פרסום.")

@router.message(Command("setadmin"))
async def setadmin_cmd(message: Message):
    try:
        username = message.text.split()[1]
        group = get_group(message.chat.id)
        if username not in group["admins"]:
            group["admins"].append(username)
            update_group(message.chat.id, group)
            await message.reply(f"✅ {username} נוסף לרשימת המנהלים.")
        else:
            await message.reply("ℹ️ המנהל כבר ברשימה.")
    except:
        await message.reply("❗ שימוש: /setadmin @username")

@router.message(Command("deleteadmin"))
async def deleteadmin_cmd(message: Message):
    try:
        username = message.text.split()[1]
        group = get_group(message.chat.id)
        if username in group["admins"]:
            group["admins"].remove(username)
            update_group(message.chat.id, group)
            await message.reply(f"🗑️ {username} הוסר מרשימת המנהלים.")
        else:
            await message.reply("❗ המנהל לא נמצא ברשימה.")
    except:
        await message.reply("❗ שימוש: /deleteadmin @username")

@router.message(Command("approve"))
async def approve_cmd(message: Message):
    group = get_group(message.chat.id)
    try:
        if message.reply_to_message:
            user_id = str(message.reply_to_message.from_user.id)
            if user_id not in group["approved"]:
                group["approved"].append(user_id)
                update_group(message.chat.id, group)
                await message.reply("✅ המשתמש אושר דרך תגובה.")
                return
        username = message.text.split()[1].lstrip("@")
        group["approved"].append(username)
        update_group(message.chat.id, group)
        await message.reply(f"✅ {username} אושר לפרסום.")
    except:
        await message.reply("❗ שימוש: /approve @username או בתגובה להודעה של המשתמש.")

@router.message(Command("remove"))
async def remove_cmd(message: Message):
    group = get_group(message.chat.id)
    try:
        username = message.text.split()[1].lstrip("@")
        if username in group["approved"]:
            group["approved"].remove(username)
            update_group(message.chat.id, group)
            await message.reply(f"🚫 {username} הוסר מהרשימה.")
            return
        user = await bot.get_chat_member(message.chat.id, username)
        user_id = str(user.user.id)
        if user_id in group["approved"]:
            group["approved"].remove(user_id)
            update_group(message.chat.id, group)
            await message.reply(f"🚫 {username} הוסר מהרשימה.")
        else:
            await message.reply("❗ המשתמש לא ברשימת המאושרים.")
    except:
        await message.reply("❗ שימוש: /remove @username")

@router.message(Command("list"))
async def list_cmd(message: Message):
    group = get_group(message.chat.id)
    if not group["approved"]:
        await message.reply("🔍 אין משתמשים מאושרים לפרסום.")
    else:
        lines = [f"- {uid}" for uid in group["approved"]]
        await message.reply("📋 משתמשים מאושרים:
" + "
".join(lines))

@router.message(Command("adminlist"))
async def adminlist_cmd(message: Message):
    group = get_group(message.chat.id)
    if not group["admins"]:
        await message.reply("🔍 לא הוגדרו מנהלים.")
    else:
        lines = [f"- {admin}" for admin in group["admins"]]
        await message.reply("👤 מנהלים מוגדרים:
" + "
".join(lines))

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
            await message.answer("🔗 כדי לפרסם בקבוצה, יש להסדיר זאת עם מנהל:", reply_markup=kb)
        else:
            await message.answer("🔇 ההודעה נמחקה. לא הוגדרו מנהלים לפנייה.")

# Webhook setup
app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
await bot.set_webhook("https://telegram-bot-0269.onrender.com/webhook")
setup_application(app, dp, bot=bot)
