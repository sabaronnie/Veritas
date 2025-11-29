from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json

# Import your pipeline
from backend.main import start_user_pipeline


# -----------------------------
# FASTAPI SETUP
# -----------------------------
app = FastAPI(title="Veritas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# REQUEST MODEL
# -----------------------------
class FactCheckRequest(BaseModel):
    url: str
    sources: Optional[List[str]] = None
    articles_limit: Optional[int] = 50


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


from backend.formatters import map_analysis_to_response


# -----------------------------
# MAIN ENDPOINT FOR FRONTEND
# -----------------------------
@app.post("/api/fact-check")
async def fact_check(req: FactCheckRequest):
    """
    1. Frontend sends a URL.
    2. We run the full pipeline (scrape + DB + GPT).
    3. Save analysis.json to ../website automatically.
    4. Return structured response to frontend.
    """

    try:
        # Run full backend pipeline (scrape → db → gpt → save json)
        raw_results = start_user_pipeline(req.url)

        # Convert raw GPT JSON → frontend format
        response = map_analysis_to_response(raw_results)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")