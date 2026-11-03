import os
import random
import logging
from telebot import TeleBot, types

# Setup logger
logging.basicConfig(level=logging.INFO)

# Load Token from Environment Variables
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("ERROR: BOT_TOKEN environment variable is not set!")

bot = TeleBot(TOKEN)

# In-memory storage for user balances (use a database like PostgreSQL/Redis for production)
user_balances = {}

def get_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = 1000  # Default starting bonus points
    return user_balances[user_id]

# --- KEYBOARDS ---

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_casino = types.InlineKeyboardButton("🎰 Casino & Games", callback_data="menu_casino")
    btn_boost = types.InlineKeyboardButton("🚀 Channel Boost", callback_data="menu_boost")
    btn_balance = types.InlineKeyboardButton("💰 My Balance", callback_data="check_balance")
    btn_help = types.InlineKeyboardButton("❓ Help", callback_data="menu_help")
    markup.add(btn_casino, btn_boost, btn_balance, btn_help)
    return markup

def casino_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_slots = types.InlineKeyboardButton("🎰 Telegram Slot", callback_data="game_slots")
    btn_dice = types.InlineKeyboardButton("🎲 Dice Roll", callback_data="game_dice")
    btn_coin = types.InlineKeyboardButton("🪙 Coin Flip", callback_data="game_coin")
    btn_back = types.InlineKeyboardButton("⬅️ Back to Main", callback_data="main_menu")
    markup.add(btn_slots, btn_dice, btn_coin, btn_back)
    return markup

def boost_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_boost_info = types.InlineKeyboardButton("⭐ Boost Channel Perks", callback_data="boost_info")
    btn_claim_reward = types.InlineKeyboardButton("🎁 Claim Boost Bonus (100 pts)", callback_data="claim_boost")
    btn_back = types.InlineKeyboardButton("⬅️ Back to Main", callback_data="main_menu")
    markup.add(btn_boost_info, btn_claim_reward, btn_back)
    return markup

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    text = (
        f"👋 Welcome to the **Casino & Boost Hub**, {message.from_user.first_name}!\n\n"
        f"💰 **Current Balance:** `{balance}` PTS\n"
        "Choose an option below to play games or boost your community:"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu())

# --- CALLBACK QUERY HANDLERS ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    balance = get_balance(user_id)

    if call.data == "main_menu":
        bot.edit_message_text(
            f"🏠 **Main Menu**\n💰 **Current Balance:** `{balance}` PTS",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif call.data == "menu_casino":
        bot.edit_message_text(
            "🎰 **Casino Zone**\nSelect a mini-game below to bet and win points!",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=casino_menu()
        )

    elif call.data == "menu_boost":
        bot.edit_message_text(
            "🚀 **Telegram Channel Boost Zone**\n\n"
            "Boost your community to unlock custom emojis, audio messages, and stories!",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=boost_menu()
        )

    elif call.data == "check_balance":
        bot.answer_callback_query(call.id, f"💰 Balance: {balance} PTS", show_alert=True)

    # --- GAMES LOGIC ---
    elif call.data == "game_slots":
        bet = 50
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Not enough points! Needs 50 PTS.", show_alert=True)
            return

        user_balances[user_id] -= bet
        # Send native Telegram animated slot machine
        msg = bot.send_dice(chat_id, emoji="🎰")
        val = msg.dice.value

        # Value 64 is Jackpot (777) in Telegram Slot dice
        if val == 64:
            reward = 500
            user_balances[user_id] += reward
            bot.send_message(chat_id, f"🎉 **JACKPOT!** You won `{reward}` PTS! 🎰", parse_mode="Markdown")
        elif val in [1, 22, 43]:  # Common match values
            reward = 100
            user_balances[user_id] += reward
            bot.send_message(chat_id, f"✨ Big Win! You won `{reward}` PTS!", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ You lost `{bet}` PTS. Try again!", parse_mode="Markdown")

    elif call.data == "game_dice":
        bet = 20
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Not enough points! Needs 20 PTS.", show_alert=True)
            return

        user_balances[user_id] -= bet
        msg = bot.send_dice(chat_id, emoji="🎲")
        val = msg.dice.value

        if val >= 4:
            reward = bet * 2
            user_balances[user_id] += reward
            bot.send_message(chat_id, f"🎲 Rolled `{val}`! You won `{reward}` PTS!", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"🎲 Rolled `{val}`. You lost `{bet}` PTS.", parse_mode="Markdown")

    elif call.data == "game_coin":
        bet = 25
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Not enough points! Needs 25 PTS.", show_alert=True)
            return
        
        outcome = random.choice(["Heads", "Tails"])
        if outcome == "Heads":
            reward = 50
            user_balances[user_id] += reward
            bot.send_message(chat_id, f"🪙 Result: **Heads**! You won `{reward}` PTS!", parse_mode="Markdown")
        else:
            user_balances[user_id] -= bet
            bot.send_message(chat_id, f"🪙 Result: **Tails**! You lost `{bet}` PTS.", parse_mode="Markdown")

    # --- BOOST LOGIC ---
    elif call.data == "boost_info":
        info_text = (
            "🚀 **How to Boost Telegram Channel:**\n\n"
            "1. Open the Channel menu.\n"
            "2. Click **Boost**.\n"
            "3. Help your channel reach higher levels to unlock custom channel perks!"
        )
        bot.send_message(chat_id, info_text, parse_mode="Markdown")

    elif call.data == "claim_boost":
        user_balances[user_id] += 100
        bot.answer_callback_query(call.id, "🎁 Claimed 100 Boost Bonus PTS!", show_alert=True)

if __name__ == "__main__":
    logging.info("Bot starting...")
    bot.infinity_polling(skip_pending_updates=True)
