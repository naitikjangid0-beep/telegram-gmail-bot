import sqlite3
import csv
import io
import requests
from flask import Flask, render_template_string, request, redirect, url_for, Response

app = Flask(__name__)

# Config - Apne Bot ka Token Yahan Rehna Chahiye
BOT_TOKEN = "7724217112:AAG-x..."  # Note: Isko apne real BOT_TOKEN se verify kar lena

def send_telegram_msg(chat_id, text):
    """Utility to send telegram notification to user from dashboard"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Send Error:", e)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            balance REAL DEFAULT 0,
            tasks_done INTEGER DEFAULT 0,
            assigned_email TEXT,
            status TEXT DEFAULT 'Pending'
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
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Advanced Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .card-stat { border-radius: 12px; border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        .table-responsive { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        .badge-pending { background-color: #ffc107; color: #000; }
        .badge-approved { background-color: #198754; color: #fff; }
        .badge-rejected { background-color: #dc3545; color: #fff; }
    </style>
</head>
<body class="p-3 p-md-4">
    <div class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>🚀 Advanced Control Panel</h2>
            <a href="/download-csv" class="btn btn-dark">📥 Download All Data (Excel/CSV)</a>
        </div>

        <!-- STATS CARDS -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card card-stat bg-primary text-white p-3">
                    <h6>Total Users</h6>
                    <h3 class="m-0">{{ total_users }}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat bg-success text-white p-3">
                    <h6>Total Tasks Submitted</h6>
                    <h3 class="m-0">{{ total_tasks }}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat bg-warning text-dark p-3">
                    <h6>Pending Approvals</h6>
                    <h3 class="m-0">{{ pending_count }}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat bg-info text-white p-3">
                    <h6>Pending Withdrawals</h6>
                    <h3 class="m-0">{{ pending_withdraws }}</h3>
                </div>
            </div>
        </div>

        <!-- BROADCAST SECTION -->
        <div class="card p-3 mb-4 border-0 shadow-sm">
            <h5>📢 Send Broadcast Message to All Users</h5>
            <form action="/broadcast" method="POST" class="d-flex gap-2">
                <input type="text" name="message" class="form-control" placeholder="Type notice for all users..." required>
                <button type="submit" class="btn btn-warning fw-bold text-nowrap">Send Notice</button>
            </form>
        </div>

        <!-- SEARCH & USER TABLE -->
        <div class="table-responsive mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h4>📋 User Submissions</h4>
                <form method="GET" action="/" class="d-flex gap-2">
                    <input type="text" name="search" class="form-control" placeholder="Search by ID, Name, Email" value="{{ search_query }}">
                    <button type="submit" class="btn btn-secondary">Search</button>
                </form>
            </div>
            <table class="table table-hover align-middle">
                <thead class="table-light">
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Username</th>
                        <th>Assigned Email</th>
                        <th>Tasks</th>
                        <th>Balance</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td><code>{{ user['user_id'] }}</code></td>
                        <td><b>{{ user['first_name'] }}</b></td>
                        <td>{{ '@' + user['username'] if user['username'] else 'N/A' }}</td>
                        <td><code>{{ user['assigned_email'] or 'Not Assigned' }}</code></td>
                        <td>{{ user['tasks_done'] }}</td>
                        <td>₹{{ user['balance'] }}</td>
                        <td>
                            {% if user['status'] == 'Approved' %}
                                <span class="badge badge-approved">Approved</span>
                            {% elif user['status'] == 'Rejected' %}
                                <span class="badge badge-rejected">Rejected</span>
                            {% else %}
                                <span class="badge badge-pending">Pending</span>
                            {% endif %}
                        </td>
                        <td>
                            <a href="/action/approve/{{ user['user_id'] }}" class="btn btn-sm btn-success">✅ Approve (+₹10)</a>
                            <a href="/action/reject/{{ user['user_id'] }}" class="btn btn-sm btn-danger">❌ Reject</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- WITHDRAWAL REQUESTS TABLE -->
        <div class="table-responsive">
            <h4 class="mb-3">💸 Withdrawal Requests</h4>
            <table class="table table-hover align-middle">
                <thead class="table-light">
                    <tr>
                        <th>ID</th>
                        <th>User ID</th>
                        <th>UPI ID</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for w in withdrawals %}
                    <tr>
                        <td>#{{ w['id'] }}</td>
                        <td><code>{{ w['user_id'] }}</code></td>
                        <td><b>{{ w['upi_id'] }}</b></td>
                        <td>₹{{ w['amount'] }}</td>
                        <td>
                            <span class="badge {{ 'badge-approved' if w['status'] == 'Paid' else 'badge-pending' }}">
                                {{ w['status'] }}
                            </span>
                        </td>
                        <td>
                            {% if w['status'] == 'Pending' %}
                            <a href="/payout/pay/{{ w['id'] }}/{{ w['user_id'] }}/{{ w['amount'] }}" class="btn btn-sm btn-primary">Mark Paid</a>
                            {% else %}
                            <span class="text-muted">Completed</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    search = request.args.get('search', '').lower()
    conn = get_db_connection()
    
    if search:
        users = conn.execute("SELECT * FROM users WHERE LOWER(first_name) LIKE ? OR LOWER(assigned_email) LIKE ? OR CAST(user_id AS TEXT) LIKE ?", 
                             (f'%{search}%', f'%{search}%', f'%{search}%')).fetchall()
    else:
        users = conn.execute("SELECT * FROM users ORDER BY rowid DESC").fetchall()

    withdrawals = conn.execute("SELECT * FROM withdrawals ORDER BY id DESC").fetchall()
    
    total_users = len(users)
    total_tasks = sum(u['tasks_done'] for u in users if u['tasks_done'])
    pending_count = sum(1 for u in users if u['status'] == 'Pending' or not u['status'])
    pending_withdraws = sum(1 for w in withdrawals if w['status'] == 'Pending')
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, users=users, withdrawals=withdrawals, 
                                  total_users=total_users, total_tasks=total_tasks, 
                                  pending_count=pending_count, pending_withdraws=pending_withdraws, search_query=search)

@app.route('/action/<type>/<int:user_id>')
def handle_action(type, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if type == 'approve':
        cursor.execute("UPDATE users SET balance = balance + 10, tasks_done = tasks_done + 1, status = 'Approved' WHERE user_id = ?", (user_id,))
        send_telegram_msg(user_id, "🎉 <b>Task Approved!</b>\nYour submitted Gmail account was verified. <b>₹10</b> has been added to your balance!")
    elif type == 'reject':
        cursor.execute("UPDATE users SET status = 'Rejected' WHERE user_id = ?", (user_id,))
        send_telegram_msg(user_id, "❌ <b>Task Rejected!</b>\nYour submission was rejected by the admin. Please create account accurately.")
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/payout/pay/<int:w_id>/<int:user_id>/<float:amount>')
def handle_payout(w_id, user_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE withdrawals SET status = 'Paid' WHERE id = ?", (w_id,))
    conn.commit()
    conn.close()
    
    send_telegram_msg(user_id, f"✅ <b>Payout Successful!</b>\nYour withdrawal request for <b>₹{amount}</b> has been processed!")
    return redirect(url_for('index'))

@app.route('/broadcast', methods=['POST'])
def broadcast():
    msg = request.form.get('message')
    if msg:
        conn = get_db_connection()
        users = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        for u in users:
            send_telegram_msg(u['user_id'], f"📢 <b>ADMIN ANNOUNCEMENT:</b>\n\n{msg}")
    return redirect(url_for('index'))

@app.route('/download-csv')
def download_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    users = cursor.execute("SELECT user_id, first_name, username, assigned_email, tasks_done, balance, status FROM users").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'First Name', 'Username', 'Assigned Email', 'Tasks Done', 'Balance (INR)', 'Status'])
    for u in users:
        writer.writerow([u['user_id'], u['first_name'], u['username'], u['assigned_email'], u['tasks_done'], u['balance'], u['status']])
        
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=gmail_bot_users.csv"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
