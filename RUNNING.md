- **Prerequisites**:
- **Python**: 3.10, 3.11 or 3.12 installed and on `PATH`.
- **git** (optional): to clone or update the repo.
- **Internet**: will be required to install packages and download ML models.

**Create Virtual Environment & Install**:
- Open a Windows `cmd.exe` shell in the project root (where this `RUNNING.md` lives).

```
:: Create venv
python -m venv .venv

:: Activate venv
.venv\Scripts\activate

:: Install Python dependencies (includes backend requirements)
pip install -r requirements.txt
```

Notes:
- `sentence-transformers` can download model weights (~100s MB). Expect a longer install/download step the first time.
- If you need GPU-backed models, install a suitable `torch` wheel separately following official instructions.

**Environment variables / secrets**:
- The repository previously contained a committed `backend\secrets.env` with sensitive values; that file was removed from the repo. Use the safe example at `backend\secrets.env.example` and create your own local `backend\secrets.env` (DO NOT commit it).
  - Copy the example and fill in your real keys:

```
copy backend\secrets.env.example backend\secrets.env
:: then edit backend\secrets.env and add your real values
```

  - Required vars (example):

```
MONGO_URI=your_mongo_connection_string
DB_NAME=veritasdatabase
OPENAI_API_Key=sk-...your-key...
```

  - The code uses `python-dotenv` and will load `backend\secrets.env` from the backend folder. Keep `backend\secrets.env` local and untracked.

**Run the pipeline (one-off)**:
- This will run the user pipeline against a sample URL and save `analysis.json` into `website\analysis.json`.

```
:: From project root with venv activated
python backend\main.py
```

**Run as an API (serve FastAPI)**:
- To run the FastAPI server which the frontend can call:

```
:: Install uvicorn if not already installed
pip install "uvicorn[standard]"

:: Run the API (listens on 127.0.0.1:8000)
uvicorn backend.veritas_api:app --reload --host 127.0.0.1 --port 8000
```

API endpoints:
- `GET /health` — basic health check
- `POST /api/fact-check` — provide JSON {"url": "<article-url>"} to trigger the pipeline

**Frontend / Browser extension**:
- The project contains two simple frontends:
  - Static website files in `website/` (open `website\popup.html` or `website\veritasweb-2.html` in your browser)
  - Chrome extension in `extension/` which can be loaded as an unpacked extension (Developer mode → Load unpacked → select `extension/` folder).

If the frontend calls the API, make sure the API is running and CORS is allowed (the FastAPI app already sets permissive CORS).

**Troubleshooting**:
- If imports fail: ensure venv is activated and `pip install` completed without errors.
- If OpenAI calls fail: confirm `OPENAI_API_Key` is set and valid; note this repo uses the newer OpenAI Responses API (check `backend/user_pipeline/model.py`).
- If MongoDB errors: confirm `MONGO_URI` is reachable and the database name matches `DB_NAME`.

**Next steps / optional**:
- Consider removing the included `backend\secrets.env` from version control and adding `backend/secrets.env` to `.gitignore`.
- If you want, I can create a `.env.example` and update `.gitignore`, or run `pip install` in the environment and test-run the pipeline for you.
