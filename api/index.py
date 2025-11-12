"""
Vercel-compatible Flask API for phone number lookup with database integration
"""
from flask import Flask, request, Response
import requests, re, html, binascii, json, logging, sqlite3, os
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === CONFIG ===
TARGET_URL = "https://hostzo.rf.gd/hacker.php?i=1"
SOURCE_NAME = "Saksham"
REQUEST_TIMEOUT = 30
# ==============

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?1",
    "Origin": "https://hostzo.rf.gd",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://hostzo.rf.gd/hacker.php?i=1",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

EMOJI_RE = re.compile(r"[\U0001F000-\U0010FFFF]+", flags=re.UNICODE)

# Database setup - Use absolute path in Vercel
def get_db_path():
    return '/tmp/wrapped_api.db'

def init_db():
    db_path = get_db_path()
    print(f"Initializing database at: {db_path}")  # Debug
    conn = sqlite3.connect(db_path)
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
    
    # Check if we have any keys
    cursor.execute('SELECT COUNT(*) FROM api_keys')
    count = cursor.fetchone()[0]
    print(f"Total keys in database: {count}")  # Debug
    
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(get_db_path())

def validate_api_key(api_key):
    """
    Validate API key from database
    Returns: (is_valid, key_data, error_message) 
    """
    if not api_key:
        return False, None, "API key is required"
    
    print(f"Validating API key: {api_key}")  # Debug
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # First, let's see what keys we have in database
    cursor.execute('SELECT key_text, active FROM api_keys')
    all_keys = cursor.fetchall()
    print(f"All keys in DB: {[dict(row) for row in all_keys]}")  # Debug
    
    cursor.execute('''
        SELECT * FROM api_keys 
        WHERE key_text = ? AND active = 1 
        AND (expiry_date = '' OR expiry_date > date('now'))
    ''', (api_key,))
    
    key_data = cursor.fetchone()
    
    if not key_data:
        conn.close()
        print(f"Key not found or inactive: {api_key}")  # Debug
        return False, None, "API key not found or inactive"
    
    print(f"Key found: {dict(key_data)}")  # Debug
    
    # Check daily limit
    if key_data['daily_limit'] > 0:
        cursor.execute('''
            SELECT COUNT(*) FROM usage_logs 
            WHERE api_key_id = ? AND date(used_at) = date('now')
        ''', (key_data['id'],))
        used_today = cursor.fetchone()[0]
        
        print(f"Used today: {used_today}, Limit: {key_data['daily_limit']}")  # Debug
        
        if used_today >= key_data['daily_limit']:
            conn.close()
            return False, key_data, f"Daily limit exceeded. Used: {used_today}/{key_data['daily_limit']}"
    
    conn.close()
    return True, key_data, None

def log_usage(api_key_id, phone_number):
    """Log API usage to database"""
    print(f"Logging usage for key_id: {api_key_id}, phone: {phone_number}")  # Debug
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO usage_logs (api_key_id, phone, used_at) 
        VALUES (?, ?, datetime('now'))
    ''', (api_key_id, phone_number))
    
    # Update last_used timestamp
    cursor.execute('''
        UPDATE api_keys SET last_used = datetime('now') WHERE id = ?
    ''', (api_key_id,))
    
    conn.commit()
    conn.close()
    print("Usage logged successfully")  # Debug

def clean_text(t):
    if not t:
        return ""
    t = html.unescape(t)
    t = EMOJI_RE.sub("", t)
    t = re.sub(r"[\uFE00-\uFE0F\u200D]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def parse_reply_html(reply_html):
    soup = BeautifulSoup(reply_html, "html.parser")
    rows = soup.find_all("div", class_="row")
    data = {}
    for r in rows:
        lbl_el = r.find("div", class_="label")
        val_el = r.find("div", class_="value")
        label = clean_text(lbl_el.get_text(" ", strip=True)) if lbl_el else ""
        value = clean_text(val_el.get_text(" ", strip=True)) if val_el else ""
        key = re.sub(r"[^\w\s]", "", label).strip().lower().replace(" ", "_").replace(":", "")
        if key:
            data[key] = value
    return data

def attempt_js_cookie(page_html):
    hexvals = re.findall(r'toNumbers\(\s*"([0-9a-fA-F]+)"\s*\)', page_html)
    if len(hexvals) < 3:
        return None
    a, b, c = hexvals[-3], hexvals[-2], hexvals[-1]
    try:
        key_bytes = binascii.unhexlify(a)
        iv_bytes = binascii.unhexlify(b)
        cipher_bytes = binascii.unhexlify(c)
        dec = AES.new(key_bytes, AES.MODE_CBC, iv_bytes).decrypt(cipher_bytes)
        try:
            plain = unpad(dec, AES.block_size)
        except Exception:
            plain = dec.rstrip(b"\x00").rstrip()
        return binascii.hexlify(plain).decode()
    except Exception:
        return None

def make_json_response(payload_dict, status=200):
    compact = json.dumps(payload_dict, separators=(",", ":"))
    headers = {"X-Source-Developer": SOURCE_NAME}
    return Response(compact, status=status, mimetype="application/json; charset=utf-8", headers=headers)

def upstream_post_number(num, cookie_value=None):
    headers = dict(BASE_HEADERS)
    
    if cookie_value:
        headers["Cookie"] = cookie_value
    
    files = {"message": (None, num)}
    
    resp = requests.post(TARGET_URL, headers=headers, files=files, timeout=REQUEST_TIMEOUT)
    return resp

@app.route("/fetch", methods=["GET"])
def fetch():
    provided_key = request.args.get("key", "").strip()
    num = request.args.get("num", "").strip()

    print(f"API Request - Key: {provided_key}, Number: {num}")  # Debug

    # Validate API key from database
    is_valid, key_data, error_msg = validate_api_key(provided_key)
    if not is_valid:
        return make_json_response({"ok": False, "error": error_msg}, status=401)

    # Validate phone number
    if not re.fullmatch(r"\d{10}", num):
        return make_json_response({"ok": False, "error": "Provide a valid 10-digit phone number in ?num= parameter."}, status=400)

    # Call upstream (first try without cookie header; if JS challenge appears, try to solve and retry with cookie)
    try:
        resp = upstream_post_number(num)
    except Exception as e:
        logging.exception("Upstream request failed (initial)")
        return make_json_response({"ok": False, "error": f"Upstream request failed: {str(e)}"}, status=502)

    # Try parse upstream JSON; if there's a JS challenge, attempt cookie solution and retry once
    try:
        upstream_json = resp.json()
    except ValueError:
        # Attempt to extract/decrypt __test cookie from the returned page and retry
        cookie = attempt_js_cookie(resp.text)
        if not cookie:
            logging.warning("JS challenge present and not solvable (no cookie extracted)")
            return make_json_response({"ok": False, "error": "JS challenge not solvable."}, status=502)
        
        # Build cookie header with __test value
        cookie_header_value = f"__test={cookie}"
        try:
            resp = upstream_post_number(num, cookie_value=cookie_header_value)
            upstream_json = resp.json()
        except Exception as e:
            logging.exception("Upstream failed after solving cookie")
            return make_json_response({"ok": False, "error": f"Upstream request failed after cookie: {str(e)}"}, status=502)

    # Extract results
    results = []
    if isinstance(upstream_json, dict) and "reply" in upstream_json:
        results.append(parse_reply_html(upstream_json["reply"]))
    elif isinstance(upstream_json, dict) and "replies" in upstream_json:
        for rhtml in upstream_json["replies"]:
            results.append(parse_reply_html(rhtml))
    else:
        logging.warning("Upstream returned unexpected structure")
        return make_json_response({"ok": False, "error": "Upstream did not return expected data."}, status=502)

    # Log successful usage
    log_usage(key_data['id'], num)

    # Top-level payload: include source_developer only once (top-level)
    payload = {
        "ok": True,
        "results": results,
        "source_developer": SOURCE_NAME
    }
    return make_json_response(payload, status=200)

@app.route("/", methods=["GET"])
def home_redirect():
    """Redirect root to admin panel"""
    from flask import redirect
    return redirect("/admin")

@app.route("/debug-db", methods=["GET"])
def debug_db():
    """Debug endpoint to check database state"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
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

# Initialize database on startup
init_db()

# Vercel requires this
if __name__ == "__main__":
    app.run(debug=False)
