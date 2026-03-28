import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# MONGODB SETUP
client = MongoClient("mongodb://localhost:27017/")
db = client["Picsource_db"]
collection = db["image_metadata"]

# Home Page
@app.route('/')
def index():
    images = list(collection.find())
    return render_template('index.html', images=images)

# Upload Page
@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

# Upload Logic
@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']

    if file.filename == '':
        return "No selected file"

    if file:
        # Save file inside uploads folder
        save_path = os.path.join(os.getcwd(), "uploads", file.filename)
        file.save(save_path)

        # Auto-calculate file size in KB and MB
        size_bytes = os.path.getsize(save_path)
        size_kb    = round(size_bytes / 1024, 2)
        size_mb    = round(size_bytes / (1024 * 1024), 2)

        # Tags: comma-separated string → clean list
        tags_raw = request.form.get('tags', '')
        tags = [tag.strip() for tag in tags_raw.split(',') if tag.strip()]

        metadata = {
            "filename":     file.filename,
            "title":        request.form.get('title', '').strip(),
            "description":  request.form.get('description', '').strip(),
            "category":     request.form.get('category', '').strip(),
            "type":         request.form.get('type', '').strip(),
            "format":       request.form.get('format', '').strip(),
            "resolution":   request.form.get('resolution', '').strip(),
            "photographer": request.form.get('photographer', '').strip(),
            "camera":       request.form.get('camera', '').strip(),
            "location":     request.form.get('location', '').strip(),
            "tags":         tags,
            "size_kb":      size_kb,
            "size_mb":      size_mb,          # auto-calculated from actual file
            "upload_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        collection.insert_one(metadata)
        return redirect(url_for('index'))

# Serve Images
@app.route('/display/<filename>')
def send_uploaded_file(filename):
    return send_from_directory(os.path.join(os.getcwd(), "uploads"), filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001)