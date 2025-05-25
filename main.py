import os
import json
import logging
import asyncio
import socket
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# התחזות לפתיחת פורט לרנדר

def fake_port():
    s = socket.socket()
    s.bind(("0.0.0.0", 10000))
    s.listen(1)
    while True:
        threading.Event().wait(10)

threading.Thread(target=fake_port, daemon=True).start()

# קובץ נתונים
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data = load_data()

# יצירת קונפיג לקבוצה

def get_chat_config(chat_id):
    return data.setdefault(str(chat_id), {
        "approved_users": [],
        "manager": None,
        "filters": {
            "links": True,
            "usernames": True,
            "forwards": True
        },
        "owner": None
    })

# פקודות
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
👋 שלום!
אני בוט ניהול פרסומים לקבוצות טלגרם ✅

📌 אני מזהה וחוסם קישורים והודעות לא מאושרות לפי הגדרות הבעלים.
📌 ניתן להגדיר מנהל להסדרת פרסומים, ולהתאים סינון ספציפי.

ℹ️ כדי לראות את רשימת הפקודות המלאה /help
        """
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🛠 רשימת פקודות:
/start – פתיחה
/help – עזרה
/setowner – הגדרת בעלים (יש לעשות בפרטי)
/setmanager – הגדרת מנהל אחראי להסדרת פרסום
/approve – אישור משתמש מסוים לפרסום
/list – רשימת המשתמשים המאושרים
/settings – קביעת סוגי קישורים שיימחקו
    """)

async def setowner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    if not context.args:
        await update.message.reply_text("נא לציין chat_id של הקבוצה.")
        return
    chat_id = context.args[0]
    data.setdefault(str(chat_id), {})
    data[str(chat_id)]["owner"] = update.effective_user.id
    save_data(data)
    await update.message.reply_text("הוגדרת כבעלים של הקבוצה.")

async def set_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    config = get_chat_config(chat_id)
    if config.get("owner") != user_id:
        return
    if not context.args:
        await update.message.reply_text("יש לציין שם משתמש של המנהל (@username)")
        return
    config["manager"] = context.args[0].lstrip("@")
    save_data(data)
    await update.message.reply_text(f"@{config['manager']} הוגדר כמנהל פרסומים.")

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    config = get_chat_config(chat_id)
    if config.get("owner") != user_id:
        return
    if not context.args:
        await update.message.reply_text("יש לציין שם משתמש (ללא @)")
        return
    username = context.args[0].lstrip("@")
    if username not in config["approved_users"]:
        config["approved_users"].append(username)
        save_data(data)
    await update.message.reply_text(f"@{username} נוסף לרשימת המאושרים.")

async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = get_chat_config(str(update.effective_chat.id))
    approved = config.get("approved_users", [])
    if approved:
        await update.message.reply_text("📋 מאושרים:\n" + "\n".join(f"@{u}" for u in approved))
    else:
        await update.message.reply_text("אין מאושרים.")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    config = get_chat_config(chat_id)
    if config.get("owner") != user_id:
        return
    buttons = [
        [InlineKeyboardButton(f"קישורים {'✅' if config['filters']['links'] else '❌'}", callback_data="toggle_links")],
        [InlineKeyboardButton(f"שמות משתמשים {'✅' if config['filters']['usernames'] else '❌'}", callback_data="toggle_usernames")],
        [InlineKeyboardButton(f"העברות {'✅' if config['filters']['forwards'] else '❌'}", callback_data="toggle_forwards")]
    ]
    await update.message.reply_text("בחר אילו תכנים למחוק:", reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)
    config = get_chat_config(chat_id)
    field = query.data.replace("toggle_", "")
    config["filters"][field] = not config["filters"][field]
    save_data(data)
    await settings(update, context)

# סינון הודעות
async def filter_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    chat_id = str(message.chat.id)
    config = get_chat_config(chat_id)
    user = message.from_user
    username = user.username or str(user.id)

    if username in config["approved_users"]:
        return

    should_delete = False
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []

    if config["filters"].get("links"):
        if any(e.type in ["url", "text_link"] for e in entities):
            should_delete = True
    if config["filters"].get("usernames") and "@" in text:
        should_delete = True
    if config["filters"].get("forwards") and message.forward_from:
        should_delete = True

    if should_delete:
        try:
            await message.delete()
        except:
            pass
        manager = config.get("manager")
        if manager:
            btn = InlineKeyboardMarkup.from_button(InlineKeyboardButton("לפנייה למנהל", url=f"https://t.me/{manager}"))
            await message.chat.send_message("🔒 כדי לפרסם בקבוצה יש להסדיר זאת עם מנהל.", reply_markup=btn)

# הרצה
async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setowner", setowner))
    app.add_handler(CommandHandler("setmanager", set_manager))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("list", list_approved))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, filter_message))

    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
