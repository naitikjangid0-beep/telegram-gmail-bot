import os
import random
import sqlite3
import telebot
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app import app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

# Keep-alive thread for Flask Server
def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

keep_alive()

# CONFIGURATION SETUP
BOT_TOKEN = "8880017395:AAEaRXzwxC3jPmy9HASJiRH-4n5A2o7xgWg"
ADMIN_CHAT_ID = "8825488979"
ADMIN_ID = 8825480979
FIXED_PASSWORD = "WsxJaggu@#"
HELP_USERNAME = "@GETOPSUP"
CHANNEL_LINK = "https://t.me/+lOpg8sGDP7YyNWU1"

bot = telebot.TeleBot(BOT_TOKEN)

FIRST_NAMES = ["Pooja", "Rahul", "Neha", "Amit", "Priya", "Suresh", "Kiran", "Vikram", "Anjali", "Rohan"]
LAST_NAMES = ["Gupta", "Sharma", "Verma", "Singh", "Kumar", "Patel", "Joshi", "Yadav", "Mehta", "Das"]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            assigned_email TEXT,
            status TEXT DEFAULT 'Pending',
            upi_id TEXT,
            balance REAL DEFAULT 0,
            tasks_done INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            upi_id TEXT,
            amount REAL,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Auto-add missing columns safely
    columns_to_check = [
        ("upi_id", "TEXT"),
        ("assigned_email", "TEXT"),
        ("status", "TEXT DEFAULT 'Pending'"),
        ("username", "TEXT")
    ]
    for col_name, col_type in columns_to_check:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

init_db()

def generate_task_details():
    f_name = random.choice(FIRST_NAMES)
    l_name = random.choice(LAST_NAMES)
    rand_num = random.randint(100000, 999999)
    email = f"{f_name.lower()}{l_name.lower()}{rand_num}@gmail.com"
    dob = f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.randint(1995,2003)}"
    return f_name, l_name, email, dob

def send_force_join_msg(chat_id):
    join_markup = InlineKeyboardMarkup()
    join_markup.add(InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_LINK))
    join_markup.add(InlineKeyboardButton("🔄 Joined / Check", callback_data="check_joined"))
    
    bot.send_message(
        chat_id,
        "⚠️ <b>Must Join Channel!</b>\n\nTo use this bot, you must first join our official Telegram channel below.",
        parse_mode="HTML",
        reply_markup=join_markup
    )

def send_main_menu(chat_id, first_name):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📄 Register an Account"),
        KeyboardButton("📁 My Accounts"),
        KeyboardButton("💰 Balance"),
        KeyboardButton("📢 Referrals"),
        KeyboardButton("🎁 Rewards"),
        KeyboardButton("🏦 Add UPI"),
        KeyboardButton("💬 Help"),
        KeyboardButton("🏧 Withdraw")
    )

    bot.send_message(
        chat_id,
        f"Hi {first_name}! Welcome back.",
        reply_markup=markup
    )

# --------------------------------------------------
# BOT HANDLERS
# --------------------------------------------------

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or "N/A"

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
        c.execute("UPDATE users SET first_name = ?, username = ? WHERE user_id = ?", (first_name, username, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Database Error:", e)

    send_force_join_msg(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_join_callback(call):
    bot.answer_callback_query(call.id, "Welcome! Loading menu...")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_main_menu(call.message.chat.id, call.from_user.first_name)

@bot.message_handler(func=lambda message: message.text == "📄 Register an Account")
def assign_task(message):
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"
    first_name = message.from_user.first_name or "User"
    f_name, l_name, email, dob = generate_task_details()

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
        c.execute("UPDATE users SET assigned_email = ?, username = ?, status = 'Pending' WHERE user_id = ?", (email, username, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Update Error:", e)

    task_msg = (
        "-------------------\n"
        f"First name: <code>{f_name}</code>\n"
        f"Last name: <code>{l_name}</code>\n"
        "-------------------\n"
        "Date of birth\n"
        f"<code>{dob}</code>\n"
        "-------------------\n"
        f"Email: <code>{email}</code>\n"
        "-------------------\n"
        f"Password: <code>{FIXED_PASSWORD}</code>\n"
        "-------------------\n"
        "🔒 Be sure to use the specified data, otherwise the account will not be paid."
    )

    inline_btn = InlineKeyboardMarkup()
    inline_btn.add(InlineKeyboardButton("🟢 Done", callback_data=f"done_{email}"))

    bot.send_message(message.chat.id, task_msg, parse_mode="HTML", reply_markup=inline_btn)

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def handle_done(call):
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "📸 Please send the Gmail account screenshot now.")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    bot.reply_to(
        message, 
        "✅ <b>Task Submitted Successfully!</b>\n\n"
        "⏳ <b>Reward:</b> ₹10 Pending for Approval\n\n"
        "Aapka screenshot verification ke liye chala gaya hai.",
        parse_mode="HTML"
    )

    if ADMIN_CHAT_ID:
        photo_id = message.photo[-1].file_id
        admin_text = f"📥 <b>NEW SUBMISSION</b>\n👤 User: {user_name} (<code>{user_id}</code>)\n💰 Reward: ₹10 Pending"
        try:
            bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=admin_text, parse_mode="HTML")
        except Exception as e:
            print("Admin photo error:", e)

@bot.message_handler(func=lambda message: "Add UPI" in message.text)
def add_upi(message):
    msg = bot.send_message(message.chat.id, "📝 Please send your UPI ID:")
    bot.register_next_step_handler(msg, process_upi_handler)

def process_upi_handler(message):
    upi_id = message.text.strip()
    user_id = message.from_user.id

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET upi_id = ? WHERE user_id = ?", (upi_id, user_id))
        conn.commit()
        conn.close()

        bot.send_message(
            message.chat.id, 
            f"💳 **UPI ID Saved Successfully!**\n\nYour UPI: <code>{upi_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error saving UPI: {e}")

@bot.message_handler(func=lambda message: message.text in ["🏧 Withdraw", "💰 Withdraw"])
def withdraw(message):
    user_id = message.from_user.id
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT balance, upi_id FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row or row[0] <= 0:
            bot.send_message(message.chat.id, "⚠️ Balance insufficient or ₹0 balance.")
            conn.close()
            return
        if not row[1]:
            bot.send_message(message.chat.id, "⚠️ Please add UPI ID first using '🏦 Add UPI'.")
            conn.close()
            return

        amount, upi_id = row[0], row[1]

        cursor.execute("INSERT INTO withdrawals (user_id, upi_id, amount, status) VALUES (?, ?, ?, 'Pending')", (user_id, upi_id, amount))
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ Withdrawal request of ₹{amount} submitted for UPI <code>{upi_id}</code>!", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error during withdrawal: {e}")

@bot.message_handler(func=lambda message: message.text == "💰 Balance")
def balance(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    bal = row[0] if row else 0
    bot.send_message(message.chat.id, f"💰 Your Current Balance: ₹{bal}")

@bot.message_handler(func=lambda message: message.text == "📁 My Accounts")
def my_accounts(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT tasks_done FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    done = row[0] if row else 0
    bot.send_message(message.chat.id, f"📁 Total Accounts Approved: {done}")

@bot.message_handler(func=lambda message: message.text == "🎁 Rewards")
def rewards_info(message):
    rewards_msg = (
        "🎁 <b>REWARD RATES</b> 🎁\n\n"
        "📌 <b>Per Gmail:</b> ₹10\n"
        "📌 <b>10+ Gmails:</b> ₹15 per Gmail\n\n"
        "💡 <i>Create more accounts daily to earn higher rewards!</i>"
    )
    bot.send_message(message.chat.id, rewards_msg, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "💬 Help")
def help_msg(message):
    bot.send_message(message.chat.id, f"💬 Support: {HELP_USERNAME}")

# --------------------------------------------------
# RUN BOT
# --------------------------------------------------
print("Bot updated & running...")
bot.infinity_polling()
