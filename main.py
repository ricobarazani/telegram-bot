import os
import json
import re
import threading
import socket
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler,
    filters, CallbackQueryHandler, ChatMemberHandler
)

# ========= הגדרות בסיס =========
TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "data.json"

# ========= התחזות לפתיחת פורט =========
def fake_port():
    s = socket.socket()
    s.bind(("0.0.0.0", 10000))
    s.listen(1)
    while True:
        threading.Event().wait(10)

threading.Thread(target=fake_port, daemon=True).start()

# ========= ניהול קובץ נתונים =========
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ========= סינון קישורים =========
def extract_links(text):
    regex = r"(https?://\S+|t\.me/\S+|@\w+)"
    return re.findall(regex, text)

# ========= הגדרות ברירת מחדל =========
def ensure_group_config(data, chat_id):
    if str(chat_id) not in data:
        data[str(chat_id)] = {
            "owner": None,
            "authorized": [],
            "filters_config": {
                "web_links": True,
                "telegram_links": True,
                "usernames": True,
                "forwards": True
            },
            "ad_manager": None
        }
        save_data(data)

# ========= ניהול הרשאות =========
def is_owner(chat_id, user_id):
    data = load_data()
    ensure_group_config(data, chat_id)
    return data[str(chat_id)]["owner"] == user_id

def is_authorized(chat_id, user_id):
    data = load_data()
    ensure_group_config(data, chat_id)
    return user_id in data[str(chat_id)]["authorized"]

# ========= Command Handlers =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 שלום!\n\n"
        "אני בוט ניהול פרסומים לקבוצות טלגרם.\n\n"
        "✅ הודעות לא מאושרות לא יכילו קישורים ויימחקו אוטומטית.\n"
        "✅ ניתן לאשר משתמשים או לקבוע סינון מותאם אישית.\n\n"
        "השתמש בפקודת /help לצפייה ברשימת הפקודות."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/setowner - קביעת בעלים (רק בטווח פרטי)\n"
        "/setmanager - קביעת מנהל לפניות\n"
        "/approve - אישור משתמש\n"
        "/list - רשימת מאושרים\n"
        "/settings - קביעת סינון\n"
    )

async def setowner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    data = load_data()
    chat_id = context.args[0] if context.args else None
    if chat_id:
        data.setdefault(str(chat_id), {})
        data[str(chat_id)]["owner"] = update.message.from_user.id
        save_data(data)
        await update.message.reply_text("הוגדרת כבעלים של הקבוצה.")

async def setmanager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not is_owner(chat_id, user_id):
        return
    if not context.args:
        await update.message.reply_text("אנא תייג את המנהל / שלח את מזהה המשתמש.")
        return
    target = int(context.args[0].lstrip("@"))
    data = load_data()
    data[str(chat_id)]["ad_manager"] = target
    save_data(data)
    await update.message.reply_text("המנהל הוגדר בהצלחה.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not is_owner(chat_id, user_id):
        return
    if not context.args:
        await update.message.reply_text("יש לציין מזהה משתמש או לתייג.")
        return
    target = int(context.args[0].lstrip("@"))
    data = load_data()
    data[str(chat_id)]["authorized"].append(target)
    save_data(data)
    await update.message.reply_text("המשתמש אושר.")

async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = load_data()
    approved = data.get(str(chat_id), {}).get("authorized", [])
    if not approved:
        await update.message.reply_text("אין משתמשים מאושרים.")
        return
    await update.message.reply_text("מאושרים:\n" + '\n'.join(map(str, approved)))

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not is_owner(chat_id, user_id):
        return
    data = load_data()
    config = data[str(chat_id)]["filters_config"]
    keyboard = [
        [InlineKeyboardButton(f"קישורים חיצוניים {'✅' if config['web_links'] else '❌'}", callback_data='toggle_web')],
        [InlineKeyboardButton(f"לינקים טלגרם {'✅' if config['telegram_links'] else '❌'}", callback_data='toggle_telegram')],
        [InlineKeyboardButton(f"שמות משתמשים @ {'✅' if config['usernames'] else '❌'}", callback_data='toggle_usernames')],
        [InlineKeyboardButton(f"הודעות מועברות {'✅' if config['forwards'] else '❌'}", callback_data='toggle_forwards')]
    ]
    await update.message.reply_text("בחר מה למחוק אוטומטית:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    if not is_owner(chat_id, user_id):
        return
    data = load_data()
    key_map = {
        'toggle_web': 'web_links',
        'toggle_telegram': 'telegram_links',
        'toggle_usernames': 'usernames',
        'toggle_forwards': 'forwards'
    }
    key = key_map.get(query.data)
    if key:
        data[str(chat_id)]["filters_config"][key] ^= True
        save_data(data)
        await settings(update, context)

# ========= סינון הודעות =========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat.id
    user_id = message.from_user.id
    data = load_data()
    ensure_group_config(data, chat_id)

    if is_authorized(chat_id, user_id):
        return

    text = message.text or message.caption or ""
    links = extract_links(text)
    should_delete = False

    filters_config = data[str(chat_id)]["filters_config"]
    for link in links:
        if filters_config["web_links"] and link.startswith("http"):
            should_delete = True
        elif filters_config["telegram_links"] and "t.me/" in link:
            should_delete = True
        elif filters_config["usernames"] and link.startswith("@"):
            should_delete = True

    if message.forward_from_chat and filters_config["forwards"]:
        should_delete = True

    if should_delete:
        await message.delete()
        manager_id = data[str(chat_id)].get("ad_manager")
        if manager_id:
            keyboard = [[InlineKeyboardButton("פנייה למנהל", url=f"https://t.me/{manager_id}")]]
            await message.chat.send_message(
                "כדי לפרסם בקבוצה – יש להסדיר זאת עם מנהל הפרסומים.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

# ========= Bot Startup =========
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setowner", setowner))
    app.add_handler(CommandHandler("setmanager", setmanager))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("list", list_approved))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.FORWARDED, handle_message))

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
