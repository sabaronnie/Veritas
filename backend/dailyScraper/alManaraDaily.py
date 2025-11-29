import os
import sys
import re
import json
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# -------------------------------------------
# ENV
# -------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(BASE_DIR + "/../secrets.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_col = db["articles"]

# -------------------------------------------
# HELPERS
# -------------------------------------------
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from cleaning import clean_text
from timestamp_standard import parse_timestamp
from specific_scrapers import scrape_almanar
from loadToDb import insert_one_article

# -------------------------------------------
# CONFIG
# -------------------------------------------
BASE_URL = "https://english.almanar.com.lb/cat/news/page/{}"
PAGE_LIMIT = 5000
MAX_AGE_HOURS = 24
HEADERS = {"User-Agent": "Mozilla/5.0"}



# -------------------------------------------
# UTILITIES
# -------------------------------------------
def generate_article_id(source, url):
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{source.lower()}_{h}"


def is_too_old(published_at):
    """published_at MUST be ISO string."""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", ""))
        age = (datetime.utcnow() - dt).total_seconds() / 3600
        return age > MAX_AGE_HOURS
    except:
        return False


# -------------------------------------------
# EXTRACT URLS FROM CATEGORY PAGE
# -------------------------------------------
def extract_urls_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    # Pattern for article links: https://english.almanar.com.lb/903020
    pattern = re.compile(r"^https://english\.almanar\.com\.lb/\d+$")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if pattern.match(href):
            links.add(href)

    return list(links)




# -----------------------------------------
# MAIN SCRAPER
# -------------------------------------------
def scrape_manar():
    print("\n============= STARTING AL-MANAR SCRAPER =============\n")

    page = 1

    while page <= PAGE_LIMIT:

        # Stop at page 2204 (your old boundary)
        if page == 2204:
            print("Reached early 2020 — stopping.")
            break

        page_url = BASE_URL.format(page)
        print(f"[PAGE] {page}: {page_url}")

        try:
            r = requests.get(page_url, headers=HEADERS, timeout=10)
        except:
            print("[X] Failed to load page")
            break

        if r.status_code != 200:
            print("[X] HTTP error", r.status_code)
            break

        urls = extract_urls_from_html(r.text)
        if not urls:
            print("[!] No more articles — finished.")
            break

        print(f"    → Found {len(urls)} article URLs")

        for url in urls:
            # Generate unique ID
            article_id = generate_article_id("Al-Manar", url)

            # Duplicate check
            if articles_col.find_one({"article_id": article_id}):
                print(f"    [-] Exists (skip) {url}")
                continue

            print(f"    [*] Scraping {url}")

            # Scrape article page
            article = scrape_almanar(url)
            if not article:
                continue

            pub = article["published_at"]

            # Stop scraping entirely when too old
            if pub and is_too_old(pub):
                print(f"\n    [STOP] {url} older than {MAX_AGE_HOURS}h — ending scraper.\n")
                return

            insert_one_article(article)

            time.sleep(0.15)

        page += 1

    print("\n============= AL-MANAR SCRAPER COMPLETE =============\n")


# -------------------------------------------
# RUN
# -------------------------------------------
if __name__ == "__main__":
    scrape_manar()