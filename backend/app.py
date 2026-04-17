import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

# ── Azure Blob Storage (swap in after deployment) ──────────────────────────
# from azure.storage.blob import BlobServiceClient
# BLOB_CONN_STR = os.environ.get("AZURE_BLOB_CONNECTION_STRING")
# BLOB_CONTAINER = os.environ.get("AZURE_BLOB_CONTAINER", "picsource-images")
# blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from pymongo import MongoClient
from datetime import datetime
from functools import wraps

app = Flask(__name__, template_folder="../frontend", static_folder="../static")
app.secret_key = "dev-secret"

# ── MongoDB ────────────────────────────────────────────────────────────────
client     = MongoClient("mongodb://localhost:27017/")
db         = client["Picsource_db"]
images_col = db["image_metadata"]
users_col  = db["users"]

# ── Uploads folder ─────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Auth helper ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════
#  REGISTER
# ══════════════════════════════════════════════════════════
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
            "password":   password,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ══════════════════════════════════════════════════════════
#  LOGIN
# ══════════════════════════════════════════════════════════
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = users_col.find_one({"username": username, "password": password})
        if not user:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        session["username"] = user["username"]
        flash(f"Welcome, {user['username']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


# ══════════════════════════════════════════════════════════
#  LOGOUT
# ══════════════════════════════════════════════════════════
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════
#  GALLERY
# ══════════════════════════════════════════════════════════
@app.route("/")
def index():
    images = list(images_col.find())
    return render_template("index.html", images=images)


# ══════════════════════════════════════════════════════════
#  UPLOAD PAGE
# ══════════════════════════════════════════════════════════
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

    ext         = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    save_path   = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    size_bytes = os.path.getsize(save_path)
    tags_raw   = request.form.get("tags", "")
    tags       = [t.strip() for t in tags_raw.split(",") if t.strip()]

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


# ══════════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════════
@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_image(filename):
    img = images_col.find_one({"filename": filename})
    if not img:
        flash("Image not found.", "error")
        return redirect(url_for("index"))

    if img.get("uploaded_by") != session.get("username"):
        flash("You can only delete your own images.", "error")
        return redirect(url_for("index"))

    local_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(local_path):
        os.remove(local_path)

    images_col.delete_one({"filename": filename})
    flash("Image deleted.", "info")
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════
#  SERVE UPLOADED FILES
# ══════════════════════════════════════════════════════════
@app.route("/display/<filename>")
def send_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
app = Flask(__name__, template_folder="../frontend", static_folder="../frontend/static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# ── MongoDB / Cosmos DB ────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client     = MongoClient(MONGO_URI)
db         = client["Picsource_db"]
images_col = db["image_metadata"]
users_col  = db["users"]

# ── Local uploads fallback (dev only) ─────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("register"))

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


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = users_col.find_one({"username": username})
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        session["user_id"]  = str(user["_id"])
        session["username"] = user["username"]
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════
#  GALLERY
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    images = list(images_col.find())
    return render_template("index.html", images=images)


# ══════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════

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

    # Generate unique filename to avoid collisions
    ext        = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"

    # ── LOCAL save (dev) ──────────────────────────────────
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(save_path)
    image_url = url_for("send_uploaded_file", filename=unique_name)

    # ── AZURE BLOB save (prod — uncomment after deployment) ──
    # file.seek(0)
    # blob_client = blob_service.get_blob_client(container=BLOB_CONTAINER, blob=unique_name)
    # blob_client.upload_blob(file, overwrite=True)
    # image_url = f"https://<your_storage_account>.blob.core.windows.net/{BLOB_CONTAINER}/{unique_name}"

    size_bytes = os.path.getsize(save_path)
    size_kb    = round(size_bytes / 1024, 2)
    size_mb    = round(size_bytes / (1024 * 1024), 2)

    tags_raw = request.form.get("tags", "")
    tags     = [t.strip() for t in tags_raw.split(",") if t.strip()]

    images_col.insert_one({
        "filename":     unique_name,
        "image_url":    image_url,
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
        "size_kb":      size_kb,
        "size_mb":      size_mb,
        "upload_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uploaded_by":  session.get("username", "unknown")
    })
    flash("Image uploaded successfully!", "success")
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════════════════════

@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_image(filename):
    from bson import ObjectId

    img = images_col.find_one({"filename": filename})
    if not img:
        flash("Image not found.", "error")
        return redirect(url_for("index"))

    # Only uploader can delete
    if img.get("uploaded_by") != session.get("username"):
        flash("You can only delete your own images.", "error")
        return redirect(url_for("index"))

    # Remove local file
    local_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(local_path):
        os.remove(local_path)

    # ── AZURE BLOB delete (prod) ──────────────────────────
    # blob_client = blob_service.get_blob_client(container=BLOB_CONTAINER, blob=filename)
    # blob_client.delete_blob()

    images_col.delete_one({"filename": filename})
    flash("Image deleted.", "info")
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════
#  STATIC FILE SERVE (dev only)
# ══════════════════════════════════════════════════════════

@app.route("/display/<filename>")
def send_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5001)