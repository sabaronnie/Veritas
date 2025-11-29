"""Shared response formatting utilities for Veritas.

Contains a single function `map_analysis_to_response` which converts the
internal model output JSON into the frontend-friendly shape used by the
static site and extension.
"""
from typing import Any, Dict
import re


def map_analysis_to_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert internal GPT analysis JSON into the frontend's expected format.

    This is a straight port of the mapping logic previously living inside
    `veritas_api.py`. Keeping it in a small, importable module avoids
    importing FastAPI when we only need the formatter (e.g., from scripts).
    """
    claims = []
    for c in raw.get("claims_in_A", []):
        matches = []
        for comp in c.get("comparisons", []):
            mtype = (comp.get("match_type") or "").lower()
            verdict = (
                "entailment" if mtype in ("support", "agreement")
                else "contradiction" if mtype == "contradiction"
                else "neutral"
            )

            matches.append({
                "source": comp.get("source"),
                "text": comp.get("article_title") or comp.get("matched_claim_text", ""),
                # Use provided similarity/confidence when present; do NOT fall back to constants
                "similarity": comp.get("similarity"),
                "nli_verdict": verdict,
                "nli_confidence": comp.get("nli_confidence"),
                "timestamp": comp.get("published_at") or comp.get("timestamp")
            })

        claims.append({
            "text": c.get("claim_text", ""),
            "matches": matches
        })

    # STATS
    stats = {
        "total_claims": len(claims),
        "verified_claims": sum(any(m["nli_verdict"] == "entailment" for m in cl["matches"]) for cl in claims),
        "disputed_claims": sum(any(m["nli_verdict"] == "contradiction" for m in cl["matches"]) for cl in claims),
        # avg_confidence will be computed below from per-match nli_confidence values
        "avg_confidence": None,
        "sources_used": len({m["source"] for cl in claims for m in cl["matches"] if m.get("source")})
    }

    agreement_values = [c.get("agreement_pct") for c in raw.get("claims_in_A", []) if c.get("agreement_pct") is not None]
    stats["agreement_pct"] = sum(agreement_values) / len(agreement_values) if agreement_values else None

    bias = raw.get("bias_analysis", {})
    stats["overall_bias_score"] = bias.get("overall_bias_score")

    # Compute avg_confidence from available match confidences (0.0-1.0)
    confidences = [
        m.get("nli_confidence") for cl in claims for m in cl.get("matches", [])
        if isinstance(m.get("nli_confidence"), (int, float))
    ]
    if confidences:
        try:
            stats["avg_confidence"] = sum(confidences) / len(confidences)
        except Exception:
            stats["avg_confidence"] = None

    # Derive article title and timestamp from multiple possible keys
    title = raw.get("article_title") or raw.get("title") or None
    if not title and isinstance(raw.get("article"), dict):
        title = raw.get("article").get("title")

    # Prefer explicit model-provided fields if present
    source = raw.get("current_source") or raw.get("source") or (raw.get("article") or {}).get("source") or "unknown"

    timestamp = (
        raw.get("user_published_at") or raw.get("published_at") or raw.get("publish_date") or raw.get("publishedAt")
        or raw.get("scraped_at") or raw.get("timestamp") or (raw.get("article") or {}).get("timestamp")
        or (raw.get("article") or {}).get("published_at")
    )

    # Normalize timestamp strings into an ISO-like form parseable by JS `Date`
    # Examples handled: "2025-11-29T11:39:35 +0000" -> "2025-11-29T11:39:35+00:00"
    def _normalize_ts(ts):
        if not ts:
            return None
        if not isinstance(ts, str):
            return ts
        s = ts.strip()
        # Remove any whitespace before a numeric timezone offset (e.g. space before +0000)
        s = re.sub(r"\s+([+-]\d{4})$", r"\1", s)
        # Ensure timezone offset has a colon: +HHMM -> +HH:MM
        s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
        return s

    timestamp = _normalize_ts(timestamp)

    article = {
        "title": title or "Article",
        "source": source,
        "timestamp": timestamp
    }

    # Include full bias analysis (if present) so frontend can render details
    return {"article": article, "claims": claims, "stats": stats, "bias": bias}
