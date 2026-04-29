import os
import sys
import shutil
from pymongo import MongoClient
from datetime import datetime

def process_upload(source_path):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["Picsource_db"]
    collection = db["image_metadata"]

    try:
        filename = os.path.basename(source_path)
        destination_path = os.path.join(os.getcwd(), filename)

        shutil.copy(source_path, destination_path)
        print(f"File copied to: {destination_path}")

        metadata = {
            "filename": filename,
            "size_bytes": os.path.getsize(destination_path),
            "upload_date": datetime.now(),
            "file_type": filename.rsplit(".", 1)[-1].lower()
        }

        result = collection.insert_one(metadata)
        print(f"MongoDB entry created. ID: {result.inserted_id}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python mongo_upload.py <path/to/image>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        sys.exit(1)

    process_upload(image_path)
