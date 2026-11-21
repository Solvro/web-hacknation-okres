# OKRES: jeden obraz, bez zewnętrznych usług. SQLite na wolumenie /app/data.
FROM ghcr.io/astral-sh/uv:0.9.7 AS uv

FROM python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    OKRES_DATA_DIR=/app/data

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && useradd --system --uid 1000 --home-dir /app okres \
    && mkdir -p /app/data && chown -R okres /app/data

USER okres
VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/logowanie/', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "okres_site.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--no-control-socket"]
