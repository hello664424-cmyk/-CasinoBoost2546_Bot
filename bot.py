import os
import logging
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Dice
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration parameters via Environment Variables
TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@YourChannelUsername")

# In-memory database storing user balance and stats
users_db: Dict[int, Dict[str, Any]] = {}

def get_user_data(user_id: int) -> Dict[str, Any]:
    if user_id not in users_db:
        users_db[user_id] = {"balance": 1000}
    return users_db[user_id]

async def is_user_subscribed(bot, user_id: int) -> bool:
    """Check if the user is subscribed to the required channel for boost verification."""
    if not REQUIRED_CHANNEL or REQUIRED_CHANNEL == "@YourChannelUsername":
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return True

def main_keyboard() -> InlineKeyboardMarkup:
    """Returns the primary menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🎰 Spin Slots (100 pts)", callback_data="play_slots"),
            InlineKeyboardButton("🎲 Roll Dice (100 pts)", callback_data="play_dice"),
        ],
        [
            InlineKeyboardButton("🎯 Darts (100 pts)", callback_data="play_darts"),
            InlineKeyboardButton("💰 My Balance", callback_data="check_balance"),
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus (+500 pts)", callback_data="daily_bonus"),
            InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command and introduces channel subscription incentive."""
    user = update.effective_user
    get_user_data(user.id)
    
    text = (
        f"👋 Welcome to the **Casino & Mini-Game Bot**, {user.first_name}!\n\n"
        f"🎮 Play games, earn points, and climb the leaderboard!\n"
        f"📢 *Subscribe to our channel {REQUIRED_CHANNEL} to unlock games and bonus rewards!*"
    )
    
    await update.message.reply_text(
        text, 
        reply_markup=main_keyboard(), 
        parse_mode="Markdown"
    )

async def check_sub_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensures user is subscribed before allowing casino action."""
    query = update.callback_query
    user_id = query.from_user.id
    
    subscribed = await is_user_subscribed(context.bot, user_id)
    if not subscribed:
        sub_msg = (
            f"⚠️ **Access Restricted!**\n\n"
            f"You must join our official channel to play games and boost your points:\n"
            f"👉 {REQUIRED_CHANNEL}"
        )
        kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel Now", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton("✅ I Have Joined", callback_data="check_sub_again")]
        ])
        await query.message.reply_text(sub_msg, reply_markup=kbd, parse_mode="Markdown")
        return False
    return True

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    user_data = get_user_data(user_id)
    
    await query.answer()

    if data == "check_sub_again":
        if await is_user_subscribed(context.bot, user_id):
            await query.message.edit_text("✅ Subscription verified! You can now play.", reply_markup=main_keyboard())
        else:
            await query.answer("❌ You haven't joined the channel yet!", show_alert=True)
        return

    # Check subscription requirement before running games
    if data in ["play_slots", "play_dice", "play_darts"]:
        if not await check_sub_gate(update, context):
            return

    bet_amount = 100

    if data == "check_balance":
        await query.message.reply_text(
            f"💳 **Your Account Balance:** `{user_data['balance']}` Points",
            parse_mode="Markdown"
        )

    elif data == "daily_bonus":
        if user_data.get("daily_claimed"):
            await query.message.reply_text("⏳ You have already claimed your daily bonus today! Check back tomorrow.")
        else:
            user_data["balance"] += 500
            user_data["daily_claimed"] = True
            await query.message.reply_text("🎁 You claimed your daily bonus of **+500 Points**!", parse_mode="Markdown")

    elif data == "play_slots":
        if user_data["balance"] < bet_amount:
            await query.message.reply_text("❌ Insufficient balance to play! Claim your daily bonus.")
            return

        user_data["balance"] -= bet_amount
        msg = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=Dice.SLOT_MACHINE)
        value = msg.dice.value
        await asyncio.sleep(2.5)  # Pause for animation build-up

        # Telegram Slots mapping logic:
        # Values 1, 22, 43, 64 correspond to triple matches (Jackpots)
        if value in [1, 22, 43, 64]:
            reward = 1000
            user_data["balance"] += reward
            result = f"🎉 **JACKPOT!** You matched 3 symbols and won `{reward}` Points!"
        elif value in [2, 3, 4, 10, 15, 20, 25, 30, 40, 50, 60]:
            reward = 250
            user_data["balance"] += reward
            result = f"✨ **MINI WIN!** You won `{reward}` Points!"
        else:
            result = "💔 No match this time! Try again."

        await query.message.reply_text(
            f"{result}\n💰 Balance: `{user_data['balance']}` Points",
            parse_mode="Markdown"
        )

    elif data == "play_dice":
        if user_data["balance"] < bet_amount:
            await query.message.reply_text("❌ Insufficient balance to play!")
            return

        user_data["balance"] -= bet_amount
        msg = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=Dice.DICE)
        value = msg.dice.value
        await asyncio.sleep(2.5)

        if value >= 4:
            reward = bet_amount * 2
            user_data["balance"] += reward
            result = f"🎲 You rolled a **{value}**! You WIN `{reward}` Points!"
        else:
            result = f"🎲 You rolled a **{value}**! Better luck next time."

        await query.message.reply_text(
            f"{result}\n💰 Balance: `{user_data['balance']}` Points",
            parse_mode="Markdown"
        )

    elif data == "play_darts":
        if user_data["balance"] < bet_amount:
            await query.message.reply_text("❌ Insufficient balance to play!")
            return

        user_data["balance"] -= bet_amount
        msg = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=Dice.DARTS)
        value = msg.dice.value
        await asyncio.sleep(2.5)

        if value == 6:  # Bullseye
            reward = 500
            user_data["balance"] += reward
            result = f"🎯 **BULLSEYE!** You won `{reward}` Points!"
        elif value >= 4:
            reward = 150
            user_data["balance"] += reward
            result = f"🎯 Nice shot! You won `{reward}` Points!"
        else:
            result = "🎯 Missed the target!"

        await query.message.reply_text(
            f"{result}\n💰 Balance: `{user_data['balance']}` Points",
            parse_mode="Markdown"
        )

def main() -> None:
    """Start the Telegram bot service."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
