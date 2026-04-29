import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="../frontend", static_folder="../static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

csrf = CSRFProtect(app)

client     = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"))
db         = client["Picsource_db"]
images_col = db["image_metadata"]
users_col  = db["user"]

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "tiff", "bmp", "heic"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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

        # Admin check (credentials stored in .env, not in database)
        if username == os.environ.get("ADMIN_USERNAME") and password == os.environ.get("ADMIN_PASSWORD"):
            session["username"] = username
            session["is_admin"] = True
            flash("Welcome, Admin!", "success")
            return redirect(url_for("index"))

        # Regular user check
        user = users_col.find_one({"username": username})
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
        session["username"] = user["username"]
        session["is_admin"] = False
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
        flash("Invalid file type. Allowed: PNG, JPG, GIF, WEBP, TIFF, BMP, HEIC.", "error")
        return redirect(url_for("upload_page"))

    ext         = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    save_path   = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    size_bytes = os.path.getsize(save_path)
    tags       = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]

    images_col.insert_one({
        "filename":     unique_name,
        "image_url":    url_for("send_uploaded_file", filename=unique_name),
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
    local_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(local_path):
        os.remove(local_path)
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

# ── SERVE FILES ────────────────────────────────────────────
@app.route("/display/<filename>")
def send_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port  = int(os.environ.get("PORT", 5001))
    app.run(debug=debug, port=port)