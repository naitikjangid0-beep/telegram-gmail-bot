import os
import csv
import io
import time
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, render_template_string, request, redirect, url_for, Response

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8880017395:AAEaRXzwxC3jPmy9HASJiRH-4n5A2o7xgWg")
FIREBASE_URL = "https://botpanel99-default-rtdb.firebaseio.com/"

# Firebase Initialization
if not firebase_admin._apps:
    cred_path = "secret_key.json"
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
    else:
        print("⚠️ Warning: secret_key.json not found! Ensure Firebase is configured.")

def send_telegram_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print("Telegram Send Error:", e)

def broadcast_to_all(text):
    try:
        users_ref = db.reference('users').get() or {}
        for u_id in users_ref.keys():
            send_telegram_msg(u_id, text)
    except Exception as e:
        print("Broadcast Error:", e)

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
        body { background-color: #f4f6f9; font-family: 'Segoe UI', system-ui, sans-serif; }
        .card-stat { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
        .user-group-card { background: #ffffff; border-radius: 14px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; border-left: 5px solid #0d6efd; }
        .badge-pending { background-color: #fff3cd; color: #856404; font-weight: 600; padding: 5px 10px; border-radius: 6px; }
        .badge-approved { background-color: #d4edda; color: #155724; font-weight: 600; padding: 5px 10px; border-radius: 6px; }
        .badge-rejected { background-color: #f8d7da; color: #721c24; font-weight: 600; padding: 5px 10px; border-radius: 6px; }
        .action-btn { padding: 4px 10px; font-size: 0.82rem; border-radius: 6px; font-weight: 500; }
    </style>
</head>
<body class="p-3 p-md-4">
    <div class="container-fluid max-width-1400">
        <!-- HEADER -->
        <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-3 border-bottom gap-2">
            <div>
                <h2 class="fw-bold text-dark mb-0"><i class="bi bi-speedometer2 text-primary me-2"></i>Multi-Task Admin Dashboard</h2>
                <small class="text-muted">Firebase Cloud Realtime Management</small>
            </div>
            <div class="d-flex gap-2 align-items-center">
                <input type="text" id="searchInput" onkeyup="filterTables()" class="form-control form-control-sm" style="width: 240px;" placeholder="🔍 Search User ID, Username...">
                <a href="/download-csv" class="btn btn-sm btn-outline-dark fw-semibold shadow-sm"><i class="bi bi-file-earmark-spreadsheet me-1"></i>CSV Export</a>
            </div>
        </div>

        <!-- STATS CARDS -->
        <div class="row g-3 mb-4">
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-primary">
                    <div class="text-muted small fw-bold">TOTAL USERS</div>
                    <div class="fs-2 fw-bold text-dark mt-1">{{ total_users }}</div>
                </div>
            </div>
            <div class="col-6 col-lg-3">
                <div class="card card-stat bg-white p-3 border-start border-4 border-success">
                    <div class="text-muted small fw-bold">TOTAL SUBMISSIONS</div>
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

        <!-- USER WISE GROUPED TASKS SECTION -->
        <h4 class="fw-bold mb-3 text-dark"><i class="bi bi-people-fill text-primary me-2"></i>User Wise Grouped Submissions</h4>
        
        {% for u_id, u_data in grouped_users.items() %}
        <div class="user-group-card searchable-user-card">
            <div class="d-flex flex-wrap justify-content-between align-items-center border-bottom pb-2 mb-3">
                <div>
                    <h5 class="fw-bold text-dark mb-0">{{ u_data['info'].get('first_name') or 'User' }} 
                        <span class="text-primary fs-6">(@{{ u_data['info'].get('username') if u_data['info'].get('username') else 'no_username' }})</span>
                    </h5>
                    <small class="text-muted">User ID: <code>{{ u_id }}</code> | UPI: <b class="text-dark">{{ u_data['info'].get('upi_id') or 'Not Added' }}</b></small>
                </div>
                <div class="d-flex gap-2 align-items-center mt-2 mt-md-0">
                    <span class="badge bg-success fs-6">Balance: ₹{{ u_data['info'].get('balance', 0) }}</span>
                    <form action="/adjust-balance/{{ u_id }}" method="POST" class="d-flex gap-1 ms-2">
                        <input type="number" step="1" name="amount" class="form-control form-control-sm" style="width: 80px;" placeholder="±Amt" required>
                        <button type="submit" class="btn btn-sm btn-dark action-btn">Adjust</button>
                    </form>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Task ID</th>
                            <th>Email Submitted</th>
                            <th>Proof Screenshot</th>
                            <th>Status</th>
                            <th>Submitted At</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for task in u_data['tasks'] %}
                        <tr>
                            <td><b>#{{ task['id'] }}</b></td>
                            <td><code>{{ task['assigned_email'] }}</code></td>
                            <td>
                                {% if task.get('screenshot_id') %}
                                <button class="btn btn-sm btn-outline-primary action-btn" onclick="openPhotoModal('{{ task['screenshot_id'] }}')">
                                    <i class="bi bi-image me-1"></i>View Proof
                                </button>
                                {% else %}
                                <span class="text-muted small">No Proof</span>
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
                            <td><small class="text-muted">{{ task.get('submission_time') or 'Just now' }}</small></td>
                            <td>
                                {% if task['status'] == 'Pending' %}
                                <a href="/task-action/approve/{{ task['id'] }}/{{ u_id }}" class="btn btn-success action-btn"><i class="bi bi-check-lg"></i> Approve (+₹19)</a>
                                <a href="/task-action/reject/{{ task['id'] }}/{{ u_id }}" class="btn btn-danger action-btn"><i class="bi bi-x-lg"></i> Reject</a>
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
        {% else %}
        <div class="alert alert-secondary">No submissions recorded yet.</div>
        {% endfor %}

        <!-- WITHDRAWAL REQUESTS SECTION -->
        <div class="card card-stat bg-white p-4 mb-4">
            <h5 class="fw-bold mb-3"><i class="bi bi-wallet2 text-success me-2"></i>Withdrawal & UPI Requests</h5>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Req ID</th>
                            <th>User ID</th>
                            <th>UPI Address</th>
                            <th>Requested Amount</th>
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
                            <td>
                                <span class="badge {{ 'badge-approved' if w['status'] == 'Paid' else 'badge-pending' }}">{{ w['status'] }}</span>
                            </td>
                            <td>
                                {% if w['status'] == 'Pending' %}
                                <a href="/payout/pay/{{ w['id'] }}/{{ w['user_id'] }}/{{ w['amount'] }}" class="btn btn-primary action-btn"><i class="bi bi-send me-1"></i>Mark Paid & Broadcast</a>
                                {% else %}
                                <span class="text-muted small">Paid</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="6" class="text-center text-muted">No withdrawal requests right now.</td></tr>
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
                    <h5 class="modal-title fw-bold">Submitted Proof</h5>
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
            var cards = document.getElementsByClassName("searchable-user-card");

            for (var i = 0; i < cards.length; i++) {
                var text = cards[i].textContent || cards[i].innerText;
                if (text.toLowerCase().indexOf(filter) > -1) {
                    cards[i].style.display = "";
                } else {
                    cards[i].style.display = "none";
                }
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    users_data = db.reference('users').get() or {}
    tasks_data = db.reference('tasks').get() or {}
    withdrawals_data = db.reference('withdrawals').get() or {}

    tasks_list = []
    for tid, tval in tasks_data.items():
        if tval and tval.get('screenshot_id'):
            tasks_list.append(tval)
    tasks_list.sort(key=lambda x: str(x.get('submission_time', '')), reverse=True)

    withdrawals = list(withdrawals_data.values()) if isinstance(withdrawals_data, dict) else []
    withdrawals.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)

    grouped_users = {}
    for uid, uinfo in users_data.items():
        u_tasks = [t for t in tasks_list if str(t.get('user_id')) == str(uid)]
        if u_tasks:
            grouped_users[uid] = {
                'info': uinfo,
                'tasks': u_tasks
            }

    total_users = len(users_data)
    total_submissions = len(tasks_list)
    pending_count = sum(1 for t in tasks_list if t.get('status') == 'Pending')
    pending_withdraws = sum(1 for w in withdrawals if w.get('status') == 'Pending')

    return render_template_string(HTML_TEMPLATE, grouped_users=grouped_users, withdrawals=withdrawals, 
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

@app.route('/task-action/<type>/<task_id>/<user_id>')
def handle_task_action(type, task_id, user_id):
    if type == 'approve':
        db.reference(f"tasks/{task_id}").update({'status': 'Approved'})
        u_ref = db.reference(f"users/{user_id}")
        u_data = u_ref.get() or {}
        
        new_balance = float(u_data.get('balance', 0)) + 19
        new_tasks = int(u_data.get('tasks_done', 0)) + 1
        
        u_ref.update({
            'balance': new_balance,
            'tasks_done': new_tasks
        })
        send_telegram_msg(user_id, "🎉 <b>Task Approved!</b>\nYour Gmail task was verified. <b>₹19</b> added to your balance!")
    elif type == 'reject':
        db.reference(f"tasks/{task_id}").update({'status': 'Rejected'})
        send_telegram_msg(user_id, "❌ <b>Task Rejected!</b>\nYour submitted task was rejected.")
        
    return redirect(url_for('index'))

@app.route('/adjust-balance/<user_id>', methods=['POST'])
def adjust_balance(user_id):
    amount = request.form.get('amount')
    if amount:
        try:
            amt = float(amount)
            u_ref = db.reference(f"users/{user_id}")
            u_data = u_ref.get() or {}
            curr_bal = float(u_data.get('balance', 0))
            u_ref.update({'balance': curr_bal + amt})
            send_telegram_msg(user_id, f"💳 <b>Balance Adjusted!</b>\nYour balance updated by <b>₹{amt}</b>.")
        except Exception as e:
            print(e)
    return redirect(url_for('index'))

@app.route('/payout/pay/<w_id>/<user_id>/<float:amount>')
def handle_payout(w_id, user_id, amount):
    db.reference(f"withdrawals/{w_id}").update({'status': 'Paid'})
    
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
    tasks_data = db.reference('tasks').get() or {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Task ID', 'User ID', 'Email', 'Status', 'Time'])
    
    for tid, t in tasks_data.items():
        if t and t.get('screenshot_id'):
            writer.writerow([t.get('id'), t.get('user_id'), t.get('assigned_email'), t.get('status'), t.get('submission_time')])
        
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=tasks_history.csv"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
