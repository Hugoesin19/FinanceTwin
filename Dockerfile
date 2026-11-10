FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY engine /app/engine
COPY api /app/api

RUN pip install --no-cache-dir -e /app/engine -e /app/api

ENV FINANCETWIN_DB=/data/financetwin.sqlite
ENV PORT=8000

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["sh", "-c", "uvicorn financetwin_api.main:app --host 0.0.0.0 --port ${PORT}"]
