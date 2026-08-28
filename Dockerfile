FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /app

RUN addgroup --system app && adduser --system --home /app --ingroup app app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN mkdir -p /app/data /app/staticfiles \
    && chmod 755 /app/entrypoint.sh \
    && chown -R app:app /app/data /app/staticfiles /app/backend

RUN DJANGO_SECRET_KEY=build-only DATA_ROOT=/app/data gosu app \
    python /app/backend/manage.py collectstatic --noinput

ENTRYPOINT ["/app/entrypoint.sh"]
WORKDIR /app/backend

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
