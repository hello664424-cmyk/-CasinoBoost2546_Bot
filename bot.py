import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Fetch bot token from environment variable
TOKEN = os.getenv("BOT_TOKEN")

# In-memory balance tracker (Note: Use a database like SQLite or PostgreSQL for production)
user_balances = {}

def get_balance(user_id: int) -> int:
    if user_id not in user_balances:
        user_balances[user_id] = 1000  # Starting balance
    return user_balances[user_id]

def update_balance(user_id: int, amount: int):
    user_balances[user_id] = get_balance(user_id) + amount

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends start message and game selection menu."""
    user = update.effective_user
    balance = get_balance(user.id)
    
    keyboard = [
        [
            InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
            InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
        ],
        [
            InlineKeyboardButton("🎯 Darts", callback_data="game_darts"),
            InlineKeyboardButton("🏀 Basketball", callback_data="game_basketball"),
        ],
        [
            InlineKeyboardButton("⚽ Football", callback_data="game_football"),
            InlineKeyboardButton("🎳 Bowling", callback_data="game_bowling"),
        ],
        [
            InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"),
            InlineKeyboardButton("🎁 Daily Bonus (+100)", callback_data="daily_bonus"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"👋 Welcome to the Telegram Casino Bot, {user.first_name}!\n\n"
        f"💳 Your Balance: **{balance} Coins**\n\n"
        "Select a game below to place a 10-coin bet and play:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button callbacks for games and account actions."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    bet_amount = 10

    if data == "check_balance":
        balance = get_balance(user_id)
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(
            f"💳 Current Balance: **{balance} Coins**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data == "daily_bonus":
        update_balance(user_id, 100)
        new_balance = get_balance(user_id)
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(
            f"🎉 You claimed your daily bonus of 100 coins!\n💳 New Balance: **{new_balance} Coins**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data == "main_menu":
        await start(update, context)
        return

    # Handle Games
    game_emoji_map = {
        "game_slots": ("🎰", "slot_machine"),
        "game_dice": ("🎲", "dice"),
        "game_darts": ("🎯", "darts"),
        "game_basketball": ("🏀", "basketball"),
        "game_football": ("⚽", "football"),
        "game_bowling": ("🎳", "bowling"),
    }

    if data in game_emoji_map:
        current_balance = get_balance(user_id)
        if current_balance < bet_amount:
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
            await query.edit_message_text(
                "❌ You don't have enough coins to play! (Required: 10 Coins)",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Deduct bet amount
        update_balance(user_id, -bet_amount)
        emoji_symbol, emoji_type = game_emoji_map[data]

        # Send native animated dice message
        msg = await context.bot.send_dice(
            chat_id=query.message.chat_id,
            emoji=emoji_symbol,
        )
        
        value = msg.dice.value
        payout = 0

        # Calculate winnings based on native dice value outcomes
        if emoji_type == "slot_machine":
            # Values: 1 (BAR BAR BAR), 64 (777), 22, 43, etc.
            if value == 64:  # Jackpot 777
                payout = 250
            elif value in [1, 22, 43]:  # Three matching symbols
                payout = 50
        elif emoji_type == "dice":
            if value >= 4:
                payout = bet_amount * 2
        elif emoji_type in ["darts", "basketball"]:
            if value in [5, 6]:  # Bullseye / Perfect basket
                payout = bet_amount * 2
        elif emoji_type == "football":
            if value in [3, 4, 5]:  # Goal
                payout = bet_amount * 2
        elif emoji_type == "bowling":
            if value == 6:  # Strike
                payout = bet_amount * 3

        if payout > 0:
            update_balance(user_id, payout)
            result_text = f"🎉 **You Won {payout} Coins!**"
        else:
            result_text = "❌ **You Lost! Better luck next time.**"

        new_balance = get_balance(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Play Again", callback_data=data),
                InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"),
            ]
        ]
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Outcome Value: **{value}**\n{result_text}\n\n💳 New Balance: **{new_balance} Coins**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is missing!")
        
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))

    logger.info("Starting bot deployment...")
    application.run_polling()

if __name__ == "__main__":
    main()
