import os
import json
import logging
import asyncio
import socket
import threading
from telegram import Update, ChatMember, ChatMemberUpdated, MessageEntity
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ChatMemberHandler
)

# התחבולה לפתיחת פורט ברנדר

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

# יצירת רשימת קישורים לקבוצות
GROUP_LINKS = [
    "t.me/",
    "https://t.me/",
    "joinchat/",
    "telegram.me/",
    "https://telegram.me/"
]

# ========== Command Handlers ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
👋 שלום!
אני בוט ניהול פרסומים לקבוצת טלגרם ✅.
✅ מזהה ומוחק קישורים והודעות לא מאושרות לפי הגדרות המנהל.
✅ ניתן להגדיר מנהל ולהתאים סינון ספציפי.

כדי לראות את הפקודות המלאות /help השתמש בפקודה
        """
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
📌 פקודות ניהול זמינות:

/allow [user_id] - הוספת משתמש מורשה
/disallow [user_id] - הסרת משתמש מורשה
/list_allowed - הצגת משתמשים מורשים

/setadmin [user_id] - הגדרת מנהל
/myid - הצגת מזהה המשתמש שלך
        """
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"המזהה שלך הוא: {update.effective_user.id}")

# ========== Filter & Message Logic ==========

def extract_user_id(text: str) -> str:
    return text.split()[1] if len(text.split()) > 1 else None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = str(message.from_user.id)
    text = message.text or ""

    if any(link in text for link in GROUP_LINKS):
        if user_id not in data.get("allowed_users", []):
            await message.delete()
            return

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = extract_user_id(update.message.text)
    if not user_id:
        await update.message.reply_text("יש לציין מזהה משתמש.")
        return
    data.setdefault("allowed_users", []).append(user_id)
    save_data(data)
    await update.message.reply_text(f"משתמש {user_id} אושר.")

async def disallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = extract_user_id(update.message.text)
    if not user_id:
        await update.message.reply_text("יש לציין מזהה משתמש.")
        return
    if user_id in data.get("allowed_users", []):
        data["allowed_users"].remove(user_id)
        save_data(data)
        await update.message.reply_text(f"משתמש {user_id} הוסר.")
    else:
        await update.message.reply_text(f"המשתמש {user_id} לא נמצא ברשימה.")

async def list_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed = data.get("allowed_users", [])
    if not allowed:
        await update.message.reply_text("אין משתמשים מאושרים.")
    else:
        await update.message.reply_text("משתמשים מאושרים:\n" + "\n".join(allowed))

async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = extract_user_id(update.message.text)
    if not user_id:
        await update.message.reply_text("יש לציין מזהה משתמש.")
        return
    data["admin"] = user_id
    save_data(data)
    await update.message.reply_text(f"משתמש {user_id} הוגדר כמנהל.")

# ========== Bot Setup ==========

token = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(token).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("myid", myid))
app.add_handler(CommandHandler("allow", allow))
app.add_handler(CommandHandler("disallow", disallow))
app.add_handler(CommandHandler("list_allowed", list_allowed))
app.add_handler(CommandHandler("setadmin", set_admin))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# פתרון לבעיית הלולאה ברנדר
async def main():
    await app.initialize()
    await app.start()
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
