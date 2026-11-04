import os
import psycopg2
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import Flask, request, redirect, url_for, session, render_template_string, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cpit251_super_secret_key_mohannad"

# --- SECURE CLOUDINARY CONFIGURATION ---
# Pulls the secret safely from Render's Environment Variables
cloudinary.config(
  cloud_name = "y5oxbi6z",
  api_key = "536198723416148",
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

# --- SECURE CLOUD DATABASE CONFIGURATION ---
# Pulls the Neon database URL safely from Render's Environment Variables
DB_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DB_URL)

# --- 1. DATABASE SETUP (PostgreSQL) ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Table for items/assets (Postgres uses SERIAL instead of AUTOINCREMENT)
    c.execute('''CREATE TABLE IF NOT EXISTS assets (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    format TEXT NOT NULL,
                    description TEXT NOT NULL,
                    filename TEXT
                )''')
    # Table for Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )''')
    
    # Create default admin account so you can log in
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_pw = generate_password_hash("password123")
        c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", ("admin", hashed_pw))
    
    # No default assets are added here. The database starts completely empty!
    
    conn.commit()
    c.close()
    conn.close()

init_db()

# --- HTML TEMPLATE ---
HTML_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="3D Asset Hub - CPIT251 Project.">
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
            <small>Structured Web Architecture & Cloud Database</small>
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
        <p>Developed by Mohannad Al Ghamdi | CPIT251 Website Design Project</p>
    </footer>
</body>
</html>
'''

# --- 2. URL ROUTES ---

@app.route("/")
def home():
    return redirect("/assets/search")

# READ & SEARCH 
@app.route("/assets/search", methods=["GET"])
def search_assets():
    query = request.args.get("q", "")
    category = request.args.get("category", "")

    conn = get_db_connection()
    c = conn.cursor()
    sql = "SELECT id, title, category, format, description, filename FROM assets WHERE 1=1"
    params = []
    
    if query:
        # ILIKE is used in Postgres for case-insensitive searching
        sql += " AND (title ILIKE %s OR description ILIKE %s)" 
        params.extend([f"%{query}%", f"%{query}%"])
    if category:
        sql += " AND category = %s"
        params.append(category)

    c.execute(sql, tuple(params))
    rows = c.fetchall()
    c.close()
    conn.close()

    items_html = ""
    for r in rows:
        file_link = f'<a class="btn btn-secondary" href="/assets/download?file={r[5]}">Download File</a>' if r[5] else ""
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
        items_html = "<p>No assets found. Click '+ Add & Upload Asset' to create one!</p>"

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

# VIEW SINGLE ITEM
@app.route("/assets/view", methods=["GET"])
def view_asset():
    asset_id = request.args.get("id", "1")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, category, format, description, filename FROM assets WHERE id = %s", (asset_id,))
    r = c.fetchone()
    c.close()
    conn.close()
    
    if not r:
        return render_template_string(HTML_PAGE, page_title="404 Not Found", content="<h2>404 Error: Asset Not Found</h2>"), 404

    download_btn = f'<p><a class="btn" href="/assets/download?file={r[5]}">Download Attached File</a></p>' if r[5] else "<p>No file attached.</p>"
    content = f'''
    <h2>{r[1]}</h2>
    <p><strong>Category:</strong> {r[2]} | <strong>Format:</strong> {r[3]} | <strong>Asset ID:</strong> {r[0]}</p>
    <p>{r[4]}</p>
    {download_btn}
    <hr>
    <p><a href="/assets/search">&larr; Back to all assets</a></p>
    '''
    return render_template_string(HTML_PAGE, page_title=r[1], content=content)

# CREATE & FILE UPLOAD
@app.route("/assets/upload", methods=["GET", "POST"])
def upload_asset():
    if not session.get("user"):
        return redirect("/auth/login")
    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        fmt = request.form["format"]
        desc = request.form["description"]
        uploaded
