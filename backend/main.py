from backend.user_pipeline.scrape_html import scrape_article
from backend.user_pipeline.model import analyze_article
from .query_database import load_from_database
from .formatters import map_analysis_to_response
import json
import os


def save_json(data, filename="analysis.json"):
    """
    Save JSON inside ../website/<filename>
    regardless of where main.py is called from.
    """

    # Get the directory of main.py (backend folder)
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    # Compute: ../website/
    website_dir = os.path.abspath(os.path.join(backend_dir, "..", "website"))

    # Ensure website directory exists
    os.makedirs(website_dir, exist_ok=True)

    # Full path: ../website/analysis.json
    save_path = os.path.join(website_dir, filename)

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved JSON to {save_path}")

def remove_unwanted_fields(articles):
    REMOVE_FIELDS = {
        "final_relevance",
        "similarity_score",
        "scraped_at",
        "section",
        "_id"
    }

    cleaned = []

    for art in articles:
        new_obj = {k: v for k, v in art.items() if k not in REMOVE_FIELDS}
        cleaned.append(new_obj)

    return cleaned

def remove_unwanted_fields_single(article):
    REMOVE_FIELDS = {"final_relevance", "similarity_score", "scraped_at", "section", "_id"}
    return {k: v for k, v in article.items() if k not in REMOVE_FIELDS}

def start_user_pipeline(url):
    
    scraped_data = scrape_article(url)
    #save_json(scraped_data, "scraped_article.json")   # OPTIONAL
    
    
    articles = load_from_database(scraped_data)
    #print(articles)

    articles = remove_unwanted_fields(articles)
    scraped_data = remove_unwanted_fields_single(scraped_data)
    
    results = analyze_article(scraped_data, articles)

    # Save RAW model output for auditing/debugging under backend/GPT_response.json
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(backend_dir, "GPT_response.json")
    try:
        with open(raw_path, "w", encoding="utf-8") as rf:
            json.dump(results, rf, ensure_ascii=False, indent=2)
        print(f"[✓] Saved raw model output to {raw_path}")
    except Exception as e:
        print(f"[!] Failed to save raw model output: {e}")

    # Map model output to frontend format and save to website/analysis.json
    mapped = map_analysis_to_response(results)
    save_json(mapped)
    return results


if __name__ == "__main__":
    # Example one-off run when executing this file directly
    start_user_pipeline("https://www.newarab.com/news/hezbollah-urges-pope-reject-israeli-aggression-lebanon")




