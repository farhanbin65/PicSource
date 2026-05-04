import os
import uuid
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

app = Flask(__name__, template_folder="../frontend", static_folder="../static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

csrf = CSRFProtect(app)

# ── MONGODB ATLAS (for user accounts only) ─────────────────
client    = MongoClient(os.environ.get("COSMOS_URI"))
db        = client["Picsource_db"]
users_col = db["user"]

# ── LOGIC APP URLS (CRUD for images via Cosmos DB) ─────────
LOGIC_CREATE = os.environ.get("LOGIC_CREATE")
LOGIC_READ   = os.environ.get("LOGIC_READ")
LOGIC_UPDATE = os.environ.get("LOGIC_UPDATE")
LOGIC_DELETE = os.environ.get("LOGIC_DELETE")

# ── AZURE BLOB STORAGE ─────────────────────────────────────
BLOB_CONTAINER        = os.environ.get("BLOB_CONTAINER", "images")
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT")
conn_str              = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
blob_service          = BlobServiceClient.from_connection_string(conn_str)
container_client      = blob_service.get_container_client(BLOB_CONTAINER)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "tiff", "bmp", "heic"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_blob_url(filename):
    return f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{BLOB_CONTAINER}/{filename}"

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ── REGISTER ───────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if users_col.find_one({"username": username}):
            flash("Username already taken.", "error")
            return redirect(url_for("register"))
        users_col.insert_one({
            "username":   username,
            "password":   generate_password_hash(password),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# ── LOGIN ──────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == os.environ.get("ADMIN_USERNAME") and \
           password == os.environ.get("ADMIN_PASSWORD"):
            session["username"] = username
            session["is_admin"]  = True
            flash("Welcome, Admin!", "success")
            return redirect(url_for("index"))
        user = users_col.find_one({"username": username})
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
        session["username"] = user["username"]
        session["is_admin"]  = False
        flash(f"Welcome, {user['username']}!", "success")
        return redirect(url_for("index"))
    return render_template("login.html")

# ── LOGOUT ─────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

# ── GALLERY (READ via Logic App) ───────────────────────────
@app.route("/")
def index():
    try:
        response = requests.get(LOGIC_READ, timeout=30)
        if response.status_code == 200 and response.text:
            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                images = data
            elif isinstance(data, dict):
                images = data.get("value", data.get("Documents", data.get("items", [])))
            else:
                images = []
        else:
            images = []
    except Exception as e:
        images = []
        flash(f"Could not load images: {e}", "error")
    return render_template("index.html", images=images)
# ── UPLOAD (CREATE via Logic App) ──────────────────────────
@app.route("/upload-page")
@login_required
def upload_page():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
@login_required
def handle_upload():
    if "file" not in request.files:
        flash("No file part.", "error")
        return redirect(url_for("upload_page"))
    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("upload_page"))
    if not allowed_file(file.filename):
        flash("Invalid file type.", "error")
        return redirect(url_for("upload_page"))

    ext         = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"

    # Upload to Azure Blob
    blob_client = container_client.get_blob_client(unique_name)
    file_bytes  = file.read()
    blob_client.upload_blob(file_bytes, overwrite=True)

    size_bytes = len(file_bytes)
    tags       = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]

    # CREATE via Logic App → Cosmos DB
    payload = {
        "filename":     unique_name,
        "image_url":    get_blob_url(unique_name),
        "title":        request.form.get("title", "").strip(),
        "description":  request.form.get("description", "").strip(),
        "category":     request.form.get("category", "").strip(),
        "type":         request.form.get("type", "").strip(),
        "format":       request.form.get("format", "").strip(),
        "resolution":   request.form.get("resolution", "").strip(),
        "photographer": request.form.get("photographer", "").strip(),
        "camera":       request.form.get("camera", "").strip(),
        "location":     request.form.get("location", "").strip(),
        "tags":         tags,
        "size_kb":      round(size_bytes / 1024, 2),
        "size_mb":      round(size_bytes / (1024 * 1024), 2),
        "upload_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uploaded_by":  session.get("username", "unknown")
    }
    try:
        requests.post(LOGIC_CREATE, json=payload, timeout=30)
        flash("Image uploaded!", "success")
    except Exception as e:
        flash(f"Upload failed: {e}", "error")
    return redirect(url_for("index"))

# ── DELETE (DELETE via Logic App) ──────────────────────────
@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_image(filename):
    if not session.get("is_admin"):
        flash("Only admin can delete images.", "error")
        return redirect(url_for("index"))

    # Delete from Blob Storage
    try:
        container_client.get_blob_client(filename).delete_blob()
    except Exception:
        pass

    # DELETE via Logic App → Cosmos DB
    try:
        requests.request(
            "DELETE", LOGIC_DELETE,
            json={"id": filename},
            timeout=30
        )
        flash("Image deleted.", "info")
    except Exception as e:
        flash(f"Delete failed: {e}", "error")
    return redirect(url_for("index"))

# ── UPDATE (UPDATE via Logic App) ──────────────────────────
@app.route("/update/<filename>", methods=["POST"])
@login_required
def update_image(filename):
    if not session.get("is_admin"):
        flash("Only admin can edit images.", "error")
        return redirect(url_for("index"))

    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    payload = {
        "id":           filename,
        "title":        request.form.get("title", "").strip(),
        "description":  request.form.get("description", "").strip(),
        "category":     request.form.get("category", "").strip(),
        "type":         request.form.get("type", "").strip(),
        "format":       request.form.get("format", "").strip(),
        "resolution":   request.form.get("resolution", "").strip(),
        "photographer": request.form.get("photographer", "").strip(),
        "camera":       request.form.get("camera", "").strip(),
        "location":     request.form.get("location", "").strip(),
        "tags":         tags,
    }
    try:
        requests.request(
            "PATCH", LOGIC_UPDATE,
            json=payload,
            timeout=30
        )
        flash("Image updated!", "success")
    except Exception as e:
        flash(f"Update failed: {e}", "error")
    return redirect(url_for("index"))

# ── HEALTH CHECK ───────────────────────────────────────────
@app.route("/health")
def health():
    return {
        "status":   "healthy",
        "service":  "PicSource",
        "storage":  "Azure Blob Storage",
        "database": "Azure Cosmos DB (via Logic Apps)",
        "crud":     "Azure Logic Apps"
    }, 200

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port  = int(os.environ.get("PORT", 5001))
    app.run(debug=debug, port=port)