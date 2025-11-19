"""
Veritas - Cross-Source Comparison Module
----------------------------------------
Compares factual claims extracted from multiple news outlets to detect:
✅ Core (agreement)
🟡 Partial (overlap)
⚠ Disputed (contradiction)

Implements:
  - Entity-based prefiltering
  - Date-based filtering (±2 days)
  - Sentence-BERT semantic similarity
  - Sentiment-based contradiction detection
  - Graph clustering (NetworkX) to group same-event claims
"""

import os
import json
from itertools import combinations
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import networkx as nx
from datetime import datetime, timedelta
from tqdm import tqdm

# ======== CONFIG ========
CLAIM_DIR = "data/claims"
SAVE_DIR = "data/events"
os.makedirs(SAVE_DIR, exist_ok=True)

# ======== MODELS ========
print("🧠 Loading models...")
model = SentenceTransformer("all-MiniLM-L6-v2")
sentiment_model = pipeline("sentiment-analysis")

# ======== HELPERS ========

def parse_date(datestr):
    """
    Safely parse ISO or textual date formats.
    """
    if not datestr:
        return None
    try:
        # Handle ISO or YYYY-MM-DD
        return datetime.fromisoformat(datestr.replace("Z", ""))
    except Exception:
        try:
            return datetime.strptime(datestr[:10], "%Y-%m-%d")
        except Exception:
            return None


def same_time_window(c1, c2, days=2):
    """
    Compare if two claims are from articles within ±days of each other.
    """
    d1, d2 = parse_date(c1.get("date", "")), parse_date(c2.get("date", ""))
    if not d1 or not d2:
        return True  # If date missing, don't block comparison
    return abs((d1 - d2).days) <= days


def same_topic(c1, c2):
    """
    Basic filter: compare only if claims share at least one entity keyword.
    """
    set1 = set(map(str.lower, c1.get("entities", [])))
    set2 = set(map(str.lower, c2.get("entities", [])))
    return len(set1.intersection(set2)) >= 1


def sentiment_polarity(sentence):
    """
    Get sentiment label: POSITIVE, NEGATIVE, or NEUTRAL
    """
    try:
        res = sentiment_model(sentence[:512])[0]
        return res["label"]
    except Exception:
        return "NEUTRAL"


def detect_contradiction(c1, c2, sim_score):
    """
    Detect potential contradictions between two semantically similar sentences
    based on polarity differences or negation keywords.
    """
    neg_words = {"not", "no", "never", "deny", "denied", "rejected", "false"}
    s1, s2 = c1["sentence"].lower(), c2["sentence"].lower()

    neg1 = any(w in s1 for w in neg_words)
    neg2 = any(w in s2 for w in neg_words)

    pol1 = sentiment_polarity(c1["sentence"])
    pol2 = sentiment_polarity(c2["sentence"])

    contradictory = (
        sim_score > 0.6
        and ((neg1 != neg2) or (pol1 != pol2))
    )
    return contradictory


def load_all_claims():
    """
    Load all claim-level data from data/claims/
    """
    all_claims = []
    for file in os.listdir(CLAIM_DIR):
        if file.endswith(".json"):
            with open(os.path.join(CLAIM_DIR, file), "r", encoding="utf-8") as f:
                articles = json.load(f)
                for a in articles:
                    for c in a.get("claims", []):
                        all_claims.append({
                            "source": a["source"],
                            "title": a["title"],
                            "sentence": c["sentence"],
                            "entities": c.get("entities", []),
                            "date": a.get("date", "")
                        })
    print(f"📄 Loaded {len(all_claims)} total claims.")
    return all_claims


# ======== MAIN COMPARISON LOGIC ========

def compare_claims(all_claims):
    """
    Compare claims pairwise across sources using semantic similarity,
    entity and date filtering.
    """
    comparisons = []
    pairs = list(combinations(all_claims, 2))

    for c1, c2 in tqdm(pairs, desc="Comparing cross-source claims"):
        if c1["source"] == c2["source"]:
            continue
        if not same_topic(c1, c2):
            continue
        if not same_time_window(c1, c2, days=2):
            continue

        emb1 = model.encode(c1["sentence"], convert_to_tensor=True)
        emb2 = model.encode(c2["sentence"], convert_to_tensor=True)
        sim = util.cos_sim(emb1, emb2).item()

        label = None
        if detect_contradiction(c1, c2, sim):
            label = "Disputed"
        elif sim > 0.85:
            label = "Core"
        elif sim > 0.65:
            label = "Partial"

        if label:
            comparisons.append({
                "claim1": c1,
                "claim2": c2,
                "similarity": round(sim, 3),
                "label": label
            })

    print(f"🔎 Found {len(comparisons)} significant cross-source matches.")
    return comparisons


# ======== EVENT CLUSTERING ========

def cluster_events(comparisons):
    """
    Build a graph of claims and cluster them into same-event groups.
    """
    G = nx.Graph()

    for comp in comparisons:
        s1 = comp["claim1"]["sentence"]
        s2 = comp["claim2"]["sentence"]
        G.add_node(s1, **comp["claim1"])
        G.add_node(s2, **comp["claim2"])
        G.add_edge(s1, s2, weight=comp["similarity"], label=comp["label"])

    clusters = list(nx.connected_components(G))
    events = []

    for i, cluster in enumerate(clusters, 1):
        cluster_claims = [G.nodes[n] for n in cluster]
        edges = [G.edges[e] for e in G.edges(cluster)]
        avg_sim = sum(e["weight"] for e in edges) / max(len(edges), 1)
        labels = [e["label"] for e in edges]
        if not cluster_claims:
            continue
        events.append({
            "event_id": f"event_{i}",
            "claims": cluster_claims,
            "average_similarity": round(avg_sim, 3),
            "dominant_label": max(set(labels), key=labels.count) if labels else "Unknown"
        })

    print(f"🧩 Formed {len(events)} event clusters.")
    return events


# ======== MAIN PIPELINE ========

def main():
    print("🚀 Starting Veritas cross-source comparison pipeline...")
    all_claims = load_all_claims()
    comparisons = compare_claims(all_claims)
    events = cluster_events(comparisons)

    save_path = os.path.join(SAVE_DIR, "events_clusters.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done. Saved {len(events)} clustered events.")
    print(f"📁 Output file: {save_path}")


if __name__ == "__main__":
    main()
