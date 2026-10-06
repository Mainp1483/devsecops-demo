"""
DevSecOps demo app - CỐ TÌNH chứa 20 lỗi (đánh dấu VULN-xx) để thực hành quét SonarQube.
KHÔNG dùng cho production, KHÔNG public ra internet.
"""
import hashlib
import io
import base64
import logging
import os
import pickle
import random
import sqlite3
import string
import subprocess
import xml.sax

import requests
from flask import Flask, redirect, request, send_file, session

app = Flask(__name__)
app.secret_key = "super-secret-key-123"                 # VULN-02: hardcode secret
app.config["WTF_CSRF_ENABLED"] = False                  # VULN-11: tắt CSRF
DB_PASSWORD = "Admin@123456"                            # VULN-02: hardcode mật khẩu DB
PAYMENT_API_KEY = "demo-payment-key-0123456789abcdef"   # VULN-03: hardcode API key (giá trị giả)
DB_FILE = "app.db"
UPLOAD_DIR = "uploads"
logging.basicConfig(level=logging.INFO)


def get_db():
    return sqlite3.connect(DB_FILE)


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()   # VULN-04: MD5


def init_db():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, item TEXT, total REAL)")
    if not db.execute("SELECT 1 FROM users").fetchone():
        db.execute("INSERT INTO users (username, password, email) VALUES (?,?,?)",
                   ("admin", hash_password("admin123"), "admin@example.com"))
        db.execute("INSERT INTO users (username, password, email) VALUES (?,?,?)",
                   ("alice", hash_password("alice123"), "alice@example.com"))
        db.execute("INSERT INTO orders (user_id, item, total) VALUES (1, 'Laptop', 1200)")
        db.execute("INSERT INTO orders (user_id, item, total) VALUES (2, 'Phone', 800)")
    db.commit()
    db.close()


@app.route("/")
def index():
    return "<h2>DevSecOps Demo</h2><p>Các endpoint: /login /search /ping /download /load-prefs /fetch-rate " \
           "/change-password /forgot-password /go /import-xml /preview /order/1 /upload /discount</p>"


# VULN-01: SQL Injection | VULN-13: ghi mật khẩu vào log
@app.route("/login", methods=["GET", "POST"])
def login():
    username = request.values.get("username", "")
    password = request.values.get("password", "")
    app.logger.info("Login attempt: user=%s password=%s", username, password)
    query = "SELECT id, username FROM users WHERE username = '%s' AND password = '%s'" % (
        username, hash_password(password))
    row = get_db().execute(query).fetchone()
    if row:
        session["user_id"] = row[0]
        return "Xin chào " + row[1]
    return "Sai thông tin đăng nhập", 401


# VULN-05: Reflected XSS
@app.route("/search")
def search():
    q = request.args.get("q", "")
    return "<h1>Kết quả cho: " + q + "</h1>"


# VULN-06: Command Injection
@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    out = subprocess.check_output("ping -c 1 " + host, shell=True)
    return out


# VULN-07: Path Traversal
@app.route("/download")
def download():
    name = request.args.get("file", "")
    return send_file(os.path.join(UPLOAD_DIR, name))


# VULN-08: Deserialization không an toàn
@app.route("/load-prefs")
def load_prefs():
    raw = request.cookies.get("prefs", "")
    prefs = pickle.loads(base64.b64decode(raw))
    return {"prefs": str(prefs)}


# VULN-10: tắt kiểm tra SSL
@app.route("/fetch-rate")
def fetch_rate():
    r = requests.get("https://api.exchangerate.host/latest", verify=False, timeout=5)
    return r.text


# VULN-11: thiếu CSRF token ở thao tác nhạy cảm
@app.route("/change-password", methods=["POST"])
def change_password():
    uid = session.get("user_id")
    if not uid:
        return "Chưa đăng nhập", 401
    db = get_db()
    db.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(request.form["new_password"]), uid))
    db.commit()
    return "Đã đổi mật khẩu"


# VULN-12: token reset mật khẩu dùng random (không an toàn mật mã)
@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    token = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
    return {"reset_token": token}


# VULN-14: Open Redirect
@app.route("/go")
def go():
    return redirect(request.args.get("next", "/"))


class ItemHandler(xml.sax.ContentHandler):
    def __init__(self):
        super().__init__()
        self.items = []

    def startElement(self, name, attrs):
        self.items.append(name)


# VULN-15: XXE (cho phép external entity)
@app.route("/import-xml", methods=["POST"])
def import_xml():
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_external_ges, True)
    handler = ItemHandler()
    parser.setContentHandler(handler)
    parser.parse(io.BytesIO(request.data))
    return {"elements": handler.items}


# VULN-16: SSRF
@app.route("/preview")
def preview():
    url = request.args.get("url", "")
    return requests.get(url, timeout=5).text


# VULN-17: IDOR - không kiểm tra đơn hàng có thuộc người dùng hiện tại không
@app.route("/order/<int:order_id>")
def get_order(order_id):
    row = get_db().execute("SELECT id, user_id, item, total FROM orders WHERE id = ?", (order_id,)).fetchone()
    return {"order": row}


# VULN-18: upload không giới hạn loại/kích thước, không dùng secure_filename
@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    f.save(os.path.join(UPLOAD_DIR, f.filename))
    return "Đã upload " + f.filename


# VULN-20: code smell - hàm phức tạp, except rỗng, code trùng lặp, biến thừa
@app.route("/discount")
def discount():
    user_type = request.args.get("type", "normal")
    amount = float(request.args.get("amount", "0"))
    vip_years = int(request.args.get("years", "0"))
    unused_variable = "chưa dùng"
    # TODO: viết lại hàm này
    try:
        if user_type == "vip":
            if amount > 1000:
                if vip_years > 5:
                    rate = 0.30
                elif vip_years > 2:
                    rate = 0.20
                else:
                    rate = 0.10
            elif amount > 500:
                if vip_years > 5:
                    rate = 0.25
                elif vip_years > 2:
                    rate = 0.15
                else:
                    rate = 0.05
            else:
                rate = 0.02
        elif user_type == "member":
            if amount > 1000:
                if vip_years > 5:
                    rate = 0.30
                elif vip_years > 2:
                    rate = 0.20
                else:
                    rate = 0.10
            else:
                rate = 0.01
        else:
            rate = 0
    except:
        pass
    return {"final": amount * (1 - rate)}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)      # VULN-09: debug=True + bind 0.0.0.0
# test
# test 2
