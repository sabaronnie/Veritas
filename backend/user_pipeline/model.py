from openai import OpenAI
import os
import json

from dotenv import load_dotenv

# Resolve: backend/user_pipeline/ → go up one level → backend/secrets.env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "..", "secrets.env")
load_dotenv(ENV_PATH)
client = OpenAI(api_key=os.getenv("OPENAI_API_Key"))

def safe_json_loads(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Ask the model to repair the JSON
        repair_prompt = f"""
The following is intended to be valid JSON, but contains errors.
Fix it and return ONLY valid JSON. Do NOT add explanations.

RAW:
{raw}
"""
        repair = client.responses.create(
            model="gpt-4.1",
            input=repair_prompt,
            max_output_tokens=3000,
        )
        fixed = repair.output[0].content[0].text
        return json.loads(fixed)

def save_raw_response(text, filename="model_output.txt"):
    out_path = os.path.join(BASE_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[✓] Saved model output to {out_path}")

def analyze_article(A, B_list):
    """
    Single OpenAI call:
    - Extract claims from A
    - Compare A claims with B articles
    - Output JSON in the required format
    - Perform bias analysis
    """
    A_json = json.dumps(A, ensure_ascii=False, indent=2)
    B_json = json.dumps(B_list, ensure_ascii=False, indent=2)

    system_prompt = """
You are Veritas-LLM, a cross-source news verification engine.
You MUST output ONLY valid JSON following the EXACT schema below.

STRICT RULES:
- No explanations
- No text outside JSON
- ALL fields must be filled
- Claims must be extracted from Article A
- Claim comparisons must use claims extracted from B articles
- No hallucinations
- Use `null` when no match exists

OUTPUT JSON SCHEMA:

{
  "title": "...",
  "user_published_at": "...",
  "current_source": "...",
  "claims_in_A": [
    {
      "claim_id": "A#",
      "claim_text": "...",
      "comparisons": [
          {
            "source": "...",
            "article_id": "...",
            "published_at": "...",
            "article_title": "...",
            "match_type": "support | contradiction | no_match",
            "matched_claim_id": "B# or null",
            "matched_claim_text": "text or null",
            "nli_confidence": 0.0  # float in range 0.0-1.0 or null when not available
          }
        ]
    }
  ],
  "bias_analysis": {
    "framing_bias": "...",
    "omission_bias": "...",
    "emotional_language": "...",
    "source_bias": "...",
    "overall_bias_score": 0.0
  }
}
"""
    # NOTE: For each comparison, include an `nli_confidence` numeric value between 0.0 and 1.0
    # if your model can estimate confidence. If not available, use `null`.
    # response = client.responses.create(
    #     model="gpt-4.1",
    #     input=prompt,
    #     max_output_tokens=6000,
    #     #reasoning={"effort": "medium"},
    #     #response_format={"type": "json_object"}
    # )
    
    user_prompt = f"""
ARTICLE_A:
{A_json}

ARTICLES_B:
{B_json}

Extract claims and fill the required JSON structure.
"""
    # response = client.chat.completions.create(
    #     model="gpt-4.1",
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt}
    #     ],
    #     response_format={"type": "json_object"},   # <-- HARD guarantee of JSON
    #     max_tokens=6000
    # )

    # # parsed = resp.choices[0].message.parsed
    # # return parsed

    # raw_text = response.output[0].content[0].text
    # return safe_json_loads(raw_text)
    #return safe_json_loads(response)
    #return response.output_json
    
    # response = client.responses.create(
    #     model="gpt-4.1",
    #     input=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt}
    #     ],
    #     #response_format={"type": "json_object"},
    #     #max_tokens=6000,
    # )
    final_prompt = f"""
    {system_prompt}
    
    {user_prompt}
    """


    #print(final_prompt)
    # response = client.responses.create(
    #     model="gpt-4.1",
    #     input=final_prompt,

    # )
    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )

    # Let the SDK do the parsing:
    return safe_json_loads(response.output_text)
    # result = response
    # return result

    # # PERFECT JSON directly from the model
    # raw_text= response.output[0].content[0].text
    # # save_raw_response(response, "raw_output.json")
    # return safe_json_loads(response.output_text)