import os
import json
import logging
import asyncio
import socket
import threading
from telegram import Update, ChatMember, Chat, MessageEntity
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          filters, ContextTypes, ChatMemberHandler)

# התחבולה לפתיחת פורט לרנדר

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

# יצירת קבוצות עם ברירת מחדל
if "groups" not in data:
    data["groups"] = {}
    save_data(data)

# ===== Command Handlers =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
👋 שלום! אני בוט ניהול קבוצות טלגרם.
✅ מזהה ומוחק קישורים והעברות לפי הגדרות הקבוצה.
✅ ניתן להגדיר מנהלי פרסום עם סינון ספציפי.

כדי לראות את הפקודות המלאות השתמש בפקודה /help
        """
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
📋 רשימת פקודות:
/start – התחלה והצגת מידע
/help – הצגת עזרה
/allow <username> – לאפשר למשתמש לפרסם (קבוצה בלבד)
/disallow <username> – לבטל אפשרות פרסום
/status – הצגת משתמשים מורשים
        """
    )

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != Chat.GROUP and update.effective_chat.type != Chat.SUPERGROUP:
        return await update.message.reply_text("פקודה זו זמינה רק בקבוצות.")

    if not context.args:
        return await update.message.reply_text("אנא ציין שם משתמש. לדוגמה: /allow username")

    username = context.args[0].lstrip("@")
    group_id = str(update.effective_chat.id)

    data.setdefault("groups", {}).setdefault(group_id, {}).setdefault("usernames", []).append(username)
    save_data(data)
    await update.message.reply_text(f"המשתמש @{username} נוסף לרשימת המורשים לפרסם.")

async def disallow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != Chat.GROUP and update.effective_chat.type != Chat.SUPERGROUP:
        return await update.message.reply_text("פקודה זו זמינה רק בקבוצות.")

    if not context.args:
        return await update.message.reply_text("אנא ציין שם משתמש. לדוגמה: /disallow username")

    username = context.args[0].lstrip("@")
    group_id = str(update.effective_chat.id)
    group_data = data.get("groups", {}).get(group_id, {})
    if "usernames" in group_data and username in group_data["usernames"]:
        group_data["usernames"].remove(username)
        save_data(data)
        await update.message.reply_text(f"המשתמש @{username} הוסר מרשימת המורשים לפרסם.")
    else:
        await update.message.reply_text(f"@{username} לא נמצא ברשימת המורשים.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = str(update.effective_chat.id)
    allowed = data.get("groups", {}).get(group_id, {}).get("usernames", [])
    if not allowed:
        await update.message.reply_text("לא הוגדרו משתמשים מורשים עדיין.")
    else:
        await update.message.reply_text("משתמשים מורשים:\n" + "\n".join(f"@{u}" for u in allowed))

# ===== מסנן הודעות =====
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    group_id = str(update.effective_chat.id)

    # קישורים והעברות
    has_link = any(entity.type in [MessageEntity.URL, MessageEntity.TEXT_LINK] for entity in message.entities or [])
    is_forward = message.forward_date is not None

    allowed_users = data.get("groups", {}).get(group_id, {}).get("usernames", [])
    if user.username in allowed_users:
        return

    if has_link or is_forward:
        try:
            await message.delete()
        except Exception:
            pass

# ===== Main =====

async def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("allow", allow))
    app.add_handler(CommandHandler("disallow", disallow))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_messages))

    print("Bot is running...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
