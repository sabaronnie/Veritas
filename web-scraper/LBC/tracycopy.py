import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from timestamp_standard import parse_timestamp

# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL_FILE = "lbc_article_urls.txt"
OUTPUT_FILE = "lbc_articles.jsonl"

START_INDEX = 36999  # start from this index and go backwards


# -----------------------------
# CLEANING HELPERS
# -----------------------------
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)
    replacements = {
        "’": "'", "‘": "'", "‚": "'",
        "“": '"', "”": '"', "„": '"'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def clean_url(url):
    if not url:
        return None
    url = url.strip()
    url = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", url)
    url = url.replace("\xa0", "")
    return url


# -----------------------------
# SCRAPER
# -----------------------------
def scrape_lbc_article(url):
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    source = "LBC"
    scraped_at = datetime.utcnow().isoformat() + "Z"

    title_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_lblTitle")
    title = title_tag.get_text(strip=True) if title_tag else ""

    date_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_lblDate")
    published_raw = date_tag.get_text(strip=True) if date_tag else ""
    published_at = parse_timestamp(published_raw, source)

    section_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_lblCatTitle")
    section = section_tag.get_text(strip=True) if section_tag else ""

    img_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_ArticleImage")
    image_url = img_tag["src"] if img_tag and img_tag.get("src") else None

    short_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsDescription15_lblShortDesc")
    short_text = short_tag.get_text(strip=True) if short_tag else ""

    long_desc = soup.select_one(".LongDesc")
    long_paragraphs = []
    author = None

    if long_desc:
        for div in long_desc.find_all("div"):

            for junk in div.find_all(["bannerinjection", "controlinjection"]):
                junk.decompose()

            em = div.find("em")
            if em:
                em_text = em.get_text(" ", strip=True).lower()
                original = em.get_text(" ", strip=True)

                if "report by" in em_text:
                    author = original.replace("Report by", "").split(",")[0].strip()
                    em.extract()
                elif em_text.startswith("by "):
                    cleaned = original[3:].strip().strip(",. ")
                    blacklist = ["reuters", "afp", "associated press", "ap"]
                    if cleaned.lower() not in blacklist:
                        author = cleaned
                    em.extract()

            for br in div.find_all("br"):
                br.replace_with("\n")

            text = div.get_text(" ", strip=True)
            if text:
                long_paragraphs.append(text)

    full_text = (short_text + "\n" + "\n".join(long_paragraphs)).strip()

    return {
        "source": source,
        "url": clean_url(url),
        "title": clean_text(title),
        "text": clean_text(full_text),
        "section": clean_text(section),
        "image_url": clean_url(image_url),
        "author": clean_text(author) if author else None,
        "published_at": published_at,
        "scraped_at": scraped_at
    }


# -----------------------------
# LOAD URL LIST
# -----------------------------
with open(URL_FILE, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

total = len(urls)
print(f"Loaded {total} URLs.")
print(f"Starting from index {START_INDEX}")


# -----------------------------
# LOAD EXISTING SCRAPED URLS (FAST SET)
# -----------------------------
already = set()
if os.path.exists(OUTPUT_FILE):
    print("Loading existing scraped URLs...")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                u = obj.get("url")
                if u:
                    already.add(u)
            except:
                pass

print(f"Already scraped: {len(already)} URLs.\n")


# -----------------------------
# MAIN SCRAPING LOOP (BACKWARDS)
# -----------------------------
with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
    for file_index in range(START_INDEX, 0, -1):

        url = urls[file_index - 1]  # because list is 0-indexed

        print(f"Scraping {file_index} / {total} → {url}")

        if url in already:
            print("   → Already scraped, skipping.")
            continue

        try:
            article = scrape_lbc_article(url)
            out.write(json.dumps(article, ensure_ascii=False) + "\n")
            out.flush()

            already.add(url)

            time.sleep(0.7)

        except Exception as e:
            print("   → FAILED:", e)
            time.sleep(3)

print("Done.")