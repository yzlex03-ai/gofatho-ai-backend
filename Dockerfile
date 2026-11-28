FROM python:3.11-slim

WORKDIR /app

# Create unprivileged runtime user for container security
RUN groupadd -r gofatho && useradd -r -g gofatho -d /app gofatho

# Copy requirements and install lightweight FastAPI + Uvicorn + Pydantic stack
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code and bundled SQLite FTS5 Master Database
COPY backend/ /app/backend/
COPY data/gofatho_ai_master.sqlite /app/data/gofatho_ai_master.sqlite

# Rebuild all 4 SQLite FTS5 full-text indexes on container build for <6ms cold / <0.01ms warm RAG queries and set ownership
RUN python3 -c "import sqlite3; conn=sqlite3.connect('/app/data/gofatho_ai_master.sqlite'); conn.executescript(\"CREATE VIRTUAL TABLE IF NOT EXISTS dictionary_fts USING fts5(headword, normalized_form, english, amharic, domain, content='dictionary', content_rowid='id'); INSERT INTO dictionary_fts(dictionary_fts) VALUES('rebuild'); CREATE VIRTUAL TABLE IF NOT EXISTS phrasebook_fts USING fts5(phrase_code, gofatho_latin, english, amharic, domain, content='everyday_phrasebook', content_rowid='id'); INSERT INTO phrasebook_fts(phrasebook_fts) VALUES('rebuild'); CREATE VIRTUAL TABLE IF NOT EXISTS curriculum_fts USING fts5(exercise_code, title_gofatho, question_gofatho, answer_gofatho, english_explanation, content='curriculum_meeze_exercises', content_rowid='id'); INSERT INTO curriculum_fts(curriculum_fts) VALUES('rebuild'); CREATE VIRTUAL TABLE IF NOT EXISTS igt_fts USING fts5(igt_code, gofatho_surface, leipzig_gloss, english_translation, grammatical_category, content='sellassie_igt_corpus', content_rowid='id'); INSERT INTO igt_fts(igt_fts) VALUES('rebuild');\"); conn.commit(); conn.close()" \
    && chown -R gofatho:gofatho /app

ENV GOFATHO_DB_PATH=/app/data/gofatho_ai_master.sqlite
ENV PORT=7860
EXPOSE 7860

USER gofatho
WORKDIR /app/backend
CMD ["uvicorn", "fastapi_rag_server:app", "--host", "0.0.0.0", "--port", "7860"]
