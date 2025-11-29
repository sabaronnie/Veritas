**Dockerizing Veritas (backend + frontend)**

Quick start (Windows cmd.exe)

1. Ensure Docker and Docker Compose are installed and running.

2. Provide secrets:
   - Create `backend/secrets.env` (do NOT commit this file). Example keys required:
     OPENAI_API_Key=sk-...
     MONGO_URI=mongodb://mongo:27017/veritas

3. Build and start services:
```
docker compose build
docker compose up
```

Services:
- Backend API: http://localhost:8001 (served by Uvicorn)
- Frontend: http://localhost:8000 (served by nginx)
- MongoDB: internal service `mongo` (exposed in compose as volume)

Notes and recommendations
- The backend image uses `python:3.11-slim` to avoid heavy build issues with some ML wheels.
- If you rely on heavy ML packages (sentence-transformers, numpy/scipy), install them locally or build a specialized image with compiled wheels (this repo uses a relaxed requirements file under `website/requirements_py312.txt`).
- Secrets: keep `backend/secrets.env` outside version control and rotate keys if they've been committed previously.

Development tips
- To mount the source and enable live reload, the compose file mounts the repo into the container (useful for development). For production, remove the mount and build a clean image.
