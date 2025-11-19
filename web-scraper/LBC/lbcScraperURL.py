import requests
from bs4 import BeautifulSoup
import time
import json
import os

BASE_URL = "https://www.lbcgroup.tv/Website/DynamicPages/LoadMore/Loadmore_LatestNews.aspx"

def fetch_page(loadindex: int):
    """Fetch one page of article HTML blocks using the LBC AJAX endpoint."""
    params = {
        "loadindex": loadindex,
        "lang": "en",
        "rnd": 1720,             # can be any number, avoids caching
        "mostreadperiod": "daily",
        "rownumber": 8
    }

    try:
        r = requests.get(BASE_URL, params=params, timeout=10)
        if r.status_code == 200:
            return r.text.strip()
        else:
            print(f"[!] Failed on loadindex={loadindex}, status={r.status_code}")
            return ""
    except Exception as e:
        print(f"[ERROR] {e}")
        return ""


def extract_article_urls(html_block: str):
    """Extract article URLs from the returned HTML block."""
    soup = BeautifulSoup(html_block, "html.parser")
    urls = []

    # Usually <a href="..."> tags wrap the article boxes
    for link in soup.select('div.card-module-horizontal > a[href]'):
        url = link["href"]

        # Filter ONLY real article URLs
        if "/news/" in url and url.startswith("http"):
            urls.append(url)

        # Sometimes LBC uses relative URLs like "/news/en/123..."
        elif "/news/" in url:
            urls.append("https://www.lbcgroup.tv" + url)

    return urls

OUTPUT_FILE = "lbc_article_urls.txt"
def load_existing_urls():
    """Load URLs already saved earlier (if file exists)."""
    if not os.path.exists(OUTPUT_FILE):
        return set()

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())
    
def save_new_url(url):
    """Append a new URL to the file."""
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")
    
def scrape_all_article_urls(max_pages=2000):
    """Loop through paginated endpoint until no more articles appear."""
    existing_urls = load_existing_urls()
    all_urls = set()
    page = 1843

    while True:
        print(f"[+] Fetching loadindex={page} ...")
        html = fetch_page(page)
        #print(html)
        with open("lbc_html.json", "w", encoding="utf-8") as f:
            f.write(html)
        # Stop if empty/no more results
        if not html or len(html) < 30:
            print("[DONE] Reached the end of pagination.")
            break

        # Extract URLs from page
        urls = extract_article_urls(html)

        if not urls:
            print("[STOP] No URLs found on this page → stopping.")
            break

        print(f"    Found {len(urls)} URLs")

        # Add to set to avoid duplicates
        for u in urls:
            if u not in existing_urls:
                existing_urls.add(u)
                save_new_url(u)
                print(f"    [+] NEW: {u} (page = {page})")
            else:
                print(f"    [-] Already saved: {u} (page = {page})")
        # for u in urls:
        #     all_urls.add(u)

        page += 1
        time.sleep(0.5)  # stay polite and avoid rate limits

        if page >= max_pages:
            print("[WARNING] Max pages reached, stopping.")
            break
        
        # if page == 20:
        #     break

    return list(all_urls)


if __name__ == "__main__":
    urls = scrape_all_article_urls()

    print(f"\nTotal unique articles found: {len(urls)}")

    # Save to JSON
    # with open("lbc_article_urls.json", "w", encoding="utf-8") as f:
    #     json.dump(urls, f, ensure_ascii=False, indent=2)

    print("Saved to lbc_article_urls.json")