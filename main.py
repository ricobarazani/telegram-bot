import os
import json
import asyncio
import logging
import socket
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, ChatMemberUpdated
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ChatMemberHandler
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "data.json"

# ---------------------- Fake Port Binding ----------------------
def fake_port():
    s = socket.socket()
    s.bind(("0.0.0.0", 10000))
    s.listen(1)
    while True:
        time.sleep(10)

threading.Thread(target=fake_port, daemon=True).start()

# ---------------------- Logging ----------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------- Data Handling ----------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

data = load_data()

# ---------------------- Helper Functions ----------------------
def get_chat_config(chat_id):
    return data.setdefault(str(chat_id), {
        "allowed_users": [],
        "link_types": {
            "telegram": True,
            "web": True,
            "usernames": True
        },
        "ad_manager_id": None
    })

def is_user_admin(chat_member: ChatMember):
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

async def is_admin(user_id, chat_id, context):
    member = await context.bot.get_chat_member(chat_id, user_id)
    return is_user_admin(member)

# ---------------------- Command Handlers ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 שלום!\n\n"
        "אני בוט ניהול פרסומים לקבוצות טלגרם.\n\n"
        "✅ הודעות לא מאושרות לא יכילו קישורים ויימחקו.\n"
        "✅ ניתן להגדיר מנהל להסדרת פרסומים.\n\n"
        "השתמש בפקודת /help כדי לראות את רשימת הפקודות."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 פקודות זמינות:\n"
        "/set_ad_manager <@username> - הגדרת מנהל פרסומים.\n"
        "/approve <@username> - אישור משתמש לפרסום.\n"
        "/approved - הצגת רשימת מאושרים.\n"
        "/settings - קביעת סוגי קישורים למחיקה."
    )

async def set_ad_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id, update.effective_chat.id, context):
        return

    if not context.args:
        await update.message.reply_text("🛠 נא לציין שם משתמש.")
        return

    username = context.args[0].lstrip("@")
    config = get_chat_config(update.effective_chat.id)
    config['ad_manager_id'] = username
    save_data(data)
    await update.message.reply_text(f"👤 {username} הוגדר כמנהל להסדרת פרסומים.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id, update.effective_chat.id, context):
        return

    if not context.args:
        await update.message.reply_text("❗ נא לציין שם משתמש לאישור.")
        return

    username = context.args[0].lstrip("@")
    config = get_chat_config(update.effective_chat.id)
    if username not in config['allowed_users']:
        config['allowed_users'].append(username)
        save_data(data)
        await update.message.reply_text(f"✅ {username} אושר לפרסם קישורים.")
    else:
        await update.message.reply_text(f"ℹ️ {username} כבר מאושר.")

async def approved_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = get_chat_config(update.effective_chat.id)
    users = config['allowed_users']
    if not users:
        await update.message.reply_text("📭 אין משתמשים מאושרים.")
    else:
        await update.message.reply_text("📋 משתמשים מאושרים:\n" + "\n".join(f"@{u}" for u in users))

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id, update.effective_chat.id, context):
        return

    config = get_chat_config(update.effective_chat.id)
    buttons = [
        [InlineKeyboardButton(f"📎 טלגרם: {'✅' if config['link_types']['telegram'] else '❌'}", callback_data='toggle_telegram')],
        [InlineKeyboardButton(f"🌐 אתרים: {'✅' if config['link_types']['web'] else '❌'}", callback_data='toggle_web')],
        [InlineKeyboardButton(f"👤 יוזרים: {'✅' if config['link_types']['usernames'] else '❌'}", callback_data='toggle_usernames')]
    ]
    await update.message.reply_text("⚙️ הגדר אילו קישורים למחוק:", reply_markup=InlineKeyboardMarkup(buttons))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    config = get_chat_config(query.message.chat.id)
    if query.data.startswith("toggle_"):
        key = query.data.replace("toggle_", "")
        config['link_types'][key] = not config['link_types'][key]
        save_data(data)
        await settings(update, context)

# ---------------------- Message Filtering ----------------------
def contains_link(text, config):
    import re
    if config['link_types'].get("telegram"):
        if re.search(r"t\.me/|telegram\.me/", text):
            return True
    if config['link_types'].get("web"):
        if re.search(r"https?://", text):
            return True
    if config['link_types'].get("usernames"):
        if re.search(r"@\w+", text):
            return True
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = str(message.chat.id)
    user = message.from_user

    config = get_chat_config(chat_id)

    if await is_admin(user.id, chat_id, context):
        return

    if contains_link(message.text or "", config):
        if user.username not in config['allowed_users']:
            await message.delete()
            if config['ad_manager_id']:
                button = InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton("📩 להסדרת פרסום", url=f"https://t.me/{config['ad_manager_id']}")
                )
                await message.chat.send_message(
                    f"@{user.username} הפרסום נמחק. להסדרת פרסום פנה למנהל.",
                    reply_markup=button
                )

# ---------------------- Main ----------------------
async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("set_ad_manager", set_ad_manager))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("approved", approved_list))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    await application.initialize()
    await application.start()
    await asyncio.Event().wait()

if __name__ == '__main__':
    import time
    asyncio.run(main())
