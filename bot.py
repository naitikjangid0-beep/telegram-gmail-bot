import os
import random
import sqlite3
import time
import telebot
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app import app, DB_PATH

BOT_TOKEN = "8880017395:AAEaRXzwxC3jPmy9HASJiRH-4n5A2o7xgWg"
FIXED_PASSWORD = "WsxJaggu@#"
HELP_USERNAME = "@GETOPSUP"
CHANNEL_LINK = "https://t.me/+lOpg8sGDP7YyNWU1"

bot = telebot.TeleBot(BOT_TOKEN)

FIRST_NAMES = ["Robert", "Daniel", "Michael", "James", "David", "Pooja", "Rahul", "Neha", "Amit", "Priya"]
LAST_NAMES = ["Odebralski", "Smith", "Johnson", "Williams", "Gupta", "Sharma", "Verma", "Singh"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def generate_task_details():
    f_name = random.choice(FIRST_NAMES)
    l_name = random.choice(LAST_NAMES)
    rand_num = random.randint(100, 999)
    email = f"{f_name.lower()}{l_name.lower()}{rand_num}@gmail.com"
    reg_id = f"G{random.randint(10000000, 99999999)}"
    
    month = random.choice(MONTHS)
    day = random.randint(1, 28)
    year = random.randint(1995, 2006)
    
    return f_name, l_name, email, reg_id, month, day, year

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
        KeyboardButton("🎁 Rewards"),
        KeyboardButton("🏦 Add UPI"),
        KeyboardButton("💬 Help"),
        KeyboardButton("🏧 Withdraw")
    )
    bot.send_message(chat_id, f"Hi {first_name}! Welcome back.", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""

    try:
        conn = from app import app, DB_PATH, get_db_connection
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
        c.execute("UPDATE users SET first_name = ?, username = ? WHERE user_id = ?", (first_name, username, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Error:", e)

    send_force_join_msg(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_join_callback(call):
    bot.answer_callback_query(call.id, "Welcome!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_main_menu(call.message.chat.id, call.from_user.first_name)

@bot.message_handler(func=lambda message: message.text == "📄 Register an Account")
def assign_task(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""
    f_name, l_name, email, reg_id, month, day, year = generate_task_details()

    try:
        conn = from app import app, DB_PATH, get_db_connection
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
        c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        c.execute("INSERT INTO tasks (user_id, assigned_email, status) VALUES (?, ?, 'Pending')", (user_id, email))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Error:", e)

    task_msg = (
        f"<b>New Task (Registration ID: {reg_id})</b>\n\n"
        "Complete Task and get paid for it.\n\n"
        "For each Task you will receive: from 10₹\n"
        "――――――――――\n"
        f"First name: <code>{f_name}</code>\n"
        f"Last name: <code>{l_name}</code>\n"
        "――――――――――\n"
        "Date of birth\n"
        f"Month: <code>{month}</code> | Day: <code>{day}</code> | Year: <code>{year}</code>\n"
        "――――――――――\n"
        f"Email: <code>{email}</code>\n"
        "――――――――――\n"
        f"Password: <code>{FIXED_PASSWORD}</code>\n"
        "――――――――――\n"
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
    bot.send_message(call.message.chat.id, "📸 Send screenshot proof now to complete submission.")

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    try:
        conn = from app import app, DB_PATH, get_db_connection
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET screenshot_id = ? WHERE id = (SELECT MAX(id) FROM tasks WHERE user_id = ?)", (photo_id, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Screenshot Update Error:", e)

    reply_text = (
        "✅ <b>Your task submitted!</b>\n"
        "Status: <b>Pending</b>\n\n"
        "📌 <b>NOTE:</b>\n"
        "<i>Apne device se Gmail account ko logout kar dein.</i>"
    )
    bot.reply_to(message, reply_text, parse_mode="HTML")

@bot.message_handler(func=lambda message: "Add UPI" in message.text)
def add_upi(message):
    msg = bot.send_message(message.chat.id, "📝 Send UPI ID:")
    bot.register_next_step_handler(msg, process_upi_handler)

def process_upi_handler(message):
    upi_id = message.text.strip()
    user_id = message.from_user.id

    try:
        conn = from app import app, DB_PATH, get_db_connection
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET upi_id = ? WHERE user_id = ?", (upi_id, user_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"💳 UPI Saved: <code>{upi_id}</code>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, "Error saving UPI.")

@bot.message_handler(func=lambda message: message.text in ["🏧 Withdraw", "💰 Withdraw"])
def withdraw(message):
    user_id = message.from_user.id
    try:
        conn = from app import app, DB_PATH, get_db_connection
        cursor = conn.cursor()
        cursor.execute("SELECT balance, upi_id FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row or row[0] <= 0:
            bot.send_message(message.chat.id, "⚠️ Insufficient balance.")
            conn.close()
            return
        if not row[1]:
            bot.send_message(message.chat.id, "⚠️ Add UPI ID first using '🏦 Add UPI'.")
            conn.close()
            return

        amount, upi_id = row[0], row[1]
        cursor.execute("INSERT INTO withdrawals (user_id, upi_id, amount, status) VALUES (?, ?, ?, 'Pending')", (user_id, upi_id, amount))
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        withdraw_notice = (
            f"✅ <b>Withdrawal Request Submitted!</b>\n\n"
            f"💰 <b>Amount:</b> ₹{amount}\n"
            f"💳 <b>UPI:</b> <code>{upi_id}</code>\n\n"
            "📌 <b>Note:</b> Payment will be approved in 24 to 48 hours."
        )
        bot.send_message(message.chat.id, withdraw_notice, parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

@bot.message_handler(func=lambda message: message.text == "💰 Balance")
def balance(message):
    conn = from app import app, DB_PATH, get_db_connection
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    bot.send_message(message.chat.id, f"💰 Balance: ₹{row[0] if row else 0}")

@bot.message_handler(func=lambda message: message.text == "📁 My Accounts")
def my_accounts(message):
    user_id = message.from_user.id
    conn = from app import app, DB_PATH, get_db_connection
    cursor = conn.cursor()
    
    # Fetch all tasks submitted by user
    cursor.execute("SELECT id, assigned_email, status FROM tasks WHERE user_id = ? AND screenshot_id IS NOT NULL AND screenshot_id != '' ORDER BY id DESC", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        bot.send_message(message.chat.id, "📁 <b>My Accounts History</b>\n\nNo accounts submitted yet.", parse_mode="HTML")
        return

    approved_cnt = sum(1 for t in tasks if t[2] == 'Approved')
    rejected_cnt = sum(1 for t in tasks if t[2] == 'Rejected')
    pending_cnt = sum(1 for t in tasks if t[2] == 'Pending')

    msg = (
        f"📁 <b>My Submitted Accounts Summary</b>\n"
        f"🟢 Approved: <b>{approved_cnt}</b> | 🔴 Rejected: <b>{rejected_cnt}</b> | 🟡 Pending: <b>{pending_cnt}</b>\n"
        "――――――――――――――――\n\n"
    )
    
    for t in tasks[:15]: # Shows latest 15 tasks
        t_id, email, status = t[0], t[1], t[2]
        if status == 'Approved':
            icon = "🟢 Approved (+₹10)"
        elif status == 'Rejected':
            icon = "🔴 Rejected"
        else:
            icon = "🟡 Pending Verification"
            
        msg += f"🆔 <b>#Task {t_id}</b>\n📧 <code>{email}</code>\nStatus: <b>{icon}</b>\n\n"

    bot.send_message(message.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "🎁 Rewards")
def rewards_info(message):
    bot.send_message(message.chat.id, "🎁 Reward: ₹10 per Gmail account.", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "💬 Help")
def help_msg(message):
    bot.send_message(message.chat.id, f"💬 Support: {HELP_USERNAME}")

def start_bot_polling():
    while True:
        try:
            bot.polling(none_stop=True, timeout=30)
        except Exception as e:
            print("Bot Polling Error, retrying...", e)
            time.sleep(5)

bot_thread = Thread(target=start_bot_polling)
bot_thread.daemon = True
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
