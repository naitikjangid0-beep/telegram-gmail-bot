import sqlite3
import csv
import io
import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for, Response

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8880017395:AAEaRXzwxC3jPmy9HASJiRH-4n5A2o7xgWg")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def send_telegram_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print("Telegram Send Error:", e)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Database Initialization & Migration
def init_app_db():
    conn = get_db_connection()
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
            tasks_done INTEGER DEFAULT 0,
            last_screenshot_id TEXT,
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            upi_id TEXT,
            amount REAL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Auto-add missing columns safely
    columns = [
        ("last_screenshot_id", "TEXT"),
        ("submission_time", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("upi_id", "TEXT"),
        ("assigned_email", "TEXT"),
        ("status", "TEXT DEFAULT 'Pending'"),
        ("username", "TEXT")
    ]
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

init_app_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Enterprise Admin Control Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
        .navbar-brand { font-weight: 700; letter-spacing: 0.5px; }
        .card-stat { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); transition: transform 0.2s; }
        .card-stat:hover { transform: translateY(-2px); }
        .table-card { background: #ffffff; border-radius: 14px; padding: 24px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); margin-bottom: 30px; }
        .badge-pending { background-color: #fff3cd; color: #856404; font-weight: 600; padding: 6px 12px; border-radius: 6px; }
        .badge-approved { background-color: #d4edda; color: #155724; font-weight: 600; padding: 6px 12px; border-radius: 6px; }
        .badge-rejected { background-color: #f8d7da; color: #721c24; font-weight: 600; padding: 6px 12px; border-radius: 6px; }
        .ss-thumb { width: 48px; height: 48px; object-fit: cover; border-radius: 8px; cursor: pointer; border: 2px solid #e9ecef; transition: all 0.2s; }
        .ss-thumb:hover { border-color: #0d6efd; transform: scale(1.05); }
        .action-btn { padding: 4px 10px; font-size: 0.82rem; border-radius: 6px; font-weight: 500; }
    </style>
</head>
<body class="p-3 p-md-4">
    <div class="container-fluid max-width-1400">
        <!-- HEADER -->
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-3 border-bottom">
            <div>
                <h2 class="navbar-brand fs-3 text-dark mb-0"><i class="bi bi-speedometer2 text-primary me-2"></i>Admin Dashboard Pro</h2>
                <small class="text-muted">Real-time Telegram Bot & Task Verification Management</small>
            </div>
            <div class="mt-2 mt-md-0">
                <a href="/download-csv" class="btn btn-outline-dark fw-semibold shadow-sm"><i class="bi bi-file-earmark-spreadsheet me-2"></i>Export CSV Data</a>
            </div>
        </div>

        <!-- STATS METRICS -->
        <div class="row g-3 mb-4">
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-primary">
                    <div class="text-muted small fw-bold">TOTAL USERS</div>
                    <div class="fs-2 fw-bold text-dark mt-1">{{ total_users }}</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-success">
                    <div class="text-muted small fw-bold">APPROVED TASKS</div>
                    <div class="fs-2 fw-bold text-success mt-1">{{ total_tasks }}</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-warning">
                    <div class="text-muted small fw-bold">PENDING APPROVALS</div>
                    <div class="fs-2 fw-bold text-warning mt-1">{{ pending_count }}</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-info">
                    <div class="text-muted small fw-bold">PENDING PAYOUTS</div>
                    <div class="fs-2 fw-bold text-info mt-1">{{ pending_withdraws }}</div>
                </div>
            </div>
        </div>

        <!-- BROADCAST / ANNOUNCEMENT SECTION -->
        <div class="card border-0 shadow-sm rounded-3 p-3 mb-4 bg-white">
            <h6 class="fw-bold text-secondary mb-2"><i class="bi bi-megaphone-fill me-2 text-warning"></i>Broadcast Notification</h6>
            <form action="/broadcast" method="POST" class="row g-2">
                <div class="col-md-10">
                    <input type="text" name="message" class="form-control" placeholder="Type message to broadcast to all registered Telegram users..." required>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-warning w-100 fw-bold"><i class="bi bi-send me-1"></i> Send Notice</button>
                </div>
            </form>
        </div>

        <!-- USER SUBMISSIONS & SCREENSHOT VERIFICATION TABLE -->
        <div class="table-card">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                <h5 class="fw-bold m-0"><i class="bi bi-people-fill text-primary me-2"></i>User Submissions & Proof Screenshots</h5>
                <form method="GET" action="/" class="d-flex gap-2 col-md-4">
                    <input type="text" name="search" class="form-control form-control-sm" placeholder="Search ID, Name, Email, UPI..." value="{{ search_query }}">
                    <button type="submit" class="btn btn-sm btn-secondary"><i class="bi bi-search"></i></button>
                </form>
            </div>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>User ID</th>
                            <th>Name / Username</th>
                            <th>Assigned Gmail</th>
                            <th>Screenshot Proof</th>
                            <th>UPI ID</th>
                            <th>Tasks</th>
                            <th>Balance</th>
                            <th>Status</th>
                            <th>Action / Balance Adjust</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td><code>{{ user['user_id'] }}</code></td>
                            <td>
                                <div class="fw-bold">{{ user['first_name'] or 'N/A' }}</div>
                                <small class="text-muted">{{ '@' + user['username'] if user['username'] and user['username'] != 'N/A' else 'No username' }}</small>
                            </td>
                            <td><code>{{ user['assigned_email'] or 'None Assigned' }}</code></td>
                            <td>
                                {% if user['last_screenshot_id'] %}
                                    <button class="btn btn-sm btn-outline-primary action-btn" onclick="openPhotoModal('{{ user['last_screenshot_id'] }}', '{{ user['user_id'] }}')">
                                        <i class="bi bi-image me-1"></i>View Proof
                                    </button>
                                {% else %}
                                    <span class="text-muted small">No Proof Sent</span>
                                {% endif %}
                            </td>
                            <td><span class="fw-semibold text-primary">{{ user['upi_id'] or 'Not Set' }}</span></td>
                            <td><span class="badge bg-light text-dark border">{{ user['tasks_done'] or 0 }}</span></td>
                            <td><span class="fw-bold text-success">₹{{ user['balance'] or 0 }}</span></td>
                            <td>
                                {% if user['status'] == 'Approved' %}
                                    <span class="badge-approved">Approved</span>
                                {% elif user['status'] == 'Rejected' %}
                                    <span class="badge-rejected">Rejected</span>
                                {% else %}
                                    <span class="badge-pending">Pending</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="d-flex gap-1 mb-1">
                                    <a href="/action/approve/{{ user['user_id'] }}" class="btn btn-success action-btn"><i class="bi bi-check-lg"></i> Approve (+₹10)</a>
                                    <a href="/action/reject/{{ user['user_id'] }}" class="btn btn-danger action-btn"><i class="bi bi-x-lg"></i> Reject</a>
                                </div>
                                <form action="/adjust-balance/{{ user['user_id'] }}" method="POST" class="d-flex gap-1">
                                    <input type="number" step="1" name="amount" class="form-control form-control-sm px-1 py-0" style="width: 70px;" placeholder="±Amt" required>
                                    <button type="submit" class="btn btn-sm btn-dark px-2 py-0 action-btn">Set Bal</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- WITHDRAWAL REQUESTS TABLE -->
        <div class="table-card">
            <h5 class="fw-bold mb-3"><i class="bi bi-wallet2 text-success me-2"></i>Withdrawal Requests Management</h5>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Request ID</th>
                            <th>User ID</th>
                            <th>UPI ID</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Timestamp</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for w in withdrawals %}
                        <tr>
                            <td>#{{ w['id'] }}</td>
                            <td><code>{{ w['user_id'] }}</code></td>
                            <td><b class="text-primary">{{ w['upi_id'] }}</b></td>
                            <td><span class="fw-bold text-success">₹{{ w['amount'] }}</span></td>
                            <td>
                                <span class="badge {{ 'badge-approved' if w['status'] == 'Paid' else 'badge-pending' }}">
                                    {{ w['status'] }}
                                </span>
                            </td>
                            <td><small class="text-muted">{{ w['created_at'] or 'N/A' }}</small></td>
                            <td>
                                {% if w['status'] == 'Pending' %}
                                <a href="/payout/pay/{{ w['id'] }}/{{ w['user_id'] }}/{{ w['amount'] }}" class="btn btn-primary action-btn"><i class="bi bi-check-circle me-1"></i>Mark Paid</a>
                                {% else %}
                                <span class="text-muted small fw-semibold"><i class="bi bi-check-all text-success"></i> Completed</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- SCREENSHOT MODAL VIEWER -->
    <div class="modal fade" id="photoModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title fw-bold">Screenshot Proof Verification</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body text-center p-3">
                    <img id="modalImage" src="" class="img-fluid rounded border shadow-sm" alt="Telegram Proof Image" style="max-height: 480px;">
                    <div id="modalFallback" class="p-4 text-muted border rounded mt-2 d-none">
                        <i class="bi bi-image-alt fs-1 d-block mb-2 text-primary"></i>
                        File ID: <code id="fileIdText"></code><br>
                        <small>Telegram File ID retrieved. Photo verified in admin chat.</small>
                    </div>
                </div>
                <div class="modal-footer justify-content-between">
                    <span id="modalUserId" class="small text-muted fw-bold"></span>
                    <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function openPhotoModal(fileId, userId) {
            document.getElementById('modalUserId').innerText = "User ID: " + userId;
            var modalImage = document.getElementById('modalImage');
            var modalFallback = document.getElementById('modalFallback');
            var fileIdText = document.getElementById('fileIdText');

            // Set file source directly via Telegram API link helper
            modalImage.src = "/get-telegram-photo/" + fileId;
            modalImage.onerror = function() {
                modalImage.classList.add('d-none');
                modalFallback.classList.remove('d-none');
                fileIdText.innerText = fileId;
            };
            modalImage.onload = function() {
                modalImage.classList.remove('d-none');
                modalFallback.classList.add('d-none');
            };

            var myModal = new bootstrap.Modal(document.getElementById('photoModal'));
            myModal.show();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    search = request.args.get('search', '').lower()
    conn = get_db_connection()
    
    if search:
        users = conn.execute("SELECT * FROM users WHERE LOWER(first_name) LIKE ? OR LOWER(assigned_email) LIKE ? OR LOWER(upi_id) LIKE ? OR CAST(user_id AS TEXT) LIKE ? ORDER BY submission_time DESC", 
                             (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%')).fetchall()
    else:
        users = conn.execute("SELECT * FROM users ORDER BY rowid DESC").fetchall()

    withdrawals = conn.execute("SELECT * FROM withdrawals ORDER BY id DESC").fetchall()
    
    total_users = len(users)
    total_tasks = sum(u['tasks_done'] for u in users if u['tasks_done'])
    pending_count = sum(1 for u in users if u['status'] == 'Pending' and u['assigned_email'])
    pending_withdraws = sum(1 for w in withdrawals if w['status'] == 'Pending')
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, users=users, withdrawals=withdrawals, 
                                  total_users=total_users, total_tasks=total_tasks, 
                                  pending_count=pending_count, pending_withdraws=pending_withdraws, search_query=search)

@app.route('/get-telegram-photo/<file_id>')
def get_telegram_photo(file_id):
    try:
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        if res.get("ok"):
            file_path = res["result"]["file_path"]
            img_res = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}")
            return Response(img_res.content, mimetype=img_res.headers.get('content-type', 'image/jpeg'))
    except Exception as e:
        print("Error fetching photo:", e)
    return "Image unavailable", 404

@app.route('/action/<type>/<int:user_id>')
def handle_action(type, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if type == 'approve':
        cursor.execute("UPDATE users SET balance = balance + 10, tasks_done = tasks_done + 1, status = 'Approved' WHERE user_id = ?", (user_id,))
        send_telegram_msg(user_id, "🎉 <b>Task Approved!</b>\nYour submitted Gmail account was verified. <b>₹10</b> has been added to your balance!")
    elif type == 'reject':
        cursor.execute("UPDATE users SET status = 'Rejected' WHERE user_id = ?", (user_id,))
        send_telegram_msg(user_id, "❌ <b>Task Rejected!</b>\nYour submission was rejected by the admin. Please ensure the account is created accurately.")
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/adjust-balance/<int:user_id>', methods=['POST'])
def adjust_balance(user_id):
    amount = request.form.get('amount')
    if amount:
        try:
            amt = float(amount)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, user_id))
            conn.commit()
            conn.close()
            send_telegram_msg(user_id, f"💳 <b>Balance Adjusted!</b>\nYour balance was updated by <b>₹{amt}</b> by the admin.")
        except Exception as e:
            print("Balance error:", e)
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
    users = cursor.execute("SELECT user_id, first_name, username, assigned_email, upi_id, tasks_done, balance, status FROM users").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'First Name', 'Username', 'Assigned Email', 'UPI ID', 'Tasks Done', 'Balance (INR)', 'Status'])
    for u in users:
        writer.writerow([u['user_id'], u['first_name'], u['username'], u['assigned_email'], u['upi_id'], u['tasks_done'], u['balance'], u['status']])
        
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=gmail_bot_users.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
