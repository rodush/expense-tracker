FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY app ./app
COPY main.py ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/ready', timeout=3)"

CMD ["sh", "-c", "uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
