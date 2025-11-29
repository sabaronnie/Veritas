import json
import os
import hashlib
from datetime import datetime

from pymongo import MongoClient
from dotenv import load_dotenv


# -------------------------
# Load ENV settings
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(BASE_DIR + "/../secrets.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_col = db["articles"]


# -------------------------
# Helper: generate article ID
# -------------------------
import hashlib

#db["articles"].create_index("article_id", unique=True)
# result = db["articles"].delete_many({"source": "961News"})
# print(f"Deleted {result.deleted_count} documents with source=961News.")

def generate_article_id(source, url, published_at):
    base = f"{source.lower()}||{url.strip()}||{published_at.strip()}"
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return f"{source.lower()}_{h}"

# -------------------------
# Validate one article
# -------------------------
def validate_article(article):
    required_non_null = ["source", "url", "title", "published_at", "scraped_at"]

    for key in required_non_null:
        if key not in article or article[key] is None or str(article[key]).strip() == "":
            return False, f"Missing or empty required field: {key}"

    # Fix null text
    if article.get("text") is None:
        article["text"] = ""

    if not isinstance(article["text"], str):
        return False, "Text is not a string"

    # URL format
    if not isinstance(article["url"], str) or not article["url"].startswith("http"):
        return False, "Invalid URL"

    # published_at timestamp validation
    ts = article["published_at"]
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "").replace("+00:00", ""))
    except Exception:
        return False, f"Invalid datetime format: {ts}"

    if dt.year < 2023:
        return False, f"Too old (year {dt.year}), must be 2023 or later"

    return True, "OK"


# -------------------------
# Insert ONE article
# -------------------------
def insert_one_article(article_json):
    """article_json can be a dict or string"""

    # If input is a string → parse JSON
    if isinstance(article_json, str):
        try:
            article = json.loads(article_json)
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON format"}

    else:
        article = article_json

    # Validate
    ok, msg = validate_article(article)
    if not ok:
        return {"success": False, "error": msg}

    # Add article_id
    article["article_id"] = generate_article_id(article["source"], article["url"], article["published_at"])
    # Insert into DB
    try:
        result = articles_col.insert_one(article)
        print("Successfully inserted article")
    except Exception as e:
        msg = str(e)

        if "duplicate key" in msg:
            print("Duplicate Found, not inserting")
            

# -------------------------
# MAIN (stdin mode)
# -------------------------
# if __name__ == "__main__":
#     import sys

#     raw_input = sys.stdin.read().strip()
#     if not raw_input:
#         print("❌ No JSON input provided.")
#         sys.exit(1)

#     result = insert_one_article(raw_input)
#     print(json.dumps(result, indent=2))