import os
import sys
import json
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

from specific_scrapers import scrape_961

# ---------------------------------------------------------
# IMPORT LOCAL HELPERS
# ---------------------------------------------------------
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from timestamp_standard import parse_timestamp
from cleaning import clean_text, clean_url
from loadToDb import insert_one_article

# ---------------------------------------------------------
# ENV & DB SETUP
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(BASE_DIR + "/../secrets.env")

print(BASE_DIR)
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
print(DB_NAME)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_col = db["articles"]

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

BASE_CATEGORY_URL = "https://www.the961.com/{}/page/{}/"

CATEGORIES = {
    "news": "news",
    "travel": "travel",
    "lifestyle": "lifestyle",
    "fooddrink": "food-drink",
    "thingstodo": "things-to-do",
    "diaspora": "diaspora",
}

# ⏳ STOP if article older than this
MAX_AGE_HOURS = 24 # configurable


# ---------------------------------------------------------
# ID & VALIDATION
# ---------------------------------------------------------
def generate_article_id(source, url):
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{source.lower()}_{h}"


def validate_article(article):
    required = ["source", "url", "title", "published_at", "scraped_at"]

    for key in required:
        if key not in article or article[key] is None or str(article[key]).strip() == "":
            return False, f"Missing: {key}"

    if article.get("text") is None:
        article["text"] = ""

    # Validate timestamp
    try:
        dt = datetime.fromisoformat(article["published_at"].replace("Z", "").replace("+00:00", ""))
        if dt.year < 2023:
            return False, f"Too old: {dt.year}"
    except:
        return False, "Invalid timestamp format"

    return True, "OK"


def is_too_old(published_at):
    """Return True if article is older than MAX_AGE_HOURS."""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "").replace("+00:00", ""))
        age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
        return age_hours > MAX_AGE_HOURS
    except:
        return False


# ---------------------------------------------------------
# SCRAPE URL LISTING PAGE
# ---------------------------------------------------------
def extract_urls_from_listing(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = []

    for a in soup.select("h2.post-title a, h2.is-title.post-title a"):
        href = a.get("href")
        if href and href.startswith("https://www.the961.com/"):
            urls.append(href)

    return urls



# ---------------------------------------------------------
# SAVE TO DB
# ---------------------------------------------------------
def save_article_to_db(article):
    try:
        articles_col.insert_one(article)
        print(f"    [+] Inserted → {article['article_id']}")
    except Exception as e:
        print(f"    [!] Insert error: {e}")


# ---------------------------------------------------------
# MAIN CATEGORY SCRAPER
# ---------------------------------------------------------
def scrape_category(category_key, max_pages=3000):
    category_slug = category_key.lower()

    print(f"\n===============================")
    print(f"[SCRAPING CATEGORY] {category_slug}")
    print(f"===============================")

    page = 1
    while True:
        url = BASE_CATEGORY_URL.format(category_slug, page)
        print(f"\n[Page {page}] {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except Exception:
            print("[!] Failed to load page — stopping category.")
            break

        if r.status_code != 200:
            print("[!] HTTP error — stopping category.")
            break

        urls = extract_urls_from_listing(r.text)
        if not urls:
            print("[!] No articles on this page — done.")
            break

        print(f"  → Found {len(urls)} article URLs")

        for link in urls:
            # check duplicate
            aid = generate_article_id("961News", link)
            if articles_col.find_one({"article_id": aid}):
                print(f"    [-] Exists (skip) {link}")
                continue

            print(f"    [*] Scraping {link}")

            article = scrape_961(link, CATEGORIES.get(category_key, category_key))

            pub = article["published_at"]

            # Convert ISO timestamp → datetime
            dt = datetime.fromisoformat(pub.replace("Z", "").replace("+00:00", ""))

            # Compute age in hours
            age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
            if age_hours > MAX_AGE_HOURS:
                print(f"    [STOP] Article too old ({age_hours:.1f}h) → stopping category.")
                return

            if article:
                insert_one_article(article)
                #save_article_to_db(article)

            time.sleep(0.5)

        page += 1


# ---------------------------------------------------------
# RUN ALL CATEGORIES
# ---------------------------------------------------------
if __name__ == "__main__":
    for cat in CATEGORIES.keys():
        scrape_category(cat)

    print("\n[✓] ALL CATEGORIES COMPLETE\n")