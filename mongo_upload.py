import os
import shutil
from pymongo import MongoClient
from datetime import datetime

def process_upload(source_path):
    # 1. Setup Connection
    client = MongoClient("mongodb://localhost:27017/")
    db = client["Picsource_db"]
    collection = db["image_metadata"]

    try:
        # 2. Path Logic
        filename = os.path.basename(source_path)
        destination_path = os.path.join(os.getcwd(), filename)

        # 3. Move file to Root
        shutil.copy(source_path, destination_path)
        print(f"✅ File copied to root: {filename}")

        # 4. Save Metadata to MongoDB
        metadata = {
            "filename": filename,
            "size_bytes": os.path.getsize(destination_path),
            "upload_date": datetime.now(),
            "file_type": filename.split('.')[-1].lower()
        }
        
        result = collection.insert_one(metadata)
        print(f"✅ MongoDB Entry Created! ID: {result.inserted_id}")

    except Exception as e:
        print(f"❌ Error: {e}")

# --- EXECUTION ---
my_image = "D:/final year project(dessertation)/all projects/Cloud_nav/PicSource/uploads/1.png"

if os.path.exists(my_image):
    process_upload(my_image)
else:
    print("❌ Source image not found. Check your file path!")