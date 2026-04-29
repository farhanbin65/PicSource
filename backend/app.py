import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

app = Flask(__name__, template_folder="../frontend", static_folder="../static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

csrf = CSRFProtect(app)

# ── COSMOS DB / MONGODB ATLAS ──────────────────────────────
client     = MongoClient(os.environ.get("COSMOS_URI"))
db         = client["Picsource_db"]
images_col = db["image_metadata"]
users_col  = db["user"]

# ── AZURE BLOB STORAGE (connection string) ─────────────────
BLOB_CONTAINER        = os.environ.get("BLOB_CONTAINER", "images")
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT")

conn_str         = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
blob_service     = BlobServiceClient.from_connection_string(conn_str)
container_client = blob_service.get_container_client(BLOB_CONTAINER)

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

# ── GALLERY ────────────────────────────────────────────────
@app.route("/")
def index():
    images = list(images_col.find())
    return render_template("index.html", images=images)

# ── UPLOAD ─────────────────────────────────────────────────
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

    blob_client = container_client.get_blob_client(unique_name)
    file_bytes  = file.read()
    blob_client.upload_blob(file_bytes, overwrite=True)

    size_bytes = len(file_bytes)
    tags       = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]

    images_col.insert_one({
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
    })
    flash("Image uploaded!", "success")
    return redirect(url_for("index"))

# ── DELETE ─────────────────────────────────────────────────
@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_image(filename):
    if not session.get("is_admin"):
        flash("Only admin can delete images.", "error")
        return redirect(url_for("index"))
    img = images_col.find_one({"filename": filename})
    if not img:
        flash("Image not found.", "error")
        return redirect(url_for("index"))
    try:
        container_client.get_blob_client(filename).delete_blob()
    except Exception:
        pass
    images_col.delete_one({"filename": filename})
    flash("Image deleted.", "info")
    return redirect(url_for("index"))

# ── UPDATE (metadata only) ─────────────────────────────────
@app.route("/update/<filename>", methods=["POST"])
@login_required
def update_image(filename):
    if not session.get("is_admin"):
        flash("Only admin can edit images.", "error")
        return redirect(url_for("index"))
    img = images_col.find_one({"filename": filename})
    if not img:
        flash("Image not found.", "error")
        return redirect(url_for("index"))
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    images_col.update_one({"filename": filename}, {"$set": {
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
    }})
    flash("Image updated!", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port  = int(os.environ.get("PORT", 5001))
    app.run(debug=debug, port=port)