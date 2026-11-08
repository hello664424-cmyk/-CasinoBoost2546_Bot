import os
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration settings via environment variables (stripped of hidden spaces)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@YourChannelUsername").strip()
INITIAL_BALANCE = 100
DAILY_BONUS = 50

# In-memory user database storage
# Format: { user_id: { "balance": int, "wins": int, "losses": int } }
users_db = {}

def get_user_data(user_id: int) -> dict:
    if user_id not in users_db:
        users_db[user_id] = {"balance": INITIAL_BALANCE, "wins": 0, "losses": 0}
    return users_db[user_id]

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifies if the user is subscribed to the required channel."""
    if not REQUIRED_CHANNEL or REQUIRED_CHANNEL == "@YourChannelUsername":
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return True

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎲 Roll Dice (10 pts)", callback_data="game_dice"),
            InlineKeyboardButton("🎰 Slots (10 pts)", callback_data="game_slots"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball (10 pts)", callback_data="game_basket"),
        ],
        [
            InlineKeyboardButton("💰 Balance & Stats", callback_data="user_stats"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
        ],
        [
            InlineKeyboardButton("📢 Join Channel to Play", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    get_user_data(user.id)
    
    welcome_text = (
        f"👋 Welcome **{user.first_name}** to the Casino Engagement Bot!\n\n"
        f"🎮 Play native games, track your balance, and boost your standing.\n"
        f"📌 *Make sure you join {REQUIRED_CHANNEL} to qualify for rewards!*"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def handle_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    chat_id = query.message.chat_id

    # Check Channel Subscription
    subscribed = await is_subscribed(user_id, context)
    if not subscribed:
        await query.edit_message_text(
            f"⚠️ **Access Denied!**\n\nYou must join {REQUIRED_CHANNEL} to play games.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel Now", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
                [InlineKeyboardButton("🔄 Verify & Menu", callback_data="main_menu")]
            ])
        )
        return

    # Check balance requirements
    bet_cost = 10
    if user_data["balance"] < bet_cost:
        await query.edit_message_text(
            f"❌ **Insufficient Balance!**\nYou need at least {bet_cost} points to play.\n"
            f"Current Balance: {user_data['balance']} points.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    # Deduct bet cost
    user_data["balance"] -= bet_cost
    action = query.data

    if action == "game_dice":
        msg = await context.bot.send_dice(chat_id=chat_id, emoji="🎲")
        val = msg.dice.value
        # Dice logic: 4, 5, 6 are wins
        if val >= 4:
            win_amount = bet_cost * 2
            user_data["balance"] += win_amount
            user_data["wins"] += 1
            result_text = f"🎉 **You won {win_amount} points!** (Rolled {val})"
        else:
            user_data["losses"] += 1
            result_text = f"📉 **You lost {bet_cost} points.** (Rolled {val})"

    elif action == "game_slots":
        msg = await context.bot.send_dice(chat_id=chat_id, emoji="🎰")
        val = msg.dice.value
        # Slot values range 1-64. 64 is triple 7s (jackpot), other specific values are partial wins
        if val == 64:
            win_amount = bet_cost * 10
            user_data["balance"] += win_amount
            user_data["wins"] += 1
            result_text = f"💥 **JACKPOT! You won {win_amount} points!** 🎰"
        elif val in [1, 22, 43]:
            win_amount = float(bet_cost * 2)
            user_data["balance"] += int(win_amount)
            user_data["wins"] += 1
            result_text = f"✨ **Good Spin! You won {int(win_amount)} points!**"
        else:
            user_data["losses"] += 1
            result_text = f"📉 **Better luck next time! Lost {bet_cost} points.**"

    elif action == "game_basket":
        msg = await context.bot.send_dice(chat_id=chat_id, emoji="🏀")
        val = msg.dice.value
        # Basketball: values 4 and 5 indicate scored baskets
        if val in [4, 5]:
            win_amount = bet_cost * 2
            user_data["balance"] += win_amount
            user_data["wins"] += 1
            result_text = f"🏀 **SWISH! You scored and won {win_amount} points!**"
        else:
            user_data["losses"] += 1
            result_text = f"❌ **Missed shot! Lost {bet_cost} points.**"

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{result_text}\n💰 **Current Balance:** {user_data['balance']}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user_data(user_id)

    stats_text = (
        f"📊 **User Statistics**\n\n"
        f"👤 User: {query.from_user.first_name}\n"
        f"💰 Balance: `{user_data['balance']}` points\n"
        f"🏆 Total Wins: `{user_data['wins']}`\n"
        f"❌ Total Losses: `{user_data['losses']}`\n"
    )

    await query.edit_message_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ])
    )

async def handle_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user_data(user_id)

    user_data["balance"] += DAILY_BONUS

    await query.edit_message_text(
        f"🎁 **Daily Reward Claimed!**\n\n"
        f"You received `{DAILY_BONUS}` points!\n"
        f"💰 New Balance: `{user_data['balance']}` points.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ])
    )

def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers setup
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(handle_stats, pattern="^user_stats$"))
    application.add_handler(CallbackQueryHandler(handle_daily, pattern="^daily_bonus$"))
    application.add_handler(CallbackQueryHandler(handle_games, pattern="^game_"))

    # Start long polling
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
