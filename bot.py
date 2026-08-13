BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running live!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
import random
import sqlite3
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
def add_user_to_db(user_id, first_name):
    try:
       conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                tasks_done INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, first_name, balance, tasks_done) 
            VALUES (?, ?, 0, 0)
        ''', (user_id, first_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Error:", e)
# --------------------------------------------------
# CONFIGURATION SETUP
# --------------------------------------------------
BOT_TOKEN = "8880017395:AAEaRXzwxC3jPmy9HASJiRH-4n5A2o7xgWg"
ADMIN_CHAT_ID = "8825488979"
FIXED_PASSWORD = "WsxJaggu@#"
HELP_USERNAME = "@GETOPSUP"

# Force Join Channel Link
CHANNEL_LINK = "https://t.me/+lOpg8sGDP7YyNWU1"

bot = telebot.TeleBot(BOT_TOKEN)
# ================= ADMIN CONTROL PANEL =================
ADMIN_ID = 8825480979

def get_admin_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    btn1 = InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
    btn2 = InlineKeyboardButton("📩 Pending SS", callback_data="admin_pending")
    btn3 = InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
    markup.add(btn1, btn2, btn3)
    return markup

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "👑 *Admin Control Panel*\nSelect an option below:",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, "❌ Unauthorized Access!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_clicks(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Access Denied!", show_alert=True)
        return

    if call.data == "admin_stats":
        msg = "📊 *Live Stats*\nTotal Users: 10\nTasks Done: 5\nPending SS: 2"
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Stats Refreshed!")

    elif call.data == "admin_pending":
        bot.send_message(call.message.chat.id, "📩 *Pending Screenshots:*\nCurrently 0 screenshots waiting for approval.")
        bot.answer_callback_query(call.id)

    elif call.data == "admin_broadcast":
        bot.send_message(call.message.chat.id, "📢 Send message to broadcast in format: /send Hello Users")
        bot.answer_callback_query(call.id)
# Sample Names for Random Email Generation
FIRST_NAMES = ["Pooja", "Rahul", "Neha", "Amit", "Priya", "Suresh", "Kiran", "Vikram", "Anjali", "Rohan"]
LAST_NAMES = ["Gupta", "Sharma", "Verma", "Singh", "Kumar", "Patel", "Joshi", "Yadav", "Mehta", "Das"]

# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    upi_id TEXT,
    balance REAL DEFAULT 0,
    tasks_done INTEGER DEFAULT 0
)
''')
conn.commit()

# Helper function to generate dynamic Gmail details
def generate_task_details():
    f_name = random.choice(FIRST_NAMES)
    l_name = random.choice(LAST_NAMES)
    rand_num = random.randint(100000, 999999)
    email = f"{f_name.lower()}{l_name.lower()}{rand_num}@gmail.com"
    dob = f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.randint(1995,2003)}"
    return f_name, l_name, email, dob

# Helper to show join channel popup
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

# Send Main Menu Buttons
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
    first_name = message.from_user.first_name

    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (user_id, first_name, balance, tasks_done) VALUES (?, ?, 0, 0)", (user_id, first_name))
            conn.commit()
    except Exception as e:
        print("Database Error:", e)

    # Direct Force Join Popup
    send_force_join_msg(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_join_callback(call):
    bot.answer_callback_query(call.id, "Welcome! Loading menu...")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_main_menu(call.message.chat.id, call.from_user.first_name)

@bot.message_handler(func=lambda message: message.text == "📄 Register an Account")
def assign_task(message):
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"
    f_name, l_name, email, dob = generate_task_details()

   # Save details to Database for Dashboard View
    try:
        conn = sqlite3.connect('DB_PATH)
        c = conn.cursor()
        first_name = message.from_user.first_name or "User"
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
    bot.send_message(message.chat.id, task_msg, parse_mode="HTML", reply_markup=inline_btn)

# 1. User "Done" dabaye -> Bot Screenshot maange
@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def handle_done(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id, "📸 Please send the Gmail account screenshot now.")

# 2. User Screenshot (Photo) bheje -> Bot Success message de
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    bot.reply_to(message, "✅ Submitted successfully!\n💰 ₹10 pending, wait for approval.")

    if ADMIN_CHAT_ID:
        photo_id = message.photo[-1].file_id
        admin_text = f"📥 <b>NEW SUBMISSION</b>\n👤 User: {user_name} (<code>{user_id}</code>)\n💰 Reward: ₹10 Pending\n\n📸 <i>Check screenshot above to verify the Gmail account!</i>"
        try:
            bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=admin_text, parse_mode="HTML")
        except Exception as e:
            print("Admin photo error:", e)

@bot.message_handler(func=lambda message: message.text == "🎁 Rewards")
def rewards_info(message):
    rewards_msg = (
        "🎁 <b>REWARD RATES</b> 🎁\n\n"
        "📌 <b>Per Gmail:</b> ₹10\n"
        "📌 <b>10+ Gmails:</b> ₹15 per Gmail\n\n"
        "💡 <i>Create more accounts daily to earn higher rewards!</i>"
    )
    bot.send_message(message.chat.id, rewards_msg, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "📢 Referrals")
def referrals_info(message):
    pass

@bot.message_handler(func=lambda message: message.text == "💰 Balance")
def balance(message):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    bal = row[0] if row else 0
    bot.send_message(message.chat.id, f"💰 Your Current Balance: ₹{bal}")

@bot.message_handler(func=lambda message: message.text == "📁 My Accounts")
def my_accounts(message):
    bot.send_message(message.chat.id, "📁 Total Accounts Submitted: 0")

@bot.message_handler(func=lambda message: message.text == "🏦 Add UPI")
def add_upi(message):
    msg = bot.send_message(message.chat.id, "📝 Please send your UPI ID:")
    bot.register_next_step_handler(msg, process_upi)

def process_upi(message):
    upi = message.text.strip()
    cursor.execute("UPDATE users SET upi_id = ? WHERE user_id = ?", (upi, message.from_user.id))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ UPI ID Saved: <code>{upi}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "💬 Help")
def help_msg(message):
    bot.send_message(message.chat.id, f"💬 Support: {HELP_USERNAME}")

@bot.message_handler(func=lambda message: message.text == "🏧 Withdraw")
def withdraw(message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance, upi_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row or row[0] <= 0:
        bot.send_message(message.chat.id, "⚠️ Balance insufficient.")
        return
    if not row[1]:
        bot.send_message(message.chat.id, "⚠️ Please add UPI ID first using '🏦 Add UPI'.")
        return

    amount, upi_id = row[0], row[1]
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
    conn.commit()

    bot.send_message(message.chat.id, f"✅ Withdrawal request of ₹{amount} submitted for UPI <code>{upi_id}</code>!", parse_mode="HTML")
# ================= AUTO-RECEIVE SCREENSHOT & LOG TO ADMIN =================
@bot.message_handler(content_types=['photo'])
def handle_screenshot_auto(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Check if user exists in database
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        bot.reply_to(message, "Please register first using /start")
        return

    # Admin ko Photo Log bhejna (Verification ke liye)
    photo_id = message.photo[-1].file_id
    try:
        bot.send_photo(
            ADMIN_ID, 
            photo_id, 
            caption=f"📥 <b>New Task Submitted for Approval!</b>\n\n👤 <b>User:</b> {first_name}\n🆔 <b>ID:</b> <code>{user_id}</code>\n💰 <b>Reward:</b> ₹10 Pending",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error sending log to admin: {e}")

    # User ko Confirmation (Pending for Approval)
    bot.reply_to(
        message, 
        "✅ <b>Task Submitted Successfully!</b>\n\n"
        "⏳ <b>Reward:</b> ₹10 Pending for Approval\n\n"
        "Aapka screenshot verification ke liye chala gaya hai. Check hone ke baad reward aapke account mein add ho jayega.",
        parse_mode="HTML"
    )
    # User Withdraw Handler
@bot.message_handler(func=lambda message: message.text == "💰 Withdraw")
def request_withdraw(message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    balance = row[0] if row else 0
    if balance < 30: # Minimum withdrawal threshold
        bot.send_message(message.chat.id, f"❌ Minimum withdrawal limit is ₹30. Your balance is ₹{balance}.")
    else:
        msg = bot.send_message(message.chat.id, f"💳 Your Balance: ₹{balance}\n\nPlease enter your **UPI ID** to withdraw:")
        bot.register_next_step_handler(msg, process_upi, balance)

def process_upi(message, balance):
    upi_id = message.text
    user_id = message.from_user.id
    
    try:
        cursor.execute("INSERT INTO withdrawals (user_id, upi_id, amount) VALUES (?, ?, ?)", (user_id, upi_id, balance))
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Withdrawal request of ₹{balance} sent! Admin will pay to `{upi_id}` soon.", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, "Something went wrong. Please try again.")
# --------------------------------------------------
# RUN BOT
# --------------------------------------------------
print("Bot updated & running...")
bot.infinity_polling()
