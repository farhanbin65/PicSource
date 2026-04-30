import os
import sys

failed = []

try:
    import uuid
except Exception as e:
    failed.append(f"uuid: {e}")

try:
    from flask import Flask, render_template, request, redirect, url_for, session, flash
except Exception as e:
    failed.append(f"flask: {e}")

try:
    from flask_wtf.csrf import CSRFProtect
except Exception as e:
    failed.append(f"flask_wtf: {e}")

try:
    from werkzeug.security import generate_password_hash, check_password_hash
except Exception as e:
    failed.append(f"werkzeug: {e}")

try:
    from pymongo import MongoClient
except Exception as e:
    failed.append(f"pymongo: {e}")

try:
    from azure.storage.blob import BlobServiceClient
except Exception as e:
    failed.append(f"azure.storage.blob: {e}")

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    failed.append(f"dotenv: {e}")

try:
    from pymongo import MongoClient
    client = MongoClient(os.environ.get("COSMOS_URI"))
    db = client["Picsource_db"]
except Exception as e:
    failed.append(f"mongodb connect: {e}")

try:
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(conn_str)
except Exception as e:
    failed.append(f"blob connect: {e}")

app = Flask(__name__)

@app.route("/")
def index():
    if failed:
        return "<br>".join(["FAILED IMPORTS:"] + failed), 500
    return "PicSource: all imports OK!"

if __name__ == "__main__":
    app.run()