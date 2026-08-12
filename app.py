import sqlite3
import csv
import io
from flask import Flask, render_template_string, request, redirect, url_for, Response

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database setup / Auto-migration
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check & Add new columns dynamically if not exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'assigned_email' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN assigned_email TEXT")
    if 'status' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Pending'")
    if 'username' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        
    conn.commit()
    conn.close()

init_db()

# Main Dashboard UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Gmail Bot Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .card-stat { border-radius: 12px; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .table-responsive { background: #fff; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .badge-pending { background-color: #ffc107; color: #000; }
        .badge-approved { background-color: #198754; color: #fff; }
        .badge-rejected { background-color: #dc3545; color: #fff; }
    </style>
</head>
<body class="p-3 p-md-4">
    <div class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>🚀 Client Control Panel</h2>
            <a href="/download-csv" class="btn btn-dark">📥 Download All Data (Excel/CSV)</a>
        </div>

        <!-- STATS CARDS -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card card-stat bg-primary text-white p-3">
                    <h6 class="text-white-50">Total Registered Users</h6>
                    <h3 class="m-0">{{ total_users }}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat bg-success text-white p-3">
                    <h6 class="text-white-50">Total Tasks Submitted</h6>
                    <h3 class="m-0">{{ total_tasks }}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat bg-warning text-dark p-3">
                    <h6 class="text-dark-50">Pending Approvals</h6>
                    <h3 class="m-0">{{ pending_count }}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat bg-info text-white p-3">
                    <h6 class="text-white-50">Total Balance Paid</h6>
                    <h3 class="m-0">₹{{ total_balance }}</h3>
                </div>
            </div>
        </div>

        <!-- USERS & TASKS TABLE -->
        <div class="table-responsive">
            <h4 class="mb-3">📋 Task Submissions & User Management</h4>
            <table class="table table-hover align-middle">
                <thead class="table-light">
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Username</th>
                        <th>Assigned Email</th>
                        <th>Tasks Done</th>
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
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY rowid DESC").fetchall()
    
    total_users = len(users)
    total_tasks = sum(u['tasks_done'] for u in users if u['tasks_done'])
    total_balance = sum(u['balance'] for u in users if u['balance'])
    pending_count = sum(1 for u in users if u['status'] == 'Pending' or not u['status'])
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, users=users, total_users=total_users, 
                                  total_tasks=total_tasks, total_balance=total_balance, 
                                  pending_count=pending_count)

# Action Route (Approve / Reject)
@app.route('/action/<type>/<int:user_id>')
def handle_action(type, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if type == 'approve':
        cursor.execute("UPDATE users SET balance = balance + 10, tasks_done = tasks_done + 1, status = 'Approved' WHERE user_id = ?", (user_id,))
    elif type == 'reject':
        cursor.execute("UPDATE users SET status = 'Rejected' WHERE user_id = ?", (user_id,))
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Export CSV Route
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
