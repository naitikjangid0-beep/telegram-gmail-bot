import sqlite3
import csv
import io
import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for, Response

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8880017395:AAEaRXzwxC3jPmy9HASJiRH-4n5A2o7xgWg")

# Safe Permanent Database Path for Render Disk or Fallback Local
PERSISTENT_DIR = "/var/data"
if not os.path.exists(PERSISTENT_DIR):
    try:
        os.makedirs(PERSISTENT_DIR, exist_ok=True)
    except Exception:
        PERSISTENT_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(PERSISTENT_DIR, 'database.db')

def send_telegram_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print("Telegram Send Error:", e)

def broadcast_to_all(text):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        users = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        for u in users:
            send_telegram_msg(u['user_id'], text)
    except Exception as e:
        print("Broadcast Error:", e)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_app_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            upi_id TEXT,
            balance REAL DEFAULT 0,
            tasks_done INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            assigned_email TEXT,
            screenshot_id TEXT,
            status TEXT DEFAULT 'Pending',
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
        .card-stat { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
        .table-card { background: #ffffff; border-radius: 14px; padding: 24px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); margin-bottom: 30px; }
        .badge-pending { background-color: #fff3cd; color: #856404; font-weight: 600; padding: 6px 12px; border-radius: 6px; }
        .badge-approved { background-color: #d4edda; color: #155724; font-weight: 600; padding: 6px 12px; border-radius: 6px; }
        .badge-rejected { background-color: #f8d7da; color: #721c24; font-weight: 600; padding: 6px 12px; border-radius: 6px; }
        .action-btn { padding: 4px 10px; font-size: 0.82rem; border-radius: 6px; font-weight: 500; }
    </style>
</head>
<body class="p-3 p-md-4">
    <div class="container-fluid max-width-1400">
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-3 border-bottom gap-2">
            <div>
                <h2 class="fw-bold text-dark mb-0"><i class="bi bi-speedometer2 text-primary me-2"></i>Multi-Task Admin Panel</h2>
                <small class="text-muted">Live Screenshot Sync & Search Panel</small>
            </div>
            <div class="d-flex gap-2 align-items-center">
                <input type="text" id="searchInput" onkeyup="filterTables()" class="form-control form-control-sm" style="width: 240px;" placeholder="🔍 Search Name, @Username, ID...">
                <a href="/download-csv" class="btn btn-sm btn-outline-dark fw-semibold shadow-sm"><i class="bi bi-file-earmark-spreadsheet me-1"></i>CSV Export</a>
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-primary">
                    <div class="text-muted small fw-bold">TOTAL REGISTERED USERS</div>
                    <div class="fs-2 fw-bold text-dark mt-1">{{ total_users }}</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-success">
                    <div class="text-muted small fw-bold">SUBMITTED TASKS</div>
                    <div class="fs-2 fw-bold text-success mt-1">{{ total_submissions }}</div>
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

        <!-- TASKS TABLE -->
        <div class="table-card">
            <h5 class="fw-bold mb-3"><i class="bi bi-card-image text-primary me-2"></i>Submitted Tasks (With Screenshots)</h5>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0 searchable-table">
                    <thead class="table-light">
                        <tr>
                            <th>Task ID</th>
                            <th>User Details & Username</th>
                            <th>Submitted Email</th>
                            <th>Proof Screenshot</th>
                            <th>Status</th>
                            <th>Submitted At</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for task in tasks %}
                        <tr>
                            <td><b>#{{ task['id'] }}</b></td>
                            <td>
                                <div class="fw-bold">{{ task['first_name'] or 'User' }}</div>
                                <div><small class="text-primary fw-semibold">@{{ task['username'] if task['username'] else 'no_username' }}</small></div>
                                <code>{{ task['user_id'] }}</code>
                            </td>
                            <td><code>{{ task['assigned_email'] }}</code></td>
                            <td>
                                {% if task['screenshot_id'] %}
                                <button class="btn btn-sm btn-outline-primary action-btn" onclick="openPhotoModal('{{ task['screenshot_id'] }}')">
                                    <i class="bi bi-image me-1"></i>View Proof
                                </button>
                                {% else %}
                                <span class="text-muted small">No SS</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if task['status'] == 'Approved' %}
                                    <span class="badge-approved">Approved</span>
                                {% elif task['status'] == 'Rejected' %}
                                    <span class="badge-rejected">Rejected</span>
                                {% else %}
                                    <span class="badge-pending">Pending</span>
                                {% endif %}
                            </td>
                            <td><small class="text-muted">{{ task['submission_time'] or 'Just now' }}</small></td>
                            <td>
                                {% if task['status'] == 'Pending' %}
                                <a href="/task-action/approve/{{ task['id'] }}/{{ task['user_id'] }}" class="btn btn-success action-btn"><i class="bi bi-check-lg"></i> Approve (+₹10)</a>
                                <a href="/task-action/reject/{{ task['id'] }}/{{ task['user_id'] }}" class="btn btn-danger action-btn"><i class="bi bi-x-lg"></i> Reject</a>
                                {% else %}
                                <span class="text-muted small">Completed</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- USERS & BALANCE TABLE -->
        <div class="table-card">
            <h5 class="fw-bold mb-3"><i class="bi bi-people-fill text-success me-2"></i>Registered Users & Balances</h5>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0 searchable-table">
                    <thead class="table-light">
                        <tr>
                            <th>User ID</th>
                            <th>Name & Username</th>
                            <th>UPI ID</th>
                            <th>Approved Tasks</th>
                            <th>Balance</th>
                            <th>Adjust Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in users %}
                        <tr>
                            <td><code>{{ u['user_id'] }}</code></td>
                            <td>
                                <b>{{ u['first_name'] or 'User' }}</b><br>
                                <small class="text-primary fw-semibold">@{{ u['username'] if u['username'] else 'no_username' }}</small>
                            </td>
                            <td><span class="text-primary fw-semibold">{{ u['upi_id'] or 'Not Set' }}</span></td>
                            <td><span class="badge bg-light text-dark border">{{ u['tasks_done'] }}</span></td>
                            <td><span class="fw-bold text-success">₹{{ u['balance'] }}</span></td>
                            <td>
                                <form action="/adjust-balance/{{ u['user_id'] }}" method="POST" class="d-flex gap-1">
                                    <input type="number" step="1" name="amount" class="form-control form-control-sm px-1 py-0" style="width: 80px;" placeholder="±Amt" required>
                                    <button type="submit" class="btn btn-sm btn-dark px-2 py-0 action-btn">Set</button>
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
                <table class="table table-hover align-middle mb-0 searchable-table">
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
                            <td><b class="text-primary">{{ w['upi_id'] }}</b></td>
                            <td><span class="fw-bold text-success">₹{{ w['amount'] }}</span></td>
                            <td><span class="badge {{ 'badge-approved' if w['status'] == 'Paid' else 'badge-pending' }}">{{ w['status'] }}</span></td>
                            <td>
                                {% if w['status'] == 'Pending' %}
                                <a href="/payout/pay/{{ w['id'] }}/{{ w['user_id'] }}/{{ w['amount'] }}" class="btn btn-primary action-btn"><i class="bi bi-send me-1"></i>Mark Paid & Broadcast</a>
                                {% else %}
                                <span class="text-muted small">Paid & Broadcasted</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- SCREENSHOT MODAL -->
    <div class="modal fade" id="photoModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title fw-bold">Proof Screenshot</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center p-3">
                    <img id="modalImage" src="" class="img-fluid rounded border shadow-sm" style="max-height: 480px;">
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function openPhotoModal(fileId) {
            var modalImage = document.getElementById('modalImage');
            modalImage.src = "/get-telegram-photo/" + fileId;
            var myModal = new bootstrap.Modal(document.getElementById('photoModal'));
            myModal.show();
        }

        function filterTables() {
            var input = document.getElementById("searchInput");
            var filter = input.value.toLowerCase();
            var tables = document.getElementsByClassName("searchable-table");

            for (var t = 0; t < tables.length; t++) {
                var tr = tables[t].getElementsByTagName("tr");
                for (var i = 1; i < tr.length; i++) {
                    var text = tr[i].textContent || tr[i].innerText;
                    if (text.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY rowid DESC").fetchall()
    
    tasks = conn.execute("""
        SELECT tasks.*, users.first_name, users.username 
        FROM tasks 
        LEFT JOIN users ON tasks.user_id = users.user_id 
        WHERE tasks.screenshot_id IS NOT NULL AND tasks.screenshot_id != '' 
        ORDER BY tasks.id DESC
    """).fetchall()
    
    withdrawals = conn.execute("SELECT * FROM withdrawals ORDER BY id DESC").fetchall()
    
    total_users = len(users)
    total_submissions = len(tasks)
    pending_count = sum(1 for t in tasks if t['status'] == 'Pending')
    pending_withdraws = sum(1 for w in withdrawals if w['status'] == 'Pending')
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, users=users, tasks=tasks, withdrawals=withdrawals, 
                                  total_users=total_users, total_submissions=total_submissions,
                                  pending_count=pending_count, pending_withdraws=pending_withdraws)

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

@app.route('/task-action/<type>/<int:task_id>/<int:user_id>')
def handle_task_action(type, task_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if type == 'approve':
        cursor.execute("UPDATE tasks SET status = 'Approved' WHERE id = ?", (task_id,))
        cursor.execute("UPDATE users SET balance = balance + 10, tasks_done = tasks_done + 1 WHERE user_id = ?", (user_id,))
        send_telegram_msg(user_id, "🎉 <b>Task Approved!</b>\nYour Gmail task was verified. <b>₹10</b> added to your balance!")
    elif type == 'reject':
        cursor.execute("UPDATE tasks SET status = 'Rejected' WHERE id = ?", (task_id,))
        send_telegram_msg(user_id, "❌ <b>Task Rejected!</b>\nYour submitted task was rejected.")
        
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
            send_telegram_msg(user_id, f"💳 <b>Balance Adjusted!</b>\nYour balance updated by <b>₹{amt}</b>.")
        except Exception as e:
            print(e)
    return redirect(url_for('index'))

@app.route('/payout/pay/<int:w_id>/<int:user_id>/<float:amount>')
def handle_payout(w_id, user_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE withdrawals SET status = 'Paid' WHERE id = ?", (w_id,))
    conn.commit()
    conn.close()
    
    send_telegram_msg(user_id, f"✅ <b>Payout Successful!</b>\nYour withdrawal request for <b>₹{amount}</b> has been processed via UPI!")
    
    masked_user = str(user_id)[:4] + "****"
    public_notice = (
        "🥳 <b>NEW SUCCESSFUL WITHDRAWAL!</b> 🥳\n\n"
        f"👤 <b>User ID:</b> <code>{masked_user}</code>\n"
        f"💸 <b>Amount Paid:</b> <b>₹{amount}</b>\n"
        "💳 <b>Status:</b> Payment Sent via UPI Successfully!\n\n"
        "🚀 <i>Keep creating accounts & earning daily!</i>"
    )
    broadcast_to_all(public_notice)
    
    return redirect(url_for('index'))

@app.route('/download-csv')
def download_csv():
    conn = get_db_connection()
    tasks = conn.execute("SELECT id, user_id, assigned_email, status, submission_time FROM tasks WHERE screenshot_id IS NOT NULL").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Task ID', 'User ID', 'Email', 'Status', 'Time'])
    for t in tasks:
        writer.writerow([t['id'], t['user_id'], t['assigned_email'], t['status'], t['submission_time']])
        
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=tasks_history.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
