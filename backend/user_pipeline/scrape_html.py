import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from trafilatura import extract as trafilatura_extract
import os
import sys
# ======================================================
# IMPORT CUSTOM SCRAPERS (edit these imports ONLY if needed)
# ======================================================

from backend.user_pipeline.specific_scrapers import scrape_almanar, scrape_961, scrape_lbc_article, scrape_mtv


# ======================================================
# DOMAIN ROUTER
# ======================================================
def choose_scraper(url):
    domain = urlparse(url).netloc.lower()

    if "almanar" in domain:
        return "almanar"

    if "961" in domain or "the961" in domain:
        return "961"

    if "lbcgroup" in domain or domain.startswith("lbc"):
        return "lbc"

    if "mtv.com.lb" in domain or "mtv" in domain:
        return "mtv"

    return "universal"


# ======================================================
# UNIVERSAL SCRAPER HELPERS
# ======================================================
def extract_metadata(soup):
    """Extract metadata fields like title, date, author."""
    def get_meta(names):
        for n in names:
            tag = soup.find("meta", {"property": n}) or soup.find("meta", {"name": n})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    return {
        "title": get_meta(["og:title", "twitter:title", "title"]),
        "publish_date": get_meta([
            "article:published_time", "article:modified_time",
            "date", "publish_date", "datePublished", "dateCreated"
        ]),
        "author": get_meta(["author", "article:author", "twitter:creator"]),
        "description": get_meta(["og:description", "description"])
    }


def extract_jsonld(soup):
    """Extract structured metadata from JSON-LD script tags."""
    scripts = soup.find_all("script", type="application/ld+json")
    result = {}

    for script in scripts:
        try:
            data = json.loads(script.string)

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") in ["Article", "NewsArticle", "BlogPosting"]:
                        data = item
                        break

            if isinstance(data, dict) and data.get("@type") in ["Article", "NewsArticle", "BlogPosting"]:
                result["title"] = data.get("headline")
                result["publish_date"] = data.get("datePublished")

                author = data.get("author")
                if isinstance(author, dict):
                    result["author"] = author.get("name")
                else:
                    result["author"] = author

                result["description"] = data.get("description")
                return result

        except:
            continue

    return result


def extract_heuristic_text(soup):
    """Try <article> tag or divs that look like content."""
    article_tag = soup.find("article")
    if article_tag:
        return article_tag.get_text(" ", strip=True)

    candidates = soup.find_all(
        ["div", "section"],
        class_=lambda c: c and isinstance(c, str) and any(
            k in c.lower() for k in ["article", "content", "post", "story", "main"]
        )
    )

    if candidates:
        largest = max(candidates, key=lambda c: len(c.get_text(strip=True)))
        return largest.get_text(" ", strip=True)

    return None


def extract_main_image(soup):
    """Get main article image from OG tags or HTML."""
    og = soup.find("meta", {"property": "og:image"})
    if og and og.get("content"):
        return og["content"]

    article_img = soup.find("article")
    if article_img:
        img = article_img.find("img")
        if img and img.get("src"):
            return img["src"]

    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]

    return None


def extract_date_regex(html_text):
    """Extract dates in multiple common formats."""
    patterns = [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{4}/\d{2}/\d{2})\b",
        r"\b(\d{4}\.\d{2}\.\d{2})\b"
    ]
    for p in patterns:
        match = re.search(p, html_text)
        if match:
            return match.group(1)
    return None


# ======================================================
# UNIVERSAL SCRAPER
# ======================================================
def universal_scraper(url):
    """Fallback scraper for any website not in the Lebanese set."""
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    # 1) metadata
    metadata = extract_metadata(soup)

    # 2) JSON-LD fallbacks
    jsonld = extract_jsonld(soup)
    for key, value in jsonld.items():
        if value and not metadata.get(key):
            metadata[key] = value

    # 3) fallback title
    if not metadata.get("title") and soup.title:
        metadata["title"] = soup.title.get_text(strip=True)

    # 4) fallback publish_date
    if not metadata.get("publish_date"):
        guess = extract_date_regex(html)
        if guess:
            metadata["publish_date"] = guess

    # 5) fallback author
    if not metadata.get("author"):
        author_tag = soup.find(["span", "div"], class_=lambda c: c and "author" in c.lower())
        if author_tag:
            metadata["author"] = author_tag.get_text(" ", strip=True)

    # 6) image extraction
    metadata["image_url"] = extract_main_image(soup)

    # 7) article text
    text = extract_heuristic_text(soup)

    if not text or len(text) < 200:
        tr_text = trafilatura_extract(html, include_comments=False)
        if tr_text and len(tr_text) > (len(text) if text else 0):
            text = tr_text

    if not text:
        body = soup.find("body")
        text = body.get_text(" ", strip=True) if body else html[:5000]

    # 8) fallback description
    if not metadata.get("description"):
        metadata["description"] = text[:200] if text else None

    # --------------------------------------------------
    # STANDARDIZED OUTPUT FORMAT
    # --------------------------------------------------
    return {
        "source": urlparse(url).netloc.lower(),
        "url": url,
        "title": metadata.get("title"),
        "text": text,
        "section": None,
        "image_url": metadata.get("image_url"),
        "author": metadata.get("author"),
        "published_at": metadata.get("publish_date"),
        "scraped_at": datetime.utcnow().isoformat() + "Z"
    }


# ======================================================
# MASTER ROUTER — CALL THIS ONE
# ======================================================
def scrape_article(url):
    """Main function — detects source and uses correct scraper."""
    site = choose_scraper(url)

    if site == "almanar":
        return scrape_almanar(url)

    if site == "961": 
        return scrape_961(url)

    if site == "lbc":
        return scrape_lbc_article(url)

    if site == "mtv":
        return scrape_mtv(url)

    return universal_scraper(url)


# ======================================================
# MANUAL TESTING
# ======================================================
# if __name__ == "__main__":
#     url = input("Enter article URL: ")
#     data = scrape_article(url)
#     print(json.dumps(data, indent=2, ensure_ascii=False))