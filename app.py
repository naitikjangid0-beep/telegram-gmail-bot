from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
