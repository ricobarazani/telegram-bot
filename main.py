import threading
import time
import socket

# --- Render port trick ---
def fake_port():
    s = socket.socket()
    s.bind(("0.0.0.0", 10000))
    s.listen(1)
    while True:
        time.sleep(10)

threading.Thread(target=fake_port, daemon=True).start()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

with open(DATA_FILE, "r") as f:
    data = json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ========== Command Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📥 קיבלת פקודת /start")
    await update.message.reply_text(
        """
👋 שלום!
אני בוט ניהול פרסומים לקבוצות טלגרם ✅

📌 אני מזהה וחוסם קישורים והודעות לא מאושרות לפי הגדרות הבעלים.
📌 ניתן להגדיר מנהל להסדרת פרסומים, ולהתאים סינון ספציפי.

ℹ️ כדי לראות את רשימת הפקודות המלאה /help השתמש בפקודה
        """
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📥 קיבלת פקודת /help")
    await update.message.reply_text("""
🛠 רשימת פקודות:

/settings – הגדרת סוגי קישורים שיימחקו
/setmanager – הגדרת מנהל אחראי להסדרת פרסום
/approve – אישור משתמש מסוים לפרסום
/approved – רשימת המשתמשים המאושרים

(רק בעלים יכול להפעיל פקודות אלו)
    """)

# ========== Utility Functions ==========
def get_chat_config(chat_id):
    return data.setdefault(str(chat_id), {
        "approved_users": [],
        "manager": None,
        "filters": {
            "links": True,
            "usernames": True,
            "forwards": True
        }
    })

# ========== Command Logic ==========
async def set_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    if chat_member.status != "creator":
        return

    if not context.args:
        await update.message.reply_text("יש לציין שם משתמש של המנהל")
        return

    username = context.args[0].lstrip("@")
    config = get_chat_config(chat_id)
    config["manager"] = username
    save_data()
    await update.message.reply_text(f"@{username} הוגדר כמנהל להסדרת פרסומים")

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    if chat_member.status != "creator":
        return

    if not context.args:
        await update.message.reply_text("יש לתייג או לציין את המשתמש לאישור")
        return

    user = context.args[0].lstrip("@")
    config = get_chat_config(chat_id)
    if user not in config["approved_users"]:
        config["approved_users"].append(user)
    save_data()
    await update.message.reply_text(f"@{user} נוסף לרשימת המאושרים")

async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = get_chat_config(update.effective_chat.id)
    approved = config["approved_users"]
    if approved:
        await update.message.reply_text("מאושרים לפרסום:\n" + "\n".join(f"@{u}" for u in approved))
    else:
        await update.message.reply_text("אין משתמשים מאושרים כרגע.")

# ========== Settings Menu ==========
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    if chat_member.status != "creator":
        return

    config = get_chat_config(chat_id)
    buttons = [
        [InlineKeyboardButton(f"קישורים {'✅' if config['filters']['links'] else '❌'}", callback_data="toggle_links")],
        [InlineKeyboardButton(f"שמות משתמש {'✅' if config['filters']['usernames'] else '❌'}", callback_data="toggle_usernames")],
        [InlineKeyboardButton(f"הודעות מועברות {'✅' if config['filters']['forwards'] else '❌'}", callback_data="toggle_forwards")]
    ]
    await update.message.reply_text("בחר אילו תכנים למחוק אוטומטית:", reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    config = get_chat_config(chat_id)

    if query.data.startswith("toggle_"):
        field = query.data.split("_")[1]
        config["filters"][field] = not config["filters"][field]
        save_data()
        await settings(update, context)

# ========== Message Filter ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat_id = message.chat.id
    user = message.from_user
    config = get_chat_config(chat_id)

    is_owner = (await context.bot.get_chat_member(chat_id, user.id)).status == "creator"
    is_admin = (await context.bot.get_chat_member(chat_id, user.id)).status in ["administrator", "creator"]

    if is_admin:
        return

    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    should_delete = False

    if config["filters"].get("links"):
        if any(e.type in ["url", "text_link"] for e in entities):
            should_delete = True
    if config["filters"].get("usernames") and "@" in text:
        should_delete = True
    if config["filters"].get("forwards") and message.forward_from:
        should_delete = True

    if not should_delete:
        return

    username = user.username or str(user.id)
    if username in config["approved_users"]:
        return

    try:
        await message.delete()
    except:
        return

    manager = config.get("manager")
    if manager:
        button = InlineKeyboardMarkup.from_button(InlineKeyboardButton("לפנייה למנהל", url=f"https://t.me/{manager}"))
        await message.chat.send_message("🔒 כדי לפרסם בקבוצה יש להסדיר זאת עם מנהל הקבוצה.", reply_markup=button)

# ========== Main ==========
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setmanager", set_manager))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("approved", list_approved))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("🤖 הבוט פעיל")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
