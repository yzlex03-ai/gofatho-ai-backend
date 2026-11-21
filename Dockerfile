FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install lightweight FastAPI + Uvicorn + Pydantic stack
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and bundled SQLite FTS5 Master Database
COPY backend/ /app/backend/
COPY data/gofatho_ai_master.sqlite /app/data/gofatho_ai_master.sqlite

# Rebuild SQLite FTS5 full-text indexes on container build for <1ms RAG queries
RUN python3 -c "import sqlite3; conn=sqlite3.connect('/app/data/gofatho_ai_master.sqlite'); conn.executescript(\"CREATE VIRTUAL TABLE IF NOT EXISTS dictionary_fts USING fts5(headword, normalized_form, english, amharic, domain, content='dictionary', content_rowid='id'); INSERT INTO dictionary_fts(dictionary_fts) VALUES('rebuild');\"); conn.commit(); conn.close()"

ENV GOFATHO_DB_PATH=/app/data/gofatho_ai_master.sqlite
ENV PORT=7860
EXPOSE 7860

WORKDIR /app/backend
CMD ["uvicorn", "fastapi_rag_server:app", "--host", "0.0.0.0", "--port", "7860"]
