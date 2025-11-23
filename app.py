import os
import logging
import re
from flask import Flask, request
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# -------------------------------------------------------------------
# 1️⃣ Environment setup
# -------------------------------------------------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
SUPPORT_LINK = os.getenv("SUPPORT_LINK")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# -------------------------------------------------------------------
# 2️⃣ Logging configuration
# -------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_activity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# 3️⃣ Flask app initialization
# -------------------------------------------------------------------
app = Flask(__name__)
bot_app = Application.builder().token(BOT_TOKEN).build()

# -------------------------------------------------------------------
# 4️⃣ Helper: build main menu keyboard
# -------------------------------------------------------------------
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🛠️ Contact Admin", url=f"https://t.me/{ADMIN_USERNAME.strip('@')}"),
            InlineKeyboardButton("💬 Support Chat", url=SUPPORT_LINK)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# -------------------------------------------------------------------
# 5️⃣ Core Handlers
# -------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Respond to /start and /help commands."""
    user = update.effective_user
    logger.info(f"User {user.username} started interaction.")
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}! Need help or want to contact support?",
        reply_markup=get_main_keyboard()
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide help links."""
    await update.message.reply_text(
        "Need help or want to reach admin?",
        reply_markup=get_main_keyboard()
    )

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new users to the group."""
    for member in update.message.new_chat_members:
        logger.info(f"New member joined: {member.username or member.first_name}")
        await update.message.reply_text(
            f"👋 Welcome {member.first_name}! Need help or want to contact support?",
            reply_markup=get_main_keyboard()
        )

# -------------------------------------------------------------------
# 6️⃣ Spam Filter + Forwarding
# -------------------------------------------------------------------

BANNED_KEYWORDS = ["airdrop", "double your", "giveaway", "crypto bonus", "win btc", "claim now"]
URL_PATTERN = re.compile(r"https?://")

async def spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect and handle spam messages."""
    message = update.message
    text = message.text or ""
    user = message.from_user
    chat_id = message.chat_id

    # Check spam conditions
    is_spam = (
        any(word in text.lower() for word in BANNED_KEYWORDS)
        or URL_PATTERN.search(text)
    )

    if is_spam:
        logger.warning(f"⚠️ Spam detected from @{user.username}: {text}")
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Message removed. @{user.username}, links and promotions aren't allowed."
            )
        except Exception as e:
            logger.error(f"Failed to delete spam: {e}")

        # Forward to admin for review
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⚠️ Spam Alert from @{user.username or user.first_name}:\n{text}"
            )
        except Exception as e:
            logger.error(f"Failed to forward to admin: {e}")

# -------------------------------------------------------------------
# 7️⃣ Setup Handlers
# -------------------------------------------------------------------

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("help", help_handler))
bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), spam_filter))

# -------------------------------------------------------------------
# 8️⃣ Flask route to receive webhook updates
# -------------------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming updates from Telegram via webhook."""
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "🤖 CryptoSwap Bot is live!", 200

# -------------------------------------------------------------------
# 9️⃣ Start webhook on launch
# -------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    async def main():
        # Set webhook
        await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info("Webhook set successfully.")
        await bot_app.initialize()
        await bot_app.start()
        logger.info("Bot application started.")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

    asyncio.run(main())
