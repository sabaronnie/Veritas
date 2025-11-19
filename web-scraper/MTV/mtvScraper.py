import requests
import json
import os
import sys
from datetime import datetime

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from cleaning import clean_text, clean_url

url = "https://www.mtv.com.lb/en/api/articles?start=0&end=102000&type="
response = requests.get(url)
data = response.json()

# Output path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(BASE_DIR, "../../data/mtv_articles.jsonl")

scraped_at = datetime.utcnow().isoformat() + "Z"
    
with open(out_path, "w", encoding="utf-8") as f:
    for item in data:
        article_entry = {
            "source": "MTV",
            "url": "https://www.mtv.com.lb" + item.get("Url", ""),
            "title": item.get("title"),
            "text": clean_text(item.get("Text")),
            "section": item.get("articletype"),
            "image_url": item.get("MediaUrl"),
            "author": None,
            "published_at": item.get("publishDate") + "Z",
            "scraped_at": scraped_at
        } 

        # Write ONE json object per line
        f.write(json.dumps(article_entry, ensure_ascii=False) + "\n")
        


print(f"Saved {len(data)} records to {out_path}")