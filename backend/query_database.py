import os
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# TF-IDF imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# ENV + DB INIT
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(BASE_DIR + "/secrets.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]


# ============================================================
# Utility: Normalize string
# ============================================================
def clean(s):
    if not s:
        return ""
    return " ".join(str(s).split())


# ============================================================
# Utility: Parse ISO datetime consistently (fixes your error)
# ============================================================
def parse_dt(dt_str):
    """
    Always returns a timezone-aware UTC datetime.
    Supports timestamps like:
    - "2025-11-29T11:30:00Z"
    - "2025-11-29T11:30:00"
    """
    if not dt_str:
        return None

    # Convert "Z" → "+00:00" for Python compatibility
    dt_str = dt_str.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(dt_str)
    except Exception:
        return None

    # Ensure TZ-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


# ============================================================
# 1. FAST TF-IDF TOPICAL SIMILARITY
# ============================================================
def tfidf_similarity(text1, text2):
    text1 = clean(text1)
    text2 = clean(text2)

    if not text1 or not text2:
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english")

    try:
        tfidf = vectorizer.fit_transform([text1, text2])
    except ValueError:
        return 0.0  # Happens if text becomes empty after stopwords

    sim = cosine_similarity(tfidf[0:1], tfidf[1:2])
    return float(sim[0][0])


# ============================================================
# 2. VERY LIGHT ENTITY EXTRACTOR
# ============================================================
def extract_entities(text):
    """
    Extracts capitalized words (naive NER) — good enough for news.
    """
    if not text:
        return set()

    candidates = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)

    blacklist = {
        "The", "And", "But", "For", "That", "This", "What", "When", "Where",
        "Who", "Which", "It", "He", "She", "They", "A", "An", "In", "On"
    }

    return {c for c in candidates if c not in blacklist}


# ============================================================
# 3. EVENT RELEVANCE SCORING
# ============================================================
def compute_relevance(A, B):
    """
    Combines:
    - topical similarity
    - title similarity
    - entity overlap
    - time closeness
    """
    A_text = clean(A.get("text"))
    B_text = clean(B.get("text"))

    # Topical similarity (set earlier)
    text_sim = B.get("similarity_score", 0)

    # Title similarity (strong event signal)
    title_sim = tfidf_similarity(
        clean(A.get("title", "")),
        clean(B.get("title", ""))
    )

    # Entity overlap
    A_ent = extract_entities(A_text)
    B_ent = extract_entities(B_text)
    ent_sim = len(A_ent & B_ent) / (len(A_ent) + 1)

    # Time closeness
    A_dt = parse_dt(A["published_at"])
    B_dt = parse_dt(B["published_at"])

    if not A_dt or not B_dt:
        time_weight = 0
    else:
        hours_diff = abs((A_dt - B_dt).total_seconds()) / 3600
        time_weight = max(0, 1 - hours_diff / 24)  # 0 to 1

    # Weighted score
    score = (
        0.45 * text_sim +
        0.25 * title_sim +
        0.20 * ent_sim +
        0.10 * time_weight
    )

    return score


# ============================================================
# 4. KEEP ONLY TOP N BEST ARTICLES
# ============================================================
def reduce_to_top_results(A, articles, limit=15):
    for B in articles:
        B["final_relevance"] = compute_relevance(A, B)

    articles.sort(key=lambda x: x["final_relevance"], reverse=True)

    return articles[:limit]


# ============================================================
# 5. MAIN DATABASE QUERY PIPELINE
# ============================================================
def load_from_database(scraped_data, days_window=3, min_topic_sim=0.03, limit=15):
    """
    scraped_data = article A JSON
    Returns ~<limit> articles most similar to A within time window.
    """

    A = scraped_data

    # -- 1) Parse A publish date --
    A_dt = parse_dt(A["published_at"])
    if not A_dt:
        return []

    start_dt = A_dt - timedelta(days=days_window)
    end_dt   = A_dt + timedelta(days=days_window)

    # # -- 2) Query DB for time-matching articles --
    # raw_articles = list(db.articles.find({
    #     "published_at": {
    #         "$gte": start_dt.isoformat().replace("+00:00", "Z"),
    #         "$lte": end_dt.isoformat().replace("+00:00", "Z")
    #     },
    #     "source": {"$ne": A["source"]}   # Exclude same source
    # }))
    
    raw_articles = list(db.articles.find(
        {
            "published_at": {
                "$gte": start_dt.isoformat() + "Z",
                "$lte": end_dt.isoformat() + "Z"
            },
            "source": {"$ne": scraped_data["source"]}   # optional, if needed
        },
        {
            "_id": 0,          # REMOVE ObjectId
            "scraped_at": 0,   # REMOVE scraped timestamp
            "section": 0       # REMOVE section/category
        }
    ))

    if not raw_articles:
        return []

    # -- 3) Topical filter (TF-IDF) --
    filtered = []
    for B in raw_articles:
        sim = tfidf_similarity(A.get("text", ""), B.get("text", ""))
        if sim >= min_topic_sim:
            B["similarity_score"] = sim
            filtered.append(B)

    if not filtered:
        return []

    # -- 4) Event relevance scoring + ranking --
    final_results = reduce_to_top_results(A, filtered, limit)

    return final_results