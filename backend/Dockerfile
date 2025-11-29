FROM python:3.11-slim

WORKDIR /app

# Copy root requirements + pre-downloaded Linux wheels
COPY requirements.txt /app/requirements.txt
COPY backend/wheels /wheels

# Install deps from local wheels only (no PyPI)
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-index --find-links=/wheels -r /app/requirements.txt

# Copy backend code
COPY backend/ /app/backend

ENV PYTHONUNBUFFERED=1
EXPOSE 8001

CMD ["uvicorn", "backend.veritas_api:app", "--host", "0.0.0.0", "--port", "8001"]
