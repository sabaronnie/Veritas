import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from backend.user_pipeline.timestamp_standard import parse_timestamp
from backend.user_pipeline.cleaning import clean_text, clean_url

def scrape_almanar(url):

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # ========== TITLE ==========
    title_el = soup.select_one(".article-title h2")
    title = title_el.get_text(strip=True) if title_el else ""

    # ========== PUBLICATION DATE ==========
    # Usually under .article-meta
    date_el = soup.select_one(".article-meta span:nth-of-type(2)")
    published_at = ""
    if date_el:
        raw_date = date_el.get_text(strip=True)
        try:
            published_dt = datetime.strptime(raw_date, "%B %d, %Y")
            published_at = published_dt.isoformat() + "Z"
        except:
            published_at = raw_date  # fallback

    # ========== SECTION ==========
    section_el = soup.select_one(".article-categories a")
    section = section_el.get_text(strip=True) if section_el else "Unknown"

    # ========== IMAGE ==========
    img_el = soup.select_one(".article-image img")
    image_url = img_el["src"] if img_el and img_el.get("src") else None

    # ========== BODY TEXT ==========
    body_el = soup.select_one(".article-content")
    paragraphs = []
    if body_el:
        for p in body_el.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)

    full_text = clean_text(" ".join(paragraphs))

    # ========== BUILD JSON ENTRY ==========
    scraped_at = datetime.utcnow().isoformat() + "Z"

    article_entry = {
        "source": "Al-Manar",
        "url": url,
        "title": title,
        "text": full_text,
        "section": section,
        "image_url": image_url,
        "author": None,
        "published_at": published_at,
        "scraped_at": scraped_at
    }

    return article_entry


HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_961(url, category="None"):
    r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
    #r = requests.get(url, headers=HEADERS, timeout=10)

    if r.status_code != 200:
        print(f"[!] Failed to fetch {url}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    title_tag = soup.select_one("h1.post-title, h1.is-title.post-title")
    title = title_tag.get_text(strip=True) if title_tag else None

    author_tag = soup.select_one("span.post-author a, span.meta-item.post-author a")
    author = author_tag.get_text(strip=True) if author_tag else None

    date_tag = soup.select_one("time.post-date")
    published_at = date_tag.get("datetime") if date_tag else None

    img_tag = soup.select_one("img.wp-post-image")
    image_url = img_tag.get("src") if img_tag else None

    paragraphs = []
    content = soup.select_one("div.entry-content, div.post-content")
    if content:
        for p in content.find_all("p"):
            text = clean_text(p.get_text(" ", strip=True))
            if text:
                paragraphs.append(text)

    full_text = "\n".join(paragraphs)

    scraped_at = datetime.utcnow().isoformat() + "Z"

    return {
        "source": "961News",
        "url": url,
        "title": clean_text(title),
        "text": clean_text(full_text),
        "section": category,
        "image_url": image_url,
        "author": author,
        "published_at": parse_timestamp(published_at, "961"),
        "scraped_at": scraped_at
    }
    
    
def scrape_lbc_article(url):
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    source = "LBC"
    scraped_at = datetime.utcnow().isoformat() + "Z"

    # TITLE
    title_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_lblTitle")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # DATE
    date_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_lblDate")
    
    print(date_tag)
    published_raw = date_tag.get_text(strip=True) if date_tag else ""
    published_at = parse_timestamp(published_raw, source)
    
    print("LBCCCC")
    print(published_at)

    # SECTION
    section_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_lblCatTitle")
    section = section_tag.get_text(strip=True) if section_tag else ""

    # IMAGE
    img_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsPresentation16_ArticleImage")
    image_url = img_tag["src"] if img_tag and img_tag.get("src") else None

    # SHORT DESCRIPTION
    short_tag = soup.select_one("#ctl00_MainContent_ArticleDetailsDescription15_lblShortDesc")
    short_text = short_tag.get_text(strip=True) if short_tag else ""

    # LONG DESCRIPTION + AUTHOR
    long_desc = soup.select_one(".LongDesc")
    long_paragraphs = []
    author = None

    if long_desc:
        for div in long_desc.find_all("div"):

            for junk in div.find_all(["bannerinjection", "controlinjection"]):
                junk.decompose()

            # AUTHOR
            em = div.find("em")
            if em:
                em_text = em.get_text(" ", strip=True)
                lower = em_text.lower()

                if "report by" in lower:
                    parts = em_text.split(",")
                    first_part = parts[0].strip()
                    author_name = first_part.replace("Report by", "").strip()
                    author = author_name
                    em.extract()

                else:
                    if lower.startswith("by "):
                        if "translated" not in lower and "adaptation" not in lower:
                            cleaned = em_text[3:].strip().strip(",. ")
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

    article = {
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

    return article


def scrape_mtv(url):
    response = requests.get(url)
    data = response.json()