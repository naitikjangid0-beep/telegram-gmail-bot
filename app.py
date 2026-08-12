import threading
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database table auto-create karne ke liye
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            tasks_done INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def dashboard():
    try:
        conn = get_db()
        users = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
    except Exception as e:
        users = []
    return render_template('dashboard.html', users=users)

@app.route('/approve/<int:user_id>')
def approve_task(user_id):
    conn = get_db()
    conn.execute('UPDATE users SET balance = balance + 10, tasks_done = tasks_done + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# Background Thread mein Telegram Bot ko run karne ke liye
def run_bot():
    try:
        import bot
    except Exception as e:
        print("Bot start error:", e)

# Render Server start hote hi Bot chalu ho jayega
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
