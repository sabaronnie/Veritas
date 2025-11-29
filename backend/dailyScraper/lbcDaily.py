import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os, sys
from specific_scrapers import scrape_lbc_article

from pymongo import MongoClient, InsertOne
from dotenv import load_dotenv

from loadToDb import insert_one_article
from timestamp_standard import parse_timestamp
# -------------------------
# Load ENV settings
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(BASE_DIR + "/secrets.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_col = db["articles"]

SCRAPE_HOURS = 24  # ⬅ CHANGE THIS to whatever you want (e.g. 72 for 3 days)
BASE_URL = "https://www.lbcgroup.tv/Website/DynamicPages/LoadMore/Loadmore_LatestNews.aspx"

OUTPUT_FILE = "lbc_articles.jsonl"
URL_FILE = "current_lbc_urls.txt"

# polite scraping delay
DELAY = 0.5


# -----------------------------
# UTILITIES
# -----------------------------
# def parse_lbc_timestamp(date_str):
#     """
#     Convert the LBC date format to ISO.
#     Examples:
#         '11/22/2025 03:25 PM' → '2025-11-22T15:25:00Z'
#     """
#     try:
#         dt = datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
#         return dt.replace(tzinfo=None).isoformat() + "Z"
#     except:
#         return None


def load_existing_urls():
    if not os.path.exists(URL_FILE):
        return set()
    with open(URL_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_new_url(url):
    with open(URL_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")


# -----------------------------
# FETCH PAGE FROM AJAX ENDPOINT
# -----------------------------
def fetch_page(loadindex):
    params = {
        "loadindex": loadindex,
        "lang": "en",
        "rnd": 1720,
        "mostreadperiod": "daily",
        "rownumber": 8
    }

    try:
        r = requests.get(BASE_URL, params=params, timeout=10)
        if r.status_code != 200:
            print(f"[!] HTTP {r.status_code} at loadindex={loadindex}")
            return ""
        return r.text.strip()
    except Exception as e:
        print(f"[ERROR] fetch_page: {e}")
        return ""


# -----------------------------
# PARSE ARTICLE URLs FROM AJAX BLOCK
# -----------------------------
def extract_article_urls(html_block):
    soup = BeautifulSoup(html_block, "html.parser")
    urls = []

    for link in soup.select("div.card-module-horizontal > a[href]"):
        href = link["href"]

        if href.startswith("http") and "/news/" in href:
            urls.append(href)

        elif "/news/" in href:
            urls.append("https://www.lbcgroup.tv" + href)

    return urls



# -----------------------------
# MAIN SCRAPER
# -----------------------------
def scrape_recent_articles():
    existing_urls = load_existing_urls()

    cutoff = datetime.utcnow() - timedelta(hours=SCRAPE_HOURS)
    print(f"[INFO] Scraping until articles older than {SCRAPE_HOURS} hours.")
    print(f"[INFO] Cutoff datetime: {cutoff.isoformat()}")

    loadindex = 0
    total_new = 0

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
        while True:
            print(f"[+] Fetching page index = {loadindex}")
            html = fetch_page(loadindex)

            if not html or len(html) < 30:
                print("[DONE] No more data or empty page.")
                break

            urls = extract_article_urls(html)
            if not urls:
                print("[STOP] No article URLs found on this page.")
                break

            for url in urls:
                if url in existing_urls:
                    print(f"   [-] Already scraped: {url}")
                    continue

                print(f"   [+] Scraping article: {url}")
                try:
                    article = scrape_lbc_article(url)

                    if not article["published_at"]:
                        print("       → No valid published date, skipping.")
                        continue

                    published_dt = datetime.fromisoformat(article["published_at"].replace("Z",""))

                    # STOP CONDITION: Article is older than cutoff
                    if published_dt < cutoff:
                        print("       → Article too old. Stopping scraper.")
                        return
                    
                    insert_one_article(article)

                    # Save article
                    # out.write(json.dumps(article, ensure_ascii=False) + "\n")
                    # out.flush()

                    existing_urls.add(url)
                    save_new_url(url)
                    total_new += 1

                    time.sleep(DELAY)

                except Exception as e:
                    print(f"   [ERROR scraping] {e}")
                    time.sleep(1)

            loadindex += 1
            #time.sleep(DELAY)

    print(f"[DONE] Scraped {total_new} new articles.")




# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    scrape_recent_articles()