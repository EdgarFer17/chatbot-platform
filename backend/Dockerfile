FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app \
    HF_HOME=/home/app/.cache/huggingface \
    FASTEMBED_CACHE_PATH=/home/app/.cache/fastembed \
    FASTEMBED_CACHE_DIR=/home/app/.cache/fastembed

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app --home /home/app app && \
    mkdir -p /home/app/.cache && chown -R app:app /home/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/home/app/.cache/fastembed')" && \
    chown -R app:app /home/app

COPY app ./app
COPY scripts ./scripts
COPY alembic.ini .
COPY migrations ./migrations

USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
