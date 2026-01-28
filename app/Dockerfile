FROM python:3.12-slim

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    "uvicorn[standard]==0.30.6" \
    jinja2==3.1.4 \
    psycopg2-binary==2.9.9 \
    python-multipart==0.0.9

# Build context is app/, so this copies main.py, db.py, static/, templates/ into /srv
COPY . /srv

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
