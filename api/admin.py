from flask import Flask, request, session, redirect, render_template_string
import sqlite3
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Credentials (change for production)
ADMIN_USER = 'Saksham'
ADMIN_PASS = 'SakshamXKt'

# Database setup - Shared between admin and API
def get_db_path():
    return '/tmp/wrapped_api.db'

def get_db_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_text TEXT UNIQUE,
                daily_limit INTEGER DEFAULT 0,
                used_today INTEGER DEFAULT 0,
                total_used INTEGER DEFAULT 0,
                last_used TEXT DEFAULT '',
                expiry_date TEXT DEFAULT '',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_id INTEGER,
                phone TEXT,
                used_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Admin: Database initialized successfully")
    except Exception as e:
        print(f"❌ Admin: Database initialization failed: {e}")

def calculate_usage_stats():
    """Calculate and update usage statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all keys
        cursor.execute('SELECT id FROM api_keys')
        keys = cursor.fetchall()
        
        for key_id, in keys:
            # Calculate used today
            cursor.execute('''
                SELECT COUNT(*) FROM usage_logs 
                WHERE api_key_id = ? AND date(used_at) = date('now')
            ''', (key_id,))
            used_today = cursor.fetchone()[0]
            
            # Calculate total used
            cursor.execute('SELECT COUNT(*) FROM usage_logs WHERE api_key_id = ?', (key_id,))
            total_used = cursor.fetchone()[0]
            
            # Update the key stats
            cursor.execute('''
                UPDATE api_keys SET used_today = ?, total_used = ? WHERE id = ?
            ''', (used_today, total_used, key_id))
        
        conn.commit()
        conn.close()
        print("✅ Admin: Usage stats updated")
    except Exception as e:
        print(f"❌ Admin: Error updating usage stats: {e}")

# HTML Templates with exact same design
LOGIN_HTML = '''
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Admin Login</title>
    <style>
        body{font-family:Arial,Helvetica,sans-serif;background:#f7f8fb;padding:20px}
        .box{max-width:360px;margin:60px auto;background:#fff;padding:18px;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,0.06)}
        input{width:100%;padding:10px;margin:8px 0;border-radius:8px;border:1px solid #ddd;box-sizing:border-box}
        button{width:100%;padding:10px;border-radius:8px;border:0;background:#0b71f2;color:#fff}
        .err{color:#c0392b;margin-bottom:10px}
    </style>
</head>
<body>
    <div class="box">
        <h2 style="margin:0 0 12px 0">Admin Login</h2>
        {% if login_error %}
        <div class="err">{{ login_error }}</div>
        {% endif %}
        <form method="post">
            <input name="login_user" placeholder="Username" required>
            <input name="login_pass" type="password" placeholder="Password" required>
            <div style="height:8px"></div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
'''

ADMIN_HTML = '''
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Admin Panel</title>
    <style>
        body{font-family:Arial,Helvetica,sans-serif;background:#f2f4f7;padding:16px}
        .wrap{max-width:980px;margin:0 auto}
        .card{background:#fff;padding:16px;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,0.06);margin-bottom:14px}
        input,select{padding:10px;border-radius:8px;border:1px solid #ddd;width:100%;box-sizing:border-box;margin:6px 0}
        button{padding:10px;border-radius:8px;border:0;background:#0b71f2;color:#fff}
        table{width:100%;border-collapse:collapse;margin-top:12px}
        th,td{padding:10px;border-bottom:1px solid #eee;text-align:left}
        .small{font-size:13px;color:#666}
        .badge{display:inline-block;padding:6px 8px;border-radius:8px;background:#efefef}
        .btn-link{background:none;border:0;color:#0b71f2;cursor:pointer;padding:6px 8px;border-radius:6px}
        @media(max-width:720px){.row{flex-direction:column}}
        .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}

        /* NEW: keys frame scrollable horizontally */
        .keys-frame {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        .keys-table {
            min-width:900px; /* ensures horizontal scrollbar on small screens */
        }
        .action-btn {
            padding:6px 10px;border-radius:6px;border:0;cursor:pointer;
        }
        .del-btn { background:#e74c3c;color:#fff }
        .toggle-btn { background:#f0ad4e;color:#fff }
    </style>
</head>
<body>
<div class="wrap">
    <div class="top">
        <h2>Admin Panel</h2>
        <div><a href="/admin?action=logout" style="text-decoration:none;color:#111">Logout</a></div>
    </div>

    {% if msg %}
    <div style="color:green;margin-bottom:8px">{{ msg }}</div>
    {% endif %}

    <div class="card">
        <h3>Create API Key</h3>
        <form method="post">
            <input type="hidden" name="action" value="create">
            <label>Key text (type the key you want)</label>
            <input name="key_text" placeholder="e.g. R0L3X-ABCDE-12345" required>
            <label>Daily limit (0 => unlimited)</label>
            <input name="daily_limit" type="number" value="0">
            <label>Expiry (months) (0 => never)</label>
            <input name="expiry_months" type="number" value="0">
            <div style="height:12px"></div>
            <button type="submit">Create Key</button>
        </form>
    </div>

    <div class="card keys-frame">
        <h3>All Keys</h3>
        <table class="keys-table">
            <thead><tr><th>ID</th><th>Key</th><th>Limit</th><th>Used Today</th><th>Total Used</th><th>Expiry</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
            {% for key in keys %}
            <tr>
                <td>{{ key.id }}</td>
                <td>{{ key.key_text }}</td>
                <td>{{ 'Unlimited' if key.daily_limit == 0 else key.daily_limit }}</td>
                <td>{{ key.used_today }}</td>
                <td>{{ key.total_used }}</td>
                <td>{{ key.expiry_date if key.expiry_date else 'Never' }}</td>
                <td>
                    {% if key.active %}
                    <span class="badge" style="background:#e6ffed;color:#0a7f3a">Active</span>
                    {% else %}
                    <span class="badge" style="background:#ffeaea;color:#c0392b">Revoked</span>
                    {% endif %}
                </td>
                <td>
                    <!-- Toggle form -->
                    <form method="post" style="display:inline">
                        <input type="hidden" name="action" value="toggle">
                        <input type="hidden" name="id" value="{{ key.id }}">
                        <button class="action-btn toggle-btn" type="submit">
                            {{ 'Revoke' if key.active else 'Activate' }}
                        </button>
                    </form>

                    <!-- Delete form -->
                    <form method="post" style="display:inline" onsubmit="return confirm('Delete key and all logs? This cannot be undone.');">
                        <input type="hidden" name="action" value="delete">
                        <input type="hidden" name="id" value="{{ key.id }}">
                        <button class="action-btn del-btn" type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="small">User Endpoint: <span class="badge">{{ endpoint_url }}</span></div>
    <div style="height:10px"></div>

    <!-- Owner line -->
    <div style="font-size:15px;margin-top:8px;">𝙊𝙬𝙣𝙚𝙧 : 𝙎𝙖𝙠𝙨𝙝𝙖𝙢</div>

</div>
</body>
</html>
'''

@app.route('/admin', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def admin_panel():
    # Logout handler
    if request.args.get('action') == 'logout':
        session.pop('admin_logged', None)
        return redirect('/admin')
    
    # Login check
    if not session.get('admin_logged'):
        login_error = None
        
        if request.method == 'POST':
            username = request.form.get('login_user', '')
            password = request.form.get('login_pass', '')
            
            if username == ADMIN_USER and password == ADMIN_PASS:
                session['admin_logged'] = True
                return redirect('/admin')
            else:
                login_error = 'Invalid credentials'
        
        return render_template_string(LOGIN_HTML, login_error=login_error)
    
    # Admin panel functionality
    msg = ''
    
    # Handle POST actions
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            key_text = request.form.get('key_text', '').strip()
            daily_limit = int(request.form.get('daily_limit', 0))
            expiry_months = int(request.form.get('expiry_months', 0))
            
            if not key_text:
                msg = 'Key text required'
            else:
                expiry_date = ''
                if expiry_months > 0:
                    expiry_date = (datetime.now() + timedelta(days=30*expiry_months)).strftime('%Y-%m-%d')
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO api_keys (key_text, daily_limit, expiry_date, active) 
                        VALUES (?, ?, ?, 1)
                    ''', (key_text, daily_limit, expiry_date))
                    conn.commit()
                    conn.close()
                    msg = 'Key created successfully'
                except sqlite3.IntegrityError:
                    msg = 'Key already exists'
                except Exception as e:
                    msg = f'Error creating key: {str(e)}'
        
        elif action == 'toggle' and request.form.get('id'):
            key_id = int(request.form.get('id'))
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT active FROM api_keys WHERE id = ?', (key_id,))
                result = cursor.fetchone()
                
                if result:
                    new_status = 0 if result[0] else 1
                    cursor.execute('UPDATE api_keys SET active = ? WHERE id = ?', (new_status, key_id))
                    conn.commit()
                    msg = 'Key updated successfully'
                else:
                    msg = 'Key not found'
                conn.close()
            except Exception as e:
                msg = f'Error updating key: {str(e)}'
        
        elif action == 'delete' and request.form.get('id'):
            key_id = int(request.form.get('id'))
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Delete usage logs first
                cursor.execute('DELETE FROM usage_logs WHERE api_key_id = ?', (key_id,))
                # Delete key
                cursor.execute('DELETE FROM api_keys WHERE id = ?', (key_id,))
                conn.commit()
                conn.close()
                msg = 'Key deleted successfully'
            except Exception as e:
                msg = f'Error deleting key: {str(e)}'
    
    # Recalculate usage stats
    calculate_usage_stats()
    
    # Fetch all keys
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM api_keys ORDER BY id DESC')
        keys = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        keys = []
        msg = f'Error fetching keys: {str(e)}'
    
    # Generate endpoint URL
    base_url = request.host_url.rstrip('/')
    endpoint_url = f"{base_url}/fetch?key=YOUR_KEY&num=PHONE"
    
    return render_template_string(ADMIN_HTML, 
                                msg=msg, 
                                keys=keys, 
                                endpoint_url=endpoint_url)

@app.route("/debug-db", methods=["GET"])
def debug_db():
    """Debug endpoint to check database state"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all keys
        cursor.execute('SELECT * FROM api_keys')
        keys = [dict(row) for row in cursor.fetchall()]
        
        # Get usage stats
        cursor.execute('SELECT COUNT(*) as total_logs FROM usage_logs')
        total_logs = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "database_path": get_db_path(),
            "total_keys": len(keys),
            "total_usage_logs": total_logs,
            "keys": keys
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }, 500

# Initialize database on startup
init_db()

# Vercel requires this
if __name__ == '__main__':
    app.run(debug=False)
