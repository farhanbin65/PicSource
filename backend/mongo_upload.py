import os
import sys
from pymongo import MongoClient
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def process_upload(source_path):
    # Cosmos DB
    client     = MongoClient(os.environ.get("COSMOS_URI"))
    db         = client["Picsource_db"]
    collection = db["image_metadata"]

    # Azure Blob (Managed Identity)
    account          = os.environ.get("AZURE_STORAGE_ACCOUNT")
    container_name   = os.environ.get("BLOB_CONTAINER", "images")
    credential        = DefaultAzureCredential()
    blob_service      = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=credential
    )
    container_client  = blob_service.get_container_client(container_name)

    try:
        filename = os.path.basename(source_path)

        # Upload to Blob
        with open(source_path, "rb") as f:
            data = f.read()
        container_client.get_blob_client(filename).upload_blob(data, overwrite=True)
        print(f"Uploaded to Blob: {filename}")

        blob_url = f"https://{account}.blob.core.windows.net/{container_name}/{filename}"

        metadata = {
            "filename":    filename,
            "image_url":   blob_url,
            "size_bytes":  len(data),
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_type":   filename.rsplit(".", 1)[-1].lower()
        }
        result = collection.insert_one(metadata)
        print(f"Cosmos DB entry created. ID: {result.inserted_id}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python mongo_upload.py <path/to/image>")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)
    process_upload(path)