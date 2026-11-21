#!/bin/sh
# Start kontenera: klucz sesji, migracje, (w trybie demo) dane syntetyczne, potem serwer.
set -e

# Bez DJANGO_SECRET_KEY w środowisku: klucz losowany raz i trzymany na wolumenie danych (przetrwa restart i aktualizację obrazu).
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    PLIK_KLUCZA="${OKRES_DATA_DIR:-/app/data}/.secret_key"
    if [ ! -s "$PLIK_KLUCZA" ]; then
        umask 077
        python -c 'import secrets; print(secrets.token_urlsafe(50))' > "$PLIK_KLUCZA"
        echo "Brak DJANGO_SECRET_KEY: wygenerowano klucz i zapisano w $PLIK_KLUCZA (wolumen danych)."
    fi
    DJANGO_SECRET_KEY="$(cat "$PLIK_KLUCZA")"
    export DJANGO_SECRET_KEY
fi

python manage.py migrate --noinput

if [ "${OKRES_DEMO:-0}" = "1" ] && [ "${OKRES_SEED_ON_START:-1}" = "1" ]; then
    python manage.py seed_demo --na-starcie
fi

exec "$@"
