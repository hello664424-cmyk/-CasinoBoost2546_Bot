import os
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Centralized in-memory storage for user data
# Structure: {user_id: {"balance": float, "referrals": int}}
users_db = {}

def get_user_data(user_id: int) -> dict:
    """Retrieve or initialize user data with a starting balance of $100."""
    if user_id not in users_db:
        users_db[user_id] = {"balance": 100.0, "referrals": 0}
    return users_db[user_id]


def build_main_keyboard() -> ReplyKeyboardMarkup:
    """Creates the main persistent bottom keyboard."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎰 Casino Games"), KeyboardButton("💰 Wallet")],
            [KeyboardButton("🚀 Boost & Referral"), KeyboardButton("🎁 Daily Bonus")]
        ],
        resize_keyboard=True
    )


def build_games_inline_keyboard() -> InlineKeyboardMarkup:
    """Creates the inline keyboard for choosing casino games."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎲 Dice Roll", callback_data="game_dice"),
            InlineKeyboardButton("🎰 Slot Machine", callback_data="game_slots"),
        ],
        [
            InlineKeyboardButton("🎯 Darts", callback_data="game_darts"),
            InlineKeyboardButton("⚽ Penalty Kick", callback_data="game_football"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="game_basketball"),
            InlineKeyboardButton("🪙 Coin Flip (50/50)", callback_data="game_coinflip"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")
        ]
    ])


# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_data = get_user_data(user_id)

    # Handle Referral tracking via /start <referrer_id>
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user_id and referrer_id in users_db:
            users_db[referrer_id]["balance"] += 50.0
            users_db[referrer_id]["referrals"] += 1
            try:
                await context.bot.send_message(
                    referrer_id, 
                    "🎉 <b>New Referral!</b> You earned <b>+$50</b> for inviting a user!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # Instant delivery of the welcome screen & games to satisfy ad review destination guidelines
    welcome_text = (
        f"👋 សួស្តី <b>{user.first_name}</b> មកកាន់ Casino Boost Bot!\n\n"
        f"💳 ប្រាក់សមតុល្យរបស់អ្នក: <b>${user_data['balance']:.2f}</b>\n"
        "👇 <b>ជ្រើសរើសហ្គេមកាស៊ីណូបង្រ្កាបសំណាងរបស់អ្នកខាងក្រោមនេះ៖</b>"
    )
    
    # Send main keyboard and instant game menu to satisfy reviewer criteria
    if update.callback_query:
        await update.callback_query.message.reply_text(
            welcome_text, 
            reply_markup=build_main_keyboard(), 
            parse_mode="HTML"
        )
        await update.callback_query.message.reply_text(
            "🎰 <b>លេងកាស៊ីណូឥឡូវនេះ ($10 ក្នុងមួយការភ្នាល់):</b>",
            reply_markup=build_games_inline_keyboard(),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            welcome_text, 
            reply_markup=build_main_keyboard(), 
            parse_mode="HTML"
        )
        await update.message.reply_text(
            "🎰 <b>លេងកាស៊ីណូឥឡូវនេះ ($10 ក្នុងមួយការភ្នាល់):</b>",
            reply_markup=build_games_inline_keyboard(),
            parse_mode="HTML"
        )


# --- TEXT MENU HANDLERS ---

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    if text == "🎰 Casino Games":
        await update.message.reply_text(
            "🎰 <b>Select a Casino Game to Play ($10 per roll/bet):</b>",
            reply_markup=build_games_inline_keyboard(),
            parse_mode="HTML"
        )
    elif text == "💰 Wallet":
        wallet_text = (
            "💼 <b>Your Casino Wallet</b>\n\n"
            f"• Current Balance: <b>${user_data['balance']:.2f}</b>\n"
            f"• Total Referrals: <b>{user_data['referrals']} users</b>"
        )
        await update.message.reply_text(wallet_text, parse_mode="HTML")
    elif text == "🚀 Boost & Referral":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        ref_text = (
            "🚀 <b>Boost Your Balance!</b>\n\n"
            "Invite your friends to the bot and get free bonus coins!\n"
            "🎁 <b>Reward:</b> <b>+$50.00</b> for every friend that joins.\n\n"
            f"🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>"
        )
        await update.message.reply_text(ref_text, parse_mode="HTML")
    elif text == "🎁 Daily Bonus":
        user_data["balance"] += 25.0
        await update.message.reply_text(
            f"🎁 <b>Daily Bonus Claimed!</b>\nAdded <b>+$25.00</b> to your wallet.\n💰 New Balance: <b>${user_data['balance']:.2f}</b>",
            parse_mode="HTML"
        )


# --- CALLBACK QUERY (GAME LOGIC & MENU ACTIONS) ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    data = query.data

    if data == "menu_main":
        await query.message.reply_text(
            "🏠 <b>Main Menu</b>\nChoose an option below:",
            reply_markup=build_main_keyboard(),
            parse_mode="HTML"
        )
        return

    BET_AMOUNT = 10.0

    if data.startswith("game_"):
        game_type = data.replace("game_", "")

        # Check balance
        if user_data["balance"] < BET_AMOUNT:
            await query.message.reply_text(
                "❌ Insufficient balance! Invite friends or claim your daily bonus to get more funds."
            )
            return

        # Deduct Bet
        user_data["balance"] -= BET_AMOUNT

        if game_type in ["dice", "slots", "darts", "football", "basketball"]:
            emoji_map = {
                "dice": "🎲",
                "slots": "🎰",
                "darts": "🎯",
                "football": "⚽",
                "basketball": "🏀"
            }
            emoji = emoji_map[game_type]
            
            # Send native animated dice message
            msg = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
            score = msg.dice.value
            
            # Brief pause for animation
            import asyncio
            await asyncio.sleep(3)

            payout = 0.0
            if game_type == "slots":
                if score == 64:
                    payout = 100.0
                    result_text = "🎉 <b>JACKPOT! 777!</b> You won <b>+$100.00</b>!"
                elif score in [1, 22, 43]:
                    payout = 25.0
                    result_text = "✨ <b>Match!</b> You won <b>+$25.00</b>!"
                else:
                    result_text = "❌ No match! Try again."
            
            elif game_type == "dice":
                if score >= 4:
                    payout = 20.0
                    result_text = f"🎯 Rolled <b>{score}</b>! You won <b>+$20.00</b>!"
                else:
                    result_text = f"📉 Rolled <b>{score}</b>. Better luck next time!"

            elif game_type == "darts":
                if score == 6:
                    payout = 30.0
                    result_text = "🎯 <b>BULLSEYE!</b> You won <b>+$30.00</b>!"
                elif score >= 3:
                    payout = 15.0
                    result_text = f"🎯 Hit score <b>{score}</b>! You won <b>+$15.00</b>!"
                else:
                    result_text = "❌ Missed the target!"

            elif game_type in ["football", "basketball"]:
                if score >= 4:
                    payout = 20.0
                    result_text = "⚽/🏀 <b>SCORE!</b> You won <b>+$20.00</b>!"
                else:
                    result_text = "❌ Missed!"

            user_data["balance"] += payout
            await query.message.reply_text(
                f"{result_text}\n💰 New Balance: <b>${user_data['balance']:.2f}</b>",
                reply_markup=build_games_inline_keyboard(),
                parse_mode="HTML"
            )

        elif game_type == "coinflip":
            outcome = random.choice(["Heads", "Tails"])
            win = random.choice([True, False])

            if win:
                payout = 20.0
                result_text = f"🪙 It landed on <b>{outcome}</b>! You WON <b>+$20.00</b>!"
                user_data["balance"] += payout
            else:
                result_text = f"🪙 It landed on <b>{outcome}</b>. You Lost!"

            await query.message.reply_text(
                f"{result_text}\n💰 New Balance: <b>${user_data['balance']:.2f}</b>",
                reply_markup=build_games_inline_keyboard(),
                parse_mode="HTML"
            )


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("No BOT_TOKEN environment variable provided.")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Starting Telegram Bot long-polling...")
    app.run_polling(skip_pending=True)


if __name__ == "__main__":
    main()
