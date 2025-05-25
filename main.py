import os
import json
import re
import socket
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat, MessageEntity
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

# Load config from JSON
CONFIG_FILE = "data.json"
def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"admins": [], "filters": {"usernames": True, "t.me": True, "invite": True, "forwards": True}}, f)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_config()
BOT_OWNER = int(os.getenv("BOT_OWNER_ID", "0"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

# -------------- Utility Functions --------------

def is_admin(user_id):
    return user_id == BOT_OWNER or user_id in config.get("admins", [])

def extract_user_id(update: Update):
    if update.message:
        return update.message.from_user.id
    if update.callback_query:
        return update.callback_query.from_user.id
    return None

# -------------- Link & Forward Filter --------------

def contains_prohibited_links(text):
    if config["filters"].get("usernames") and re.search(r"@\w+", text):
        return True
    if config["filters"].get("t.me") and "t.me" in text:
        return True
    if config["filters"].get("invite") and re.search(r"t\.me/joinchat/|t\.me/\+[A-Za-z0-9_-]+", text):
        return True
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text or ""
    if contains_prohibited_links(text):
        await update.message.delete()
        if any(is_admin(uid) for uid in config.get("admins", [])):
            btn = InlineKeyboardButton("אזהרה ⚠️", callback_data="warn")
            markup = InlineKeyboardMarkup([[btn]])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"הודעה נמחקה עקב קישור אסור. המשתמש <a href=\"tg://user?id={user_id}\">הזה</a> הפר את הכללים.", parse_mode='HTML', reply_markup=markup)

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config["filters"].get("forwards"):
        await update.message.delete()
        if any(is_admin(uid) for uid in config.get("admins", [])):
            btn = InlineKeyboardButton("אזהרה ⚠️", callback_data="warn")
            markup = InlineKeyboardMarkup([[btn]])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"הודעה נמחקה עקב העברה מקבוצה או ערוץ.", reply_markup=markup)

# -------------- Admin Commands --------------

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = extract_user_id(update)
    if not is_admin(user_id):
        return
    if not context.args:
        await update.message.reply_text("יש לציין מזהה משתמש.")
        return
    new_admin = int(context.args[0])
    if new_admin not in config["admins"]:
        config["admins"].append(new_admin)
        save_config(config)
        await update.message.reply_text(f"המשתמש {new_admin} נוסף למנהלים.")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = extract_user_id(update)
    if not is_admin(user_id):
        return
    admins = config.get("admins", [])
    text = "\n".join([f"👤 {uid}" for uid in admins]) or "אין מנהלים מוגדרים."
    await update.message.reply_text(f"👮 רשימת מנהלים:\n{text}")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = extract_user_id(update)
    if not is_admin(user_id):
        return
    buttons = [
        [InlineKeyboardButton(f"{'✅' if config['filters'][k] else '❌'} {label}", callback_data=f"toggle:{k}")]
        for k, label in zip(["usernames", "t.me", "invite", "forwards"], ["שמות משתמש", "t.me", "הזמנות", "העברות"])
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("בחר אילו תכנים לחסום:", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("toggle:"):
        key = query.data.split(":")[1]
        config["filters"][key] = not config["filters"].get(key, False)
        save_config(config)
        await settings(update, context)

# -------------- Start & Help --------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
👋 שלום!
אני בוט ניהול פשוט לקבוצות טלגרם.

✅ מזהה ומוחק קישורים והעברות לפי ההגדרות שקבעת.
✅ ניתן להגדיר מנהלים ולהפעיל סינון ספציפי.

ℹ️ השתמש בפקודת /help כדי לראות את כל האפשרויות.
        """
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
📋 פקודות זמינות:
/start - הצגת מידע על הבוט
/help - רשימת פקודות
/addadmin [user_id] - הוספת מנהל (רק לבעלים)
/admins - צפייה במנהלים
/settings - קביעת סינון קישורים והעברות
        """
    )

# -------------- Main --------------

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.FORWARDED, handle_forward))

    # התחבולה - פתיחת פורט דמה למניעת שגיאה ב-Render
    def fake_port():
        s = socket.socket()
        s.bind(("0.0.0.0", 10000))
        s.listen(1)
        while True:
            time.sleep(10)

    threading.Thread(target=fake_port, daemon=True).start()

    app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
