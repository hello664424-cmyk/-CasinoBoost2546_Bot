import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Virtual user balance store
user_balances = {}

def get_balance(user_id: int) -> int:
    return user_balances.get(user_id, 1000)  # Default 1000 credits to test

def update_balance(user_id: int, amount: int):
    user_balances[user_id] = get_balance(user_id) + amount

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    balance = get_balance(user.id)
    
    keyboard = [
        [
            InlineKeyboardButton("🎯 Coinflip (2x)", callback_data="game_coinflip"),
            InlineKeyboardButton("🎲 Dice Roll", callback_data="game_dice"),
        ],
        [
            InlineKeyboardButton("🎰 Slot Machine", callback_data="game_slots"),
            InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"),
        ],
        [
            InlineKeyboardButton("🚀 Claim Daily Bonus", callback_data="daily_bonus"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"👋 Welcome to the Casino Bot, {user.first_name}!\n\n"
        f"💳 Your Balance: *{balance} Credits*\n\n"
        "Choose a game or claim your daily bonus below:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "menu_main":
        await start(update, context)
        return

    if data == "check_balance":
        balance = get_balance(user_id)
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]]
        await query.edit_message_text(
            f"💰 Your Current Balance: *{balance} Credits*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data == "daily_bonus":
        update_balance(user_id, 250)
        new_balance = get_balance(user_id)
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]]
        await query.edit_message_text(
            f"🎉 You claimed *250 FREE Credits*!\n💳 New Balance: *{new_balance} Credits*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    # Coinflip Game Flow
    if data == "game_coinflip":
        keyboard = [
            [
                InlineKeyboardButton("Heads (100)", callback_data="play_cf_heads"),
                InlineKeyboardButton("Tails (100)", callback_data="play_cf_tails"),
            ],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "🎯 *Coinflip Game*\nBet: 100 Credits\nChoose Heads or Tails:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data in ["play_cf_heads", "play_cf_tails"]:
        bet = 100
        balance = get_balance(user_id)
        if balance < bet:
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]]
            await query.edit_message_text(
                "❌ Insufficient balance! Claim daily bonus or check balance.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        user_choice = "heads" if "heads" in data else "tails"
        outcome = random.choice(["heads", "tails"])
        
        if user_choice == outcome:
            update_balance(user_id, bet)
            res_text = f"🎉 The coin landed on *{outcome.upper()}*! You WON {bet} credits!"
        else:
            update_balance(user_id, -bet)
            res_text = f"💥 The coin landed on *{outcome.upper()}*! You lost {bet} credits."

        keyboard = [
            [InlineKeyboardButton("Play Again", callback_data="game_coinflip")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            f"{res_text}\n\n💳 New Balance: *{get_balance(user_id)} Credits*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    # Slot Machine Game Flow
    if data == "game_slots":
        bet = 50
        balance = get_balance(user_id)
        if balance < bet:
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]]
            await query.edit_message_text(
                "❌ Insufficient balance to spin slots (50 credits required).",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        symbols = ["🍋", "🍒", "🔔", "💎", "7️⃣"]
        reel1, reel2, reel3 = random.choice(symbols), random.choice(symbols), random.choice(symbols)

        if reel1 == reel2 == reel3:
            win_amount = 500
            update_balance(user_id, win_amount)
            msg = f"🎰 [{reel1} | {reel2} | {reel3}]\n\n🔥 **JACKPOT!** You won {win_amount} credits!"
        elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
            win_amount = 100
            update_balance(user_id, win_amount)
            msg = f"🎰 [{reel1} | {reel2} | {reel3}]\n\n✨ **MATCH TWO!** You won {win_amount} credits!"
        else:
            update_balance(user_id, -bet)
            msg = f"🎰 [{reel1} | {reel2} | {reel3}]\n\nBetter luck next spin! (-{bet} credits)"

        keyboard = [
            [InlineKeyboardButton("Spin Again (50)", callback_data="game_slots")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            f"{msg}\n\n💳 New Balance: *{get_balance(user_id)} Credits*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("No BOT_TOKEN environment variable provided.")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Starting Telegram Bot long-polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
