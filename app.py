import os
import urllib.parse
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_change_me")

# Database Connection Helper
def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'pending',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Initialize DB tables on startup
try:
    init_db()
except Exception as e:
    print(f"Database Init Error: {e}")

# HTML Template (Same Admin UI Dashboard)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .card { background: #007bff; color: white; padding: 15px; border-radius: 8px; flex: 1; text-align: center; }
        .card h3 { margin: 0; font-size: 2em; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #f8f9fa; }
        .btn { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; color: white; text-decoration: none; font-size: 14px; }
        .btn-approve { background: #28a745; }
        .btn-reject { background: #dc3545; }
        .btn-primary { background: #007bff; }
        .btn-danger { background: #d9534f; }
        .form-group { margin-bottom: 15px; }
        input[type="text"], input[type="password"], textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .flash { padding: 10px; background: #e7f3fe; border-left: 6px solid #2196F3; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        {% if not session.logged_in %}
            <h2>Admin Login</h2>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="flash">{{ messages[0] }}</div>
              {% endif %}
            {% endwith %}
            <form method="POST" action="/login">
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary">Login</button>
            </form>
        {% else %}
            <h1>Bot Admin Dashboard</h1>
            <a href="/logout" style="float: right; margin-top: -40px;" class="btn btn-danger">Logout</a>
            
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="flash">{{ messages[0] }}</div>
              {% endif %}
            {% endwith %}

            <div class="stats">
                <div class="card">
                    <h3>{{ total_users }}</h3>
                    <p>Total Users</p>
                </div>
                <div class="card" style="background: #28a745;">
                    <h3>{{ approved_users }}</h3>
                    <p>Approved Users</p>
                </div>
                <div class="card" style="background: #ffc107; color: #333;">
                    <h3>{{ pending_users }}</h3>
                    <p>Pending Users</p>
                </div>
            </div>

            <h2>User Approvals</h2>
            <table>
                <tr>
                    <th>User ID</th>
                    <th>Username</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
                {% for user in users %}
                <tr>
                    <td>{{ user.user_id }}</td>
                    <td>@{{ user.username if user.username else 'N/A' }}</td>
                    <td><strong>{{ user.status }}</strong></td>
                    <td>
                        {% if user.status != 'approved' %}
                            <a href="/action/approve/{{ user.user_id }}" class="btn btn-approve">Approve</a>
                        {% endif %}
                        {% if user.status != 'rejected' %}
                            <a href="/action/reject/{{ user.user_id }}" class="btn btn-reject">Reject</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>

            <h2 style="margin-top: 30px;">Generate Access Keys</h2>
            <form method="POST" action="/generate_key" style="display: flex; gap: 10px;">
                <input type="text" name="key_name" placeholder="Enter Key Name (e.g. KEY123)" required>
                <button type="submit" class="btn btn-primary">Add Key</button>
            </form>
            <ul style="margin-top: 10px;">
                {% for k in keys %}
                    <li><strong>{{ k.key }}</strong> (Created: {{ k.created_at }}) <a href="/delete_key/{{ k.key }}" style="color: red; margin-left: 10px;">Delete</a></li>
                {% endfor %}
            </ul>

            <h2 style="margin-top: 30px;">Broadcast Message</h2>
            <form method="POST" action="/broadcast">
                <div class="form-group">
                    <textarea name="message" rows="4" placeholder="Type message to broadcast to all approved users..." required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Send Broadcast</button>
            </form>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template_string(HTML_TEMPLATE)
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY registered_at DESC;")
    users = cur.fetchall()
    
    cur.execute("SELECT * FROM keys ORDER BY created_at DESC;")
    keys = cur.fetchall()
    
    total_users = len(users)
    approved_users = sum(1 for u in users if u['status'] == 'approved')
    pending_users = sum(1 for u in users if u['status'] == 'pending')
    
    cur.close()
    conn.close()
    
    return render_template_string(
        HTML_TEMPLATE,
        users=users,
        keys=keys,
        total_users=total_users,
        approved_users=approved_users,
        pending_users=pending_users
    )

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['logged_in'] = True
    else:
        flash("Invalid Password!")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/action/<string:action_type>/<int:user_id>')
def user_action(action_type, user_id):
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    new_status = 'approved' if action_type == 'approve' else 'rejected'
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status = %s WHERE user_id = %s;", (new_status, user_id))
    conn.commit()
    cur.close()
    conn.close()
    
    if TELEGRAM_BOT_TOKEN:
        msg = "✅ Your access request has been Approved! You can now use the bot." if new_status == 'approved' else "❌ Your access request was Rejected by admin."
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": user_id, "text": msg})
        except Exception as e:
            print(f"Error notifying user: {e}")

    flash(f"User {user_id} marked as {new_status}.")
    return redirect(url_for('index'))

@app.route('/generate_key', methods=['POST'])
def generate_key():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    key_name = request.form.get('key_name').strip()
    if key_name:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO keys (key) VALUES (%s);", (key_name,))
            conn.commit()
            flash(f"Key '{key_name}' added successfully.")
        except Exception as e:
            flash(f"Error adding key: {e}")
        finally:
            cur.close()
            conn.close()
            
    return redirect(url_for('index'))

@app.route('/delete_key/<string:key_name>')
def delete_key(key_name):
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM keys WHERE key = %s;", (key_name,))
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f"Key '{key_name}' deleted.")
    return redirect(url_for('index'))

@app.route('/broadcast', methods=['POST'])
def broadcast():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    message = request.form.get('message')
    if message and TELEGRAM_BOT_TOKEN:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE status = 'approved';")
        approved_users = cur.fetchall()
        cur.close()
        conn.close()
        
        count = 0
        for u in approved_users:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            try:
                res = requests.post(url, json={"chat_id": u['user_id'], "text": message})
                if res.status_code == 200:
                    count += 1
            except Exception as e:
                print(f"Failed sending to {u['user_id']}: {e}")
                
        flash(f"Broadcast sent to {count} users.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
