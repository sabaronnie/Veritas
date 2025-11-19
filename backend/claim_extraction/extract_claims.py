"""
Veritas - Claim Extraction Module
---------------------------------
Extracts structured factual claims from scraped news articles:
  - Splits text into factual sentences
  - Extracts key entities (Who, What, When, Where, How much)
  - Prepares JSON data for Cross-Source Comparison
"""

import os
import json
import re
from datetime import datetime
import spacy
from transformers import pipeline
from tqdm import tqdm

# ======== CONFIG ========
RAW_DIR = "data/raw"
SAVE_DIR = "data/claims"
os.makedirs(SAVE_DIR, exist_ok=True)

# ======== MODELS ========
print("🧠 Loading NLP models...")
nlp = spacy.load("en_core_web_sm")  # POS tagging, sentence segmentation, dependency parsing
ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

# ======== HELPERS ========

def clean_sentence(sentence: str) -> str:
    """
    Basic text cleaning — remove extra whitespace and junk.
    """
    sentence = re.sub(r"http\S+", "", sentence)
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.strip()


def extract_entities(sentence: str):
    """
    Extract entities (Who, What, When, Where, How much) using NER.
    """
    entities = {
        "WHO": [],
        "WHAT": [],
        "WHEN": [],
        "WHERE": [],
        "HOW_MUCH": []
    }

    results = ner(sentence)
    for r in results:
        label = r["entity_group"]
        text = r["word"]

        if label in ["PER", "ORG"]:
            entities["WHO"].append(text)
        elif label in ["LOC", "GPE"]:
            entities["WHERE"].append(text)
        elif label in ["DATE", "TIME"]:
            entities["WHEN"].append(text)
        elif label == "MONEY":
            entities["HOW_MUCH"].append(text)
        else:
            entities["WHAT"].append(text)

    # Remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))

    return entities


def extract_claims_from_text(text: str):
    """
    Split article into sentences and extract structured factual claims.
    """
    doc = nlp(text)
    claims = []

    for sent in doc.sents:
        sentence = clean_sentence(sent.text)
        if len(sentence.split()) < 6:  # ignore very short sentences
            continue

        entities = extract_entities(sentence)
        total_entities = sum(len(v) for v in entities.values())

        # Only keep sentences with enough factual info
        if total_entities >= 2:
            claims.append({
                "sentence": sentence,
                "entities": list(set(
                    entities["WHO"] + entities["WHAT"] + entities["WHEN"] + entities["WHERE"] + entities["HOW_MUCH"]
                )),
                "structure": entities
            })
    return claims


# ======== MAIN PIPELINE ========

def process_articles():
    print("🚀 Starting claim extraction...")
    for file in os.listdir(RAW_DIR):
        if not file.endswith(".json"):
            continue

        path = os.path.join(RAW_DIR, file)
        with open(path, "r", encoding="utf-8") as f:
            articles = json.load(f)

        processed_articles = []

        for a in tqdm(articles, desc=f"Processing {file}"):
            text = a.get("text", "")
            if not text.strip():
                continue

            claims = extract_claims_from_text(text)
            if claims:
                processed_articles.append({
                    "source": a["source"],
                    "bias": a["bias"],
                    "title": a["title"],
                    "url": a["url"],
                    "date": a.get("date", ""),
                    "claims": claims
                })

        # Save extracted claims
        save_path = os.path.join(SAVE_DIR, f"claims_{file}")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(processed_articles, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved {len(processed_articles)} processed articles → {save_path}")


if __name__ == "__main__":
    process_articles()
