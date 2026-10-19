
import os
import sqlite3
from flask import Flask, request, redirect, url_for, send_from_directory, session, render_template_string, Response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cpit251_super_secret_key_mohannad"

# Folder where uploaded files (3D models, images, PDFs) are stored
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- 1. DATABASE SETUP (SQLite) ---
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # Table for items/assets
    c.execute('''CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    format TEXT NOT NULL,
                    description TEXT NOT NULL,
                    filename TEXT
                )''')
    # Table for Users (Demonstrates Security & Password Hashing)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )''')
    # Create default admin account (Username: admin, Password: password123)
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_pw = generate_password_hash("password123")
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", hashed_pw))
    conn.commit()
    conn.close()

init_db()

# --- HTML TEMPLATE (With SEO Meta Tags & Semantic HTML5) ---
HTML_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="3D Asset & Digital Resource Hub - Upload, search, manage, and download 3D models and project files. CPIT251 Project.">
    <meta name="keywords" content="3D Models, OBJ, Blend, Digital Assets, CPIT251, Web Development">
    <meta name="author" content="Mohannad Al Ghamdi">
    <title>{{ page_title }} | 3D Asset Hub</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; background: #f4f6f9; color: #222; }
        header { background: #1e293b; color: white; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; }
        header a { color: #38bdf8; text-decoration: none; margin-left: 15px; font-weight: bold; }
        main { max-width: 1000px; margin: 30px auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
        .card { border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; margin-bottom: 15px; background: #fafafa; }
        .badge { background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 10px; margin: 8px 0 16px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box; }
        button, .btn { background: #2563eb; color: white; padding: 10px 16px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 14px; }
        .btn-danger { background: #dc2626; }
        .btn-secondary { background: #475569; }
        .search-bar { display: flex; gap: 10px; background: #f1f5f9; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
        footer { text-align: center; padding: 20px; color: #64748b; font-size: 14px; }
    </style>
</head>
<body>
    <header>
        <div>
            <h1 style="margin:0; font-size: 22px;">3D Asset & Model Hub</h1>
            <small>Structured Web Architecture & CRUD System — CPIT251</small>
        </div>
        <nav>
            <a href="/assets/search">Home / Browse</a>
            {% if session.get('user') %}
                <a href="/assets/upload">+ Add & Upload Asset</a>
                <a href="/auth/logout">Logout ({{ session.get('user') }})</a>
            {% else %}
                <a href="/auth/login">Admin Login</a>
            {% endif %}
        </nav>
    </header>

    <main>
        {{ content | safe }}
    </main>

    <footer>
        <p>Developed by Mohannad Al Ghamdi | CPIT251 Website Design & Development Project | <a href="/sitemap.xml">Sitemap</a> | <a href="/robots.txt">Robots.txt</a></p>
    </footer>
</body>
</html>
'''

# --- 2. URL ROUTES (Demonstrating Structured URLs & Query Strings) ---

@app.route("/")
def home():
    return redirect("/assets/search")

# READ & SEARCH (URL Example: /assets/search?q=sword&category=Rigged)
@app.route("/assets/search", methods=["GET"])
def search_assets():
    query = request.args.get("q", "")
    category = request.args.get("category", "")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    sql = "SELECT id, title, category, format, description, filename FROM assets WHERE 1=1"
    params = []
    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if category:
        sql += " AND category = ?"
        params.append(category)

    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()

    items_html = ""
    for r in rows:
        file_link = f'<a class="btn btn-secondary" href="/assets/download?file={r[5]}">Download File ({r[5]})</a>' if r[5] else ""
        admin_btns = ""
        if session.get("user"):
            admin_btns = f'''
            <a class="btn" href="/assets/edit?id={r[0]}">Edit</a>
            <a class="btn btn-danger" href="/assets/delete?id={r[0]}" onclick="return confirm('Delete this item?');">Delete</a>
            '''
        items_html += f'''
        <article class="card">
            <h3><a href="/assets/view?id={r[0]}">{r[1]}</a> <span class="badge">{r[2]}</span> <span class="badge">{r[3]}</span></h3>
            <p>{r[4]}</p>
            {file_link}
            <a class="btn" href="/assets/view?id={r[0]}">View Details</a>
            {admin_btns}
        </article>
        '''

    if not items_html:
        items_html = "<p>No assets found. Log in as admin (<b>admin</b> / <b>password123</b>) and click <b>+ Add & Upload Asset</b> to create one!</p>"

    content = f'''
    <h2>Browse & Search 3D Assets</h2>
    <form class="search-bar" method="GET" action="/assets/search">
        <input type="text" name="q" placeholder="Search by keyword..." value="{query}" style="margin:0;">
        <select name="category" style="margin:0; max-width:200px;">
            <option value="">All Categories</option>
            <option value="Character" {"selected" if category=="Character" else ""}>Character</option>
            <option value="Environment" {"selected" if category=="Environment" else ""}>Environment</option>
            <option value="Rigged" {"selected" if category=="Rigged" else ""}>Rigged Model</option>
            <option value="Texture" {"selected" if category=="Texture" else ""}>Texture / UV</option>
        </select>
        <button type="submit">Filter URL</button>
    </form>
    {items_html}
    '''
    return render_template_string(HTML_PAGE, page_title="Browse 3D Assets", content=content)

# VIEW SINGLE ITEM (URL Example: /assets/view?id=1)
@app.route("/assets/view", methods=["GET"])
def view_asset():
    asset_id = request.args.get("id", "1")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, title, category, format, description, filename FROM assets WHERE id = ?", (asset_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return render_template_string(HTML_PAGE, page_title="404 Not Found", content="<h2>404 Error: Asset Not Found</h2>"), 404

    download_btn = f'<p><a class="btn" href="/assets/download?file={r[5]}">Download Attached File ({r[5]})</a></p>' if r[5] else "<p>No file attached.</p>"
    content = f'''
    <h2>{r[1]}</h2>
    <p><strong>Category:</strong> {r[2]} | <strong>Format:</strong> {r[3]} | <strong>Asset ID:</strong> {r[0]}</p>
    <p>{r[4]}</p>
    {download_btn}
    <hr>
    <p><a href="/assets/search">&larr; Back to all assets</a></p>
    '''
    return render_template_string(HTML_PAGE, page_title=r[1], content=content)

# CREATE & FILE UPLOAD (URL: /assets/upload)
@app.route("/assets/upload", methods=["GET", "POST"])
def upload_asset():
    if not session.get("user"):
        return redirect("/auth/login")
    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        fmt = request.form["format"]
        desc = request.form["description"]
        uploaded_file = request.files.get("file")
        filename = None
        if uploaded_file and uploaded_file.filename != "":
            filename = secure_filename(uploaded_file.filename)
            uploaded_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO assets (title, category, format, description, filename) VALUES (?, ?, ?, ?, ?)",
                  (title, category, fmt, desc, filename))
        conn.commit()
        conn.close()
        return redirect("/assets/search")

    content = '''
    <h2>Add New 3D Asset & Upload File</h2>
    <form method="POST" enctype="multipart/form-data">
        <label>Asset Title *</label>
        <input type="text" name="title" required placeholder="e.g., Low-Poly Cyberpunk Sword">
        <label>Category *</label>
        <select name="category">
            <option value="Character">Character</option>
            <option value="Environment">Environment</option>
            <option value="Rigged">Rigged Model</option>
            <option value="Texture">Texture / UV</option>
        </select>
        <label>File Format *</label>
        <input type="text" name="format" required placeholder="e.g., .OBJ, .BLEND, .FBX, .PNG">
        <label>Technical Description *</label>
        <textarea name="description" rows="4" required placeholder="Describe polygon count, UV mapping, textures..."></textarea>
        <label>Attach File (3D Model, Image, or ZIP)</label>
        <input type="file" name="file">
        <button type="submit">Save & Upload to Server</button>
    </form>
    '''
    return render_template_string(HTML_PAGE, page_title="Upload New Asset", content=content)

# UPDATE ITEM (URL Example: /assets/edit?id=1)
@app.route("/assets/edit", methods=["GET", "POST"])
def edit_asset():
    if not session.get("user"):
        return redirect("/auth/login")
    asset_id = request.args.get("id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        fmt = request.form["format"]
        desc = request.form["description"]
        c.execute("UPDATE assets SET title=?, category=?, format=?, description=? WHERE id=?",
                  (title, category, fmt, desc, asset_id))
        conn.commit()
        conn.close()
        return redirect(f"/assets/view?id={asset_id}")

    c.execute("SELECT id, title, category, format, description FROM assets WHERE id=?", (asset_id,))
    r = c.fetchone()
    conn.close()
    content = f'''
    <h2>Edit Asset (ID: {r[0]})</h2>
    <form method="POST">
        <label>Asset Title</label>
        <input type="text" name="title" value="{r[1]}" required>
        <label>Category</label>
        <input type="text" name="category" value="{r[2]}" required>
        <label>Format</label>
        <input type="text" name="format" value="{r[3]}" required>
        <label>Description</label>
        <textarea name="description" rows="4" required>{r[4]}</textarea>
        <button type="submit">Update Record</button>
    </form>
    '''
    return render_template_string(HTML_PAGE, page_title="Edit Asset", content=content)

# DELETE ITEM (URL Example: /assets/delete?id=1)
@app.route("/assets/delete")
def delete_asset():
    if not session.get("user"):
        return redirect("/auth/login")
    asset_id = request.args.get("id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    conn.commit()
    conn.close()
    return redirect("/assets/search")

# DOWNLOAD FILE (URL Example: /assets/download?file=model.obj)
@app.route("/assets/download")
def download_file():
    filename = request.args.get("file")
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

# --- 3. SECURITY & AUTHENTICATION (Password Hashing) ---
@app.route("/auth/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        if row and check_password_hash(row[0], password):
            session["user"] = username
            return redirect("/assets/search")
        error = "<p style='color:red;'>Invalid credentials! Try admin / password123</p>"

    content = f'''
    <h2>Secure Administrator Login</h2>
    <p>Passwords are encrypted using PBKDF2 SHA-256 cryptographic hashing.</p>
    {error}
    <form method="POST">
        <label>Username</label>
        <input type="text" name="username" value="admin" required>
        <label>Password</label>
        <input type="password" name="password" value="password123" required>
        <button type="submit">Authenticate via POST</button>
    </form>
    '''
    return render_template_string(HTML_PAGE, page_title="Admin Login", content=content)

@app.route("/auth/logout")
def logout():
    session.pop("user", None)
    return redirect("/assets/search")

# --- 4. SEO ROUTES (Robots.txt & Sitemap.xml) ---
@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nSitemap: /sitemap.xml", mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>/assets/search</loc><priority>1.0</priority></url>
        <url><loc>/auth/login</loc><priority>0.8</priority></url>
    </urlset>'''
    return Response(xml, mimetype="application/xml")

if __name__ == "__main__":
    app.run(debug=True, port=5000)