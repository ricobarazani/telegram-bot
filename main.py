import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
)

DATA_FILE = "data.json"

# ---------- Data Management ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ---------- Helpers ----------
def get_group_config(chat_id):
    if str(chat_id) not in data:
        data[str(chat_id)] = {
            "manager_username": None,
            "approved_users": [],
            "filters": {
                "links": True,
                "usernames": True,
                "telegram_links": True,
                "forwards": False
            }
        }
    return data[str(chat_id)]

def is_owner_or_admin(member):
    return member.status in ("creator", "administrator")

def contains_filtered_content(message, filters_config):
    if filters_config.get("forwards") and message.forward_date:
        return True
    if message.entities:
        for ent in message.entities:
            if ent.type in [MessageEntity.URL, MessageEntity.TEXT_LINK] and filters_config.get("links"):
                return True
            if ent.type == MessageEntity.MENTION and filters_config.get("usernames"):
                return True
    if filters_config.get("telegram_links") and message.text:
        if "t.me/" in message.text:
            return True
    return False

# ---------- Command Handlers ----------
async def set_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if user.status != "creator":
        return
    if not context.args:
        await update.message.reply_text("אנא ציין שם משתמש. לדוגמה: /setmanager @username")
        return
    username = context.args[0]
    get_group_config(chat_id)["manager_username"] = username
    save_data(data)
    await update.message.reply_text(f"המנהל הוגדר בהצלחה: {username}")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if user.status != "creator":
        return
    if not context.args:
        await update.message.reply_text("אנא ציין שם משתמש. לדוגמה: /approve @username")
        return
    username = context.args[0].lstrip("@")
    member = await context.bot.get_chat_member(chat_id, username)
    uid = member.user.id
    config = get_group_config(chat_id)
    if uid not in config["approved_users"]:
        config["approved_users"].append(uid)
        save_data(data)
    await update.message.reply_text(f"{username} אושר לפרסם.")

async def disapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if user.status != "creator":
        return
    if not context.args:
        await update.message.reply_text("אנא ציין שם משתמש. לדוגמה: /disapprove @username")
        return
    username = context.args[0].lstrip("@")
    member = await context.bot.get_chat_member(chat_id, username)
    uid = member.user.id
    config = get_group_config(chat_id)
    if uid in config["approved_users"]:
        config["approved_users"].remove(uid)
        save_data(data)
    await update.message.reply_text(f"{username} הוסר מרשימת המאושרים.")

async def approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    config = get_group_config(chat_id)
    if not config["approved_users"]:
        await update.message.reply_text("אין משתמשים מאושרים.")
        return
    mentions = []
    for uid in config["approved_users"]:
        try:
            user = await context.bot.get_chat_member(chat_id, uid)
            mentions.append(f"@{user.user.username}" if user.user.username else user.user.full_name)
        except:
            continue
    await update.message.reply_text("משתמשים מאושרים:\n" + "\n".join(mentions))

# ---------- Settings Menu ----------
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = await context.bot.get_chat_member(chat_id, update.effective_user.id)
    if user.status != "creator":
        return
    config = get_group_config(chat_id)
    filters_config = config["filters"]
    keyboard = [
        [InlineKeyboardButton(f"{'✅' if filters_config['links'] else '❌'} לינקים", callback_data=f"toggle_links")],
        [InlineKeyboardButton(f"{'✅' if filters_config['usernames'] else '❌'} שמות משתמש", callback_data=f"toggle_usernames")],
        [InlineKeyboardButton(f"{'✅' if filters_config['telegram_links'] else '❌'} קישורי טלגרם", callback_data=f"toggle_telegram_links")],
        [InlineKeyboardButton(f"{'✅' if filters_config['forwards'] else '❌'} הודעות מועברות", callback_data=f"toggle_forwards")],
        [InlineKeyboardButton("שמור", callback_data="save_settings")]
    ]
    await update.message.reply_text("בחר מה לחסום:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    config = get_group_config(chat_id)
    filters_config = config["filters"]
    if query.data.startswith("toggle_"):
        key = query.data.split("toggle_")[1]
        filters_config[key] = not filters_config[key]
        save_data(data)
        await settings(update, context)
    elif query.data == "save_settings":
        await query.edit_message_text("ההגדרות נשמרו.")

# ---------- Message Filter ----------
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat.id
    sender = await context.bot.get_chat_member(chat_id, message.from_user.id)
    config = get_group_config(chat_id)

    # Skip owners/admins/approved
    if is_owner_or_admin(sender) or message.from_user.id in config["approved_users"]:
        return

    if contains_filtered_content(message, config["filters"]):
        try:
            await message.delete()
        except:
            return
        manager = config.get("manager_username")
        if manager:
            keyboard = [[InlineKeyboardButton("פנייה למנהל", url=f"https://t.me/{manager.lstrip('@')}")]]
            await context.bot.send_message(
                chat_id=chat_id,
                text="פרסום מותר רק באישור. להסדרת פרסום אנא פנו למנהל.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

# ---------- Main ----------
if __name__ == '__main__':
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("setmanager", set_manager))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("disapprove", disapprove))
    app.add_handler(CommandHandler("approved", approved))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.FORWARDED, check_message))

    print("Bot is running...")
    app.run_polling()