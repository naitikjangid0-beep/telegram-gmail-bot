import os
import random
import time
import telebot
import firebase_admin
from firebase_admin import credentials, db
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app import app, FIREBASE_URL

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
    rand_num = random.randint(10000, 99999)
    email = f"{f_name.lower()}{l_name.lower()}{rand_num}@gmail.com"
    reg_id = f"G{random.randint(10000000, 99999999)}"
    month = random.choice(MONTHS)
    day = random.randint(1, 28)
    year = random.randint(1995, 2006)
    return f_name, l_name, email, reg_id, month, day, year

def get_unique_task_details():
    try:
        tasks_data = db.reference("tasks").get() or {}
        used_emails = {
            t.get('assigned_email') 
            for t in tasks_data.values() 
            if isinstance(t, dict) and t.get('assigned_email')
        }
    except Exception:
        used_emails = set()

    for _ in range(50):
        f_name, l_name, email, reg_id, month, day, year = generate_task_details()
        if email not in used_emails:
            return f_name, l_name, email, reg_id, month, day, year

    f_name, l_name, _, reg_id, month, day, year = generate_task_details()
    email = f"{f_name.lower()}{l_name.lower()}{int(time.time())}@gmail.com"
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
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""

    try:
        u_ref = db.reference(f"users/{user_id}")
        u_data = u_ref.get() or {}
        u_ref.update({
            'first_name': first_name,
            'username': username,
            'upi_id': u_data.get('upi_id', ''),
            'balance': u_data.get('balance', 0),
            'tasks_done': u_data.get('tasks_done', 0)
        })
    except Exception as e:
        print("Firebase User Save Error:", e)

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
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or ""
    f_name, l_name, email, reg_id, month, day, year = get_unique_task_details()
    
    try:
        u_ref = db.reference(f"users/{user_id}")
        u_data = u_ref.get() or {}
        u_ref.update({
            'first_name': first_name,
            'username': username,
            'balance': u_data.get('balance', 0)
        })

        # Naya Task create karke push karenge Firebase mein (Multi-task fix)
        task_ref = db.reference("tasks").push()
        task_ref.set({
            'id': task_ref.key,
            'user_id': user_id,
            'assigned_email': email,
            'screenshot_id': '',
            'status': 'Pending',
            'submission_time': time.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        print("Firebase Task Save Error:", e)

    task_msg = (
        f"<b>New Task (Registration ID: {reg_id})</b>\n\n"
        "Complete Task and get paid for it.\n\n"
        "For each Task you will receive: 10₹\n"
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
    user_id = str(message.from_user.id)
    photo_id = message.photo[-1].file_id

    try:
        tasks_data = db.reference("tasks").get() or {}
        # User ka sabse aakhri pending task dhoondhkar update karenge
        user_tasks = [
            (tid, t) for tid, t in tasks_data.items() 
            if t and str(t.get('user_id')) == user_id and not t.get('screenshot_id')
        ]
        
        if user_tasks:
            target_task_id = user_tasks[-1][0]
            db.reference(f"tasks/{target_task_id}").update({
                'screenshot_id': photo_id,
                'submission_time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            # Fallback agar purana search na mile
            task_ref = db.reference("tasks").push()
            task_ref.set({
                'id': task_ref.key,
                'user_id': user_id,
                'assigned_email': 'Submitted Screenshot',
                'screenshot_id': photo_id,
                'status': 'Pending',
                'submission_time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
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
    try:
        if not message.text:
            bot.send_message(message.chat.id, "⚠️ Invalid UPI ID. Please try again.")
            return

        upi_id = message.text.strip()
        user_id = str(message.from_user.id)
        
        # Direct path set - Ye Firebase mein path missing hone par bhi auto-create kar deta hai
        db.reference(f"users/{user_id}/upi_id").set(upi_id)

        bot.send_message(message.chat.id, f"💳 UPI Saved: <code>{upi_id}</code>", parse_mode="HTML")
    except Exception as e:
        print("UPI Save Error:", e)
        bot.send_message(message.chat.id, f"⚠️ Error saving UPI: {e}")

@bot.message_handler(func=lambda message: message.text in ["🏧 Withdraw", "💰 Withdraw"])
def withdraw(message):
    user_id = str(message.from_user.id)
    try:
        u_data = db.reference(f"users/{user_id}").get() or {}
        bal = float(u_data.get('balance', 0))
        upi_id = u_data.get('upi_id', '')

        if bal <= 0:
            bot.send_message(message.chat.id, "⚠️ Insufficient balance.")
            return
        if not upi_id:
            bot.send_message(message.chat.id, "⚠️ Add UPI ID first using '🏦 Add UPI'.")
            return

        w_ref = db.reference("withdrawals").push()
        w_ref.set({
            'id': w_ref.key,
            'user_id': user_id,
            'upi_id': upi_id,
            'amount': bal,
            'status': 'Pending',
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S")
        })

        db.reference(f"users/{user_id}").update({'balance': 0})

        withdraw_notice = (
            f"✅ <b>Withdrawal Request Submitted!</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal}\n"
            f"💳 <b>UPI:</b> <code>{upi_id}</code>\n\n"
            "📌 <b>Note:</b> Payment will be approved in 24 to 48 hours."
        )
        bot.send_message(message.chat.id, withdraw_notice, parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

@bot.message_handler(func=lambda message: message.text == "💰 Balance")
def balance(message):
    user_id = str(message.from_user.id)
    u_data = db.reference(f"users/{user_id}").get() or {}
    bal = u_data.get('balance', 0)
    bot.send_message(message.chat.id, f"💰 Balance: ₹{bal}")

@bot.message_handler(func=lambda message: message.text == "📁 My Accounts")
def my_accounts(message):
    user_id = str(message.from_user.id)
    tasks_data = db.reference("tasks").get() or {}

    tasks = [
        t for t in tasks_data.values() 
        if t and str(t.get('user_id')) == user_id and t.get('screenshot_id')
    ]
    
    if not tasks:
        bot.send_message(message.chat.id, "📁 <b>My Accounts History</b>\n\nNo accounts submitted yet.", parse_mode="HTML")
        return

    approved_cnt = sum(1 for t in tasks if t.get('status') == 'Approved')
    rejected_cnt = sum(1 for t in tasks if t.get('status') == 'Rejected')
    pending_cnt = sum(1 for t in tasks if t.get('status') == 'Pending')

    msg = (
        f"📁 <b>My Submitted Accounts Summary</b>\n"
        f"🟢 Approved: <b>{approved_cnt}</b> | 🔴 Rejected: <b>{rejected_cnt}</b> | 🟡 Pending: <b>{pending_cnt}</b>\n"
        "――――――――――――――――\n\n"
    )
    
    tasks.sort(key=lambda x: str(x.get('submission_time', '')), reverse=True)
    
    for t in tasks[:15]:
        t_id = t.get('id', 'N/A')
        email = t.get('assigned_email', 'N/A')
        status = t.get('status', 'Pending')
        
        if status == 'Approved':
            icon = "🟢 Approved (+₹19)"
        elif status == 'Rejected':
            icon = "🔴 Rejected"
        else:
            icon = "🟡 Pending Verification"
            
        msg += f"🆔 <b>#Task {t_id}</b>\n📧 <code>{email}</code>\nStatus: <b>{icon}</b>\n\n"

    bot.send_message(message.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "🎁 Rewards")
def rewards_info(message):
    bot.send_message(message.chat.id, "🎁 Reward: ₹19 per Gmail account.", parse_mode="HTML")

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
