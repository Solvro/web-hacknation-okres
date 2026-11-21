#!/bin/sh
# Start kontenera: migracje, (w trybie demo) dane syntetyczne przy pustej bazie, potem serwer.
set -e

python manage.py migrate --noinput

if [ "${OKRES_DEMO:-0}" = "1" ] && [ "${OKRES_SEED_ON_START:-1}" = "1" ]; then
    if [ "$(python manage.py shell -v 0 -c 'from django.contrib.auth.models import User; print(User.objects.exists())')" = "False" ]; then
        echo "Pusta baza w trybie demo: wczytuję dane syntetyczne (seed_demo)."
        python manage.py seed_demo
    fi
fi

exec "$@"
