
import os
import re
import json
import time
from datetime import datetime
import feedparser
from newspaper import Article
from langdetect import detect, LangDetectException


# ========== CONFIG ==========
news_sources = [
    {"name": "Al Jazeera", "rss": "https://www.aljazeera.com/xml/rss/all.xml", "bias": "center-left"},
    {"name": "An-Nahar", "rss": "https://www.annahar.com/rss", "bias": "independent"},
    {"name": "Al-Akhbar", "rss": "https://al-akhbar.com/rss.xml", "bias": "left-leaning, pro-resistance"},
    {"name": "Al-Joumhouria", "rss": "https://www.aljoumhouria.com/rss.xml", "bias": "independent"},
    {"name": "Al-Liwa", "rss": "https://aliwaa.com.lb/feed/", "bias": "Sunni-oriented"},
    {"name": "Ad-Diyar", "rss": "https://www.addiyar.com/rss.xml", "bias": "Arabic daily"},
    {"name": "Lebanon24", "rss": "https://www.lebanon24.com/Rss", "bias": "center"},
    {"name": "The961", "rss": "https://www.the961.com/feed/", "bias": "independent, English-language"}
]


SAVE_DIR = "data/raw"
os.makedirs(SAVE_DIR, exist_ok=True)


# ========== HELPERS ==========
def clean_text(text: str) -> str:
    """Basic cleaning to remove URLs, extra whitespace, and HTML junk."""
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("\xa0", " ").strip()
    return text


def is_valid_article(text: str) -> bool:
    """Check if article has enough words and is in English or Arabic."""
    try:
        lang = detect(text)
        return len(text.split()) > 100 and lang in ["en"]
    except LangDetectException:
        return False


def fetch_rss_articles(source):
    """Fetch article URLs from an RSS feed."""
    feed = feedparser.parse(source["rss"])
    entries = []
    for e in feed.entries:
        entries.append({
            "title": e.title,
            "url": e.link,
            "published": getattr(e, "published", ""),
            "source": source["name"],
            "bias": source["bias"]
        })
    return entries


def extract_full_article(entry):
    """Download and parse full article content using newspaper3k."""
    try:
        a = Article(entry["url"])
        a.download()
        a.parse()
        text = clean_text(a.text)

        if not is_valid_article(text):
            return None

        return {
            "source": entry["source"],
            "bias": entry["bias"],
            "title": a.title or entry["title"],
            "url": entry["url"],
            "date": str(a.publish_date or entry["published"]),
            "authors": a.authors,
            "text": text,
            "fetched_at": str(datetime.utcnow())
        }
    except Exception as e:
        print(f"[x] Failed to process {entry['url']} — {e}")
        return None


# ========== MAIN PIPELINE ==========
def main():
    print("🚀 Starting Veritas Data Pipeline...")
    all_articles = []

    for source in SOURCES:
        print(f"\n🔗 Fetching from {source['name']} ...")
        entries = fetch_rss_articles(source)
        print(f"  → Found {len(entries)} links.")

        for entry in entries:
            article = extract_full_article(entry)
            if article:
                all_articles.append(article)
                print(f"    ✅ Saved: {article['title'][:60]}")

            # Optional: prevent rate-limiting
            time.sleep(1)

    # Save all results as a daily JSON file
    today = datetime.now().strftime("%Y-%m-%d")
    save_path = os.path.join(SAVE_DIR, f"articles_{today}.json")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done. Collected {len(all_articles)} valid articles.")
    print(f"📁 Saved to: {save_path}")


if __name__ == "__main__":
    main()