# Wdrożenie OKRES

Jeden obraz Docker, bez zewnętrznych usług. Dane (SQLite) leżą na wolumenie `/app/data`.

## Lokalnie lub w małym urzędzie

```sh
cp .env.example .env   # uzupełnij DJANGO_SECRET_KEY i DJANGO_ALLOWED_HOSTS
docker compose up --build
```

Aplikacja działa pod `http://localhost:8000`. Kontener przy starcie wykonuje migracje. W trybie demo (`OKRES_DEMO=1`) przy pustej bazie wczytuje też dane syntetyczne (`seed_demo`).

Scheduler (przypomnienia, nowe okresy oceny) uruchamia się raz dziennie z crona hosta:

```sh
docker compose exec okres python manage.py scheduler
```

## Zmienne środowiskowe

| Zmienna | Znaczenie |
|---|---|
| `DJANGO_SECRET_KEY` | wymagany, losowy, tylko w środowisku |
| `DJANGO_DEBUG` | `0` w każdym wdrożeniu |
| `DJANGO_ALLOWED_HOSTS` | domeny aplikacji, po przecinku |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | pełne adresy `https://...` przy pracy za proxy z TLS |
| `DJANGO_BEHIND_PROXY` | `1` za reverse proxy z TLS (nagłówek `X-Forwarded-Proto`, ciasteczka `Secure`) |
| `OKRES_DATA_DIR` | katalog bazy SQLite (w obrazie `/app/data`) |
| `DATABASE_URL` | opcjonalnie inna baza; Postgres wymaga doinstalowania sterownika |
| `OKRES_DEMO` | `1` tylko na demo (zegar, dane syntetyczne, szybkie logowanie) |
| `OKRES_SEED_ON_START` | `1`: w trybie demo wczytaj dane syntetyczne przy pustej bazie |
| `OKRES_AI` | `wylaczone` (domyślnie) albo `ollama`: opcjonalny asystent porządkujący notatki |
| `OKRES_OLLAMA_URL` | adres Ollamy w sieci urzędu, np. `http://localhost:11434` |
| `OKRES_AI_MODEL` | `gemma4:12b` (domyślnie); alternatywa `hf.co/speakleash/Bielik-11B-v3.1-Instruct-GGUF:Q4_K_M` |
| `OKRES_AI_THINK` | `0` (domyślnie): tryb rozumowania modelu wyłączony, szybsza odpowiedź; `1`: włączony |
| `OKRES_AI_TIMEOUT` | limit czasu odpowiedzi modelu w sekundach (domyślnie 30) |

## Coolify (demo hackathonowe)

- Aplikacja z repo przez GitHub App, build pack `Dockerfile`, port `8000`.
- Trwały wolumen podpięty pod `/app/data`.
- Zmienne: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=<domena>`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://<domena>`, `DJANGO_BEHIND_PROXY=1`, `OKRES_DEMO=1`.
- Healthcheck: `GET /logowanie/` → 200 (ten sam jest w obrazie).
- Scheduled Task: `python manage.py scheduler`, raz dziennie.

## Licencje dodanych zależności

`gunicorn` (MIT), `whitenoise` (MIT), `dj-database-url` (BSD-3-Clause). Obrazy bazowe: `python:3.13.9-slim-bookworm` i `ghcr.io/astral-sh/uv:0.9.7`, z przypiętymi wersjami.
