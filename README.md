# OKRES · Ocena Kompetencji, Rozwoju i Efektów Służby

Prototyp na HackNation 2026, zadanie „Cyfrowy Asystent Ocen Okresowych” (KPRM, Departament Służby Cywilnej).

OKRES prowadzi cały proces oceny okresowej członka korpusu służby cywilnej bez papieru: od wyznaczenia kryteriów, przez obserwacje z 24 miesięcy, rozmowę oceniającą i ocenę, po zapoznanie, sprzeciw i wydruk arkusza zgodnego ze wzorem z rozporządzenia. Moduł „wirtualny HR partner” pokazuje przełożonemu sygnały do rozmowy z widocznymi zdarzeniami źródłowymi. Pracownik widzi te same fakty.

Terminy, punktację i warunki liczy deterministyczny kod sterowany wersjonowanymi pakietami reguł (YAML). Zmiana przepisów to nowy pakiet, a nie przebudowa systemu. Proces działa w całości bez AI i bez dostępu do internetu.

## Uruchomienie

**Docker (jedna komenda):**

```sh
cp .env.example .env    # OKRES_DEMO=1 dla pokazu, 0 w urzędzie
docker compose up --build
```

Aplikacja: <http://localhost:8000>. Kontener sam wykonuje migracje. Bez `DJANGO_SECRET_KEY` w `.env` przy pierwszym starcie losuje klucz i zapisuje go na wolumenie danych (`/app/data/.secret_key`), więc restart i aktualizacja obrazu nie wylogowują użytkowników. Własny klucz można podać jednolinijkowcem: `echo "DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" >> .env`. Usługa `scheduler` raz na dobę wysyła przypomnienia i zakłada kolejne okresy oceny. Szczegóły wdrożenia, w tym Coolify, są w [DEPLOY.md](DEPLOY.md).

**Bez Dockera (Python 3.13, [uv](https://docs.astral.sh/uv/)):**

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo      # dane syntetyczne, tylko w trybie demo (DEBUG lub OKRES_DEMO=1)
uv run python manage.py runserver
uv run python manage.py test
```

### Pierwsze uruchomienie w urzędzie (`OKRES_DEMO=0`)

W profilu urzędu nie ma danych demo, zegara ani szybkiego logowania. Kolejne kroki:

1. Konto administratora kadr:

   ```sh
   docker compose exec okres python manage.py createsuperuser
   ```

2. Panel kadr (`/admin/`) → **Urząd**: nazwa, miejscowość i aktywny pakiet przepisów (domyślnie `2016-04-04`).
3. Import pracowników z CSV (separator `;`, kodowanie UTF-8). Ponowny import aktualizuje dane:

   ```sh
   docker compose cp pracownicy.csv okres:/app/data/pracownicy.csv
   docker compose exec okres python manage.py import_pracownikow /app/data/pracownicy.csv
   ```

   ```text
   login;imie;nazwisko;email;komorka;stanowisko;rodzaj_stanowiska;przelozony;urzednik;rok_mianowania;stopien;data_stopnia
   jkowalska;Joanna;Kowalska;jk@urzad.local;Wydział Spraw Obywatelskich;naczelnik wydziału;kierujacy;;tak;2012;4;2021-06-01
   anowak;Adam;Nowak;an@urzad.local;Wydział Spraw Obywatelskich;specjalista;pozostale;jkowalska;nie;;;
   ```

   `rodzaj_stanowiska` to `kierownik_urzedu`, `kierujacy` albo `pozostale` i wyznacza arkusz A, B albo C (§ 3). Hasła nie są importowane. Nadaje je kadry w panelu albo `python manage.py changepassword <login>`. SSO to plan pilotażu.
4. Panel kadr → **Pracownicy**: zaznacz dyrektora generalnego (rozpatruje sprzeciwy, widzi statystyki). Konta kadr mają `is_staff`.
5. Panel kadr → **Oceny** → Dodaj: pierwsza sprawa każdego pracownika (oceniany, oceniający, początek okresu i jego podstawa). Kolejne sprawy zakłada scheduler po sporządzeniu oceny.
6. Poczta (opcjonalnie): `OKRES_SMTP_HOST` i `OKRES_POWIADOMIENIA_EMAIL=1`. Bez SMTP powiadomienia działają w aplikacji, a wiadomości e-mail trafiają tylko do logu z ostrzeżeniem.

### Tryb demo (`OKRES_DEMO=1`)

Kontener wczytuje dane syntetyczne w pustej bazie i uzupełnia rozpoznany starszy zestaw demo. Zachowuje istniejące konta, sprawy i ustawienie zegara. Pasek „Tryb demonstracyjny” pokazuje też datę systemową, gdy kadry ją przesuną. Strona logowania ma przyciski najważniejszych ról. Seed daje 14 osób (w tym oceniającą kierownika urzędu spoza urzędu, bez konta) i 14 spraw spójnych na 21.11.2026: żadna nie jest po terminie, w tym ocenę do zapoznania (Natalia Wróbel), sprzeciw do rozpatrzenia (Joanna Kurek) i zakończone oceny z kolejnym okresem (Piotr Wysocki, Rafał Duda). Kolejny okres zakłada się po ocenie ostatecznej, a po negatywnej od razu. Zestaw demo z poprzedniej wersji nie jest uzupełniany; nowe dane po resecie wolumenu. Jeśli uruchamiasz aplikację poza kontenerem lub masz wyłączone `OKRES_SEED_ON_START`, możesz ręcznie uzupełnić rozpoznany starszy zestaw poleceniem `python manage.py seed_demo --na-starcie`. Reset danych: `docker compose down -v && docker compose up`.

**Konta demo** (hasło `demo`; w trybie demo można też kliknąć rolę na stronie logowania):

| Login | Rola |
|---|---|
| `oceniajaca` | naczelniczka wydziału, oceniająca (arkusz B dla siebie, przełożona Jana i Piotra) |
| `oceniany` | starszy specjalista, urzędnik mianowany, arkusz C, nieobecność z przykładu KPRM |
| `piotr` | specjalista, pracownik służby cywilnej, sygnały HR partnera |
| `kadry` | komórka kadrowa, panel kadr, zegar demo, scheduler, fikcja zapoznania |
| `dyrektor` | dyrektor generalny: sprzeciwy, statystyki, obowiązek stopnia służbowego |

## Co działa

| Obszar | Stan | Gdzie sprawdzić |
|---|---|---|
| Arkusze A/B/C: kryteria obowiązkowe, wykaz 14 kryteriów z Załącznika nr 1, 0–3 dodatkowe bez powtórzeń i bez powielania obowiązkowych | działa | część I sprawy; `oceny/tests.py` |
| Arkusz wyznaczany ze stanowiska (§ 3) | działa | panel kadr → Pracownicy |
| Część I: rozmowa (§ 5), oczekiwania i cele (§ 5 ust. 1 pkt 3–4) wracające w rozmowie oceniającej (§ 10 pkt 2), potwierdzenie oceniającego i ocenianego (§ 6), blokada pól, korekta administratora z powodem i śladem | działa | sprawa Jana; `Korekta` w panelu; `oceny/test_obieg.py` |
| Terminy z rachunkiem „Jak obliczono termin?”: miesiące, koniec miesiąca, dni wolne i święta, ciągłość nieobecności, 24 miesiące (art. 81 ust. 4), przedłużenie o nieobecność (art. 81 ust. 7) z powiadomieniem stron o nowym terminie | działa, przykłady KPRM jako testy | nagłówek sprawy; `oceny/test_terminy.py`, `oceny/test_obieg.py` |
| Obserwacje z okresu oceny: prywatne notatki przełożonego, osiągnięcia zgłaszane przez pracownika, grupowanie według kryteriów | działa | sekcja „Obserwacje” |
| Przygotowanie do rozmowy rozpoczynającej i oceniającej: agenda z przepisów, wskaźniki kryteriów, karty trudnych sytuacji | działa | link w sprawie |
| Część II: oceny cząstkowe, średnia, poziom i wynik na żywo (§ 11), strażnik formalny z podstawą prawną, okres podlegania ocenie, poprzednia ocena urzędnika | działa | formularz części II |
| Część rozwojowa: katalog 2–3 działań rozwojowych dla każdego z 14 kryteriów (`rules/rozwoj.yaml`, walidowany), przy ocenie 1/3 propozycje do wniosków IPRZ wstawiane tylko kliknięciem oceniającego, przy 7/9 wskazówki „mocna strona” | działa | część II; `oceny/test_rozwoj.py` |
| Część III: wniosek o kolejny stopień (art. 89 ust. 1), blokada przy 9. stopniu, powiadomienie DG i kadr o złożonym wniosku | działa | Jan jako urzędnik; `oceny/test_obieg.py` |
| Zapoznanie (§ 12), fikcja zapoznania (kadry, z datą doręczenia), pouczenie | działa | sekcja zapoznania |
| Sprzeciw (7 dni), rozpatrzenie przez DG (14 dni): nieuwzględnienie, zmiana oceny, sporządzenie po raz drugi, drugi sprzeciw, pouczenie o sądzie pracy, historia wersji | działa | konto `dyrektor` |
| Po ocenie negatywnej: kryteria w 7 dni od sporządzenia, ponowna ocena po 6 miesiącach od zapoznania | działa | `oceny/test_scheduler.py` |
| Sytuacje kadrowe: zmiana oceniającego (§ 9 ust. 3), zmiana stanowiska z rozgałęzieniem (art. 81 ust. 6, § 9 ust. 1–2), zmiana terminu (art. 81 ust. 8) z zawiadomieniem § 8 | działa | sekcja „Sytuacje kadrowe” |
| Obligatoryjny kolejny stopień (art. 89 ust. 2): wykrycie i przypomnienie dla DG | działa | `oceny/test_przygotowanie.py` |
| Wydruk A/B/C według wzorów z załączników 2–4, kopia części I, druk i PDF z przeglądarki | działa, sprawdzony wizualnie dla C | przycisk „Arkusz do druku” |
| Scheduler: przypomnienia o kryteriach, ocenie, zapoznaniu, sprzeciwie i rozpatrzeniu, kolejne sprawy, idempotentny | działa | `manage.py scheduler` |
| Poczta i kalendarz: zaproszenie `.ics` bez danych kadrowych w tytule, powiadomienia e-mail przez SMTP urzędu | działa (e-mail domyślnie w konsoli) | sprawa → zaproszenie |
| EZD: paczka sprawy ZIP (arkusz, `dane.json`, historia) do ręcznego przekazania | działa; brak API EZD | link „Paczka do akt / EZD” |
| Wirtualny HR partner: dziennik zadań, sygnały z progami i źródłami (zmiany priorytetu, przyrost zadań, powrót po nieobecności, osiągnięcie bez docenienia, możliwy spadek zaangażowania), pytanie do rozmowy, katalog działań (w tym szkolenie), uzgodnienie z datą sprawdzenia i wynikiem, perspektywa pracownika, docenienia | działa | konto `oceniajaca` → Zespół; `partner/tests.py` |
| Statystyki zbiorcze dla DG i kadr z eksportem CSV (bez notatek i danych HR) | działa | Statystyki |
| Wersje przepisów: dziedziczenie pakietów, walidacja przykładami przed aktywacją, porównanie terminów | działa | sprawa → „porównaj wersje”; `manage.py sprawdz_reguly` |
| Import pracowników z CSV | działa | `manage.py import_pracownikow plik.csv` |
| Asystent porządkujący obserwacje: bez AI albo z modelem lokalnym (Ollama, Gemma 4 12B), z cytowaniem notatek, odporny na niepoprawne odpowiedzi modelu | działa; model lokalny opcjonalny | część II → „Uporządkuj moje obserwacje”; `oceny/test_asystent.py` |
| Wdrożenie: jeden obraz, `docker compose up` bez konfiguracji (klucz generowany na wolumenie), `check --deploy` bez błędów, profil urzędu bez danych demo | działa | „Pierwsze uruchomienie w urzędzie”; [DEPLOY.md](DEPLOY.md) |

## Jak zaktualizować przepisy

1. Skopiuj albo utwórz pakiet w `rules/`, np. `rules/2027-01-01.yaml`. Najprościej dziedziczyć i nadpisać tylko zmienione klucze:

   ```yaml
   dziedziczy: "2016-04-04"
   wersja: "2027-01-01"
   nazwa: "Nowelizacja ... (Dz.U. ...)"
   obowiazuje_od: 2027-01-01
   terminy:
     okres_oceny_miesiace: 12
   przyklady:
     - {poczatek: "2027-01-04", termin_oceny: "2028-01-04"}
   ```

2. Sprawdź pakiet: `python manage.py sprawdz_reguly 2027-01-01`. Komenda weryfikuje wymagane klucze, spójność kryteriów i progów oraz każdy przykład wejście → wynik.
3. W panelu kadr (Urząd → aktywny pakiet reguł) wybierz nową wersję. Pakiet z błędem nie zostanie aktywowany. Nowe sprawy dostają nową wersję, sprawy w toku zachowują swoją. O objęciu spraw w toku decyduje przepis przejściowy.

W pakiecie można zmienić bez kodu: kryteria i ich opisy, przypisanie do arkuszy, limit kryteriów dodatkowych, skalę i progi punktacji, długości wszystkich terminów, progi przypomnień. Reguły HR partnera są w `rules/hr_partner.yaml`, treści przygotowania do rozmów w `rules/rozmowy.yaml`. Nowy rodzaj operacji na terminach wymaga zmiany kodu w `oceny/terminy.py` i testu.

## Architektura

- Python 3.13, Django 6.1, HTMX (plik lokalny, działa offline), szablony serwerowe, panel admina Django jako panel kadr.
- SQLite na wolumenie (mały urząd, zero konfiguracji). Inna baza przez `DATABASE_URL`. Postgres wymaga sterownika, a `psycopg` ma licencję LGPL, więc nie dołączamy go domyślnie.
- `oceny/terminy.py`: liczenie terminów z rachunkiem. `oceny/punktacja.py`: § 11. `oceny/models.py`: proces i blokady. `oceny/scheduler.py`: zadania okresowe. `partner/`: HR partner.
- Uprawnienia sprawdza serwer przy każdym widoku i pobraniu pliku. Oceniany i oceniający widzą swoje sprawy, kadry wszystkie, DG sprawy ze sprzeciwem. Notatek i danych HR nie widzą ani kadry, ani DG.
- HR partner nie przetwarza przyczyn nieobecności, tylko fakt i okres. Nie podejmuje decyzji, a jego sygnały nie trafiają do oceny ani do kadr.

## Dane HR partnera: zakres, podstawa i retencja

- **Zakres.** Dziennik zadań (nowe zadanie, zmiana priorytetu lub terminu, przekazanie, zakończenie), uzgodnione działania z datą sprawdzenia i wynikiem, perspektywa pracownika, docenienia, osiągnięcia zgłoszone przez pracownika oraz fakt i okres nieobecności usprawiedliwionej. Bez przyczyn nieobecności, danych o zdrowiu (art. 9 RODO), ocen nastroju i profilowania.
- **Kto widzi.** Bezpośredni przełożony i pracownik, którego dane dotyczą. Pracownik widzi te same zdarzenia źródłowe i sygnały co przełożony („Mój dobrostan i rozwój”). Kadry i DG nie mają dostępu, a sygnały nie trafiają do oceny okresowej ani statystyk.
- **Podstawa (propozycja do potwierdzenia z IOD urzędu).** Art. 6 ust. 1 lit. c RODO w związku z obowiązkami pracodawcy dotyczącymi organizacji pracy i rozwoju zawodowego (art. 94 Kodeksu pracy) oraz z indywidualnym programem rozwoju zawodowego (art. 108 ustawy o służbie cywilnej). Sygnały są wskazówką do rozmowy, a nie zautomatyzowaną decyzją (art. 22 RODO).
- **Retencja (propozycja).** Dziennik zadań i uzgodnienia przechowujemy przez bieżący i jeden poprzedni okres oceny, a potem usuwamy. Do akt osobowych nie trafiają. Prototyp nie usuwa danych automatycznie. Zadanie retencji w schedulerze i okres przechowywania ustalony z IOD należą do planu pilotażu.

## Co jest zamockowane lub uproszczone

- **Dane:** wszystkie osoby, urząd i treści są syntetyczne. Materiały partnera służyły tylko do sprawdzenia zgodności pól i nie są w repozytorium.
- **Zegar demo:** w trybie demo kadry mogą przesunąć datę systemową, a interfejs pokazuje to wyraźnym paskiem. W profilu urzędu (`OKRES_DEMO=0`) zegar, dane demo i szybkie logowanie są wyłączone.
- **Podpisy:** potwierdzenie zalogowanej osoby zapisuje datę i autora czynności. Na wydruku widnieje „potwierdzono w systemie”. To nie jest podpis w rozumieniu przepisów. Urząd wybiera jedną z dwóch ścieżek: wydruk arkusza do podpisów odręcznych albo przekazanie pliku do EZD i podpis kwalifikowany lub zaufany w EZD.
- **Logowanie:** konta Django. SSO i integracja z katalogiem urzędu to plan pilotażu.
- **EZD:** brak API EZD. Paczka ZIP (arkusz, `dane.json`, historia) do ręcznego przekazania.
- **Poczta:** bez SMTP wiadomości e-mail trafiają tylko do logu kontenera z ostrzeżeniem (`okres.W001`), a powiadomienia działają w aplikacji. Po podaniu `OKRES_SMTP_HOST` i `OKRES_POWIADOMIENIA_EMAIL=1` idą przez SMTP urzędu.
- **Plan pilotażu (nie ma w prototypie):** zastępstwa oceniającego (dziś tylko zmiana oceniającego przez kadry), import ocen historycznych z poprzednich lat (poprzednią ocenę urzędnika wpisuje się ręcznie), wniosek ocenianego o zmianę terminu składany w systemie (dziś oceniający wpisuje zmianę z podstawą art. 81 ust. 8 pkt 4), automatyczne usuwanie danych HR po okresie retencji, SSO.
- **PDF:** druk i zapis PDF z przeglądarki z szablonu A4. Przypisy na wydruku mają własną numerację, krótszą niż we wzorze.
- **Pakiet `symulacja-12m`:** ilustracja techniczna zmiany parametru, bez przypisywania przyszłej ustawie treści ani daty.

## Kwestie otwarte do potwierdzenia z mentorami KPRM

- Przedłużenie terminu o nieobecność liczymy w dniach kalendarzowych scalonej nieobecności („o czas tej nieobecności”). Nieobecność sprzed okresu oceny liczymy od początku okresu.
- Czy przedłużenie z art. 81 ust. 7 dotyczy też terminu ponownej oceny z art. 81 ust. 9. Obecnie nie dotyczy.
- Przy pierwszej ocenie próg „więcej niż 6 miesięcy” (art. 81 ust. 6 i 8, § 9 ust. 1) liczymy od ustalenia kryteriów.
- Dowód doręczenia przy fikcji zapoznania. Obecnie kadry wpisują datę i okoliczności.

## Licencje

Kod zespołu jest przeznaczony do przekazania KPRM zgodnie z regulaminem konkursu (plik [LICENSE](LICENSE): wszelkie prawa zastrzeżone, to nie jest licencja open source). Zależności mają wyłącznie licencje permisywne:

| Składnik | Licencja |
|---|---|
| Django | BSD-3-Clause |
| PyYAML | MIT |
| holidays (kalendarz świąt) | MIT |
| htmx 2.0.4 (plik lokalny) | 0BSD (Zero-Clause BSD) |
| gunicorn | MIT |
| whitenoise | MIT |
| dj-database-url | BSD-3-Clause |
| obrazy `python:3.13.9-slim-bookworm`, `ghcr.io/astral-sh/uv` | PSF / Debian, MIT/Apache-2.0 |

Bez płatnych licencji i bez usług zewnętrznych wymaganych do działania.

## Gdzie użyto AI

- **W wytwarzaniu:** kod, testy i dokumentację pisaliśmy z asystentami AI do programowania (Claude Code, Codex) pod nadzorem zespołu. Każdą zmianę sprawdzały testy automatyczne, a kluczowe reguły porównaliśmy ręcznie z tekstem ustawy, rozporządzenia, schematami pól i dokumentem KPRM o liczeniu terminów. Kod przejrzał też osobny agent AI. Wynik przeglądu i wprowadzone poprawki są w `PROGRESS.md`.
- **W produkcie:** AI jest opcjonalne i domyślnie wyłączone (`OKRES_AI=wylaczone`). Model: **Gemma 4 12B** (`gemma4:12b`) uruchamiana lokalnie w Ollamie, w sieci urzędu, bez wysyłki danych na zewnątrz; alternatywa `hf.co/speakleash/Bielik-11B-v3.1-Instruct-GGUF:Q4_K_M`. Propozycje działań rozwojowych i sygnały HR partnera pochodzą z edytowalnych katalogów YAML, nie z modelu. Po włączeniu (`OKRES_AI=ollama`) model lokalny, domyślnie Gemma 4 12B (`OKRES_AI_MODEL=gemma4:12b`) przez Ollamę z wyłączonym trybem rozumowania (`OKRES_AI_THINK=0`), porządkuje wyłącznie notatki przełożonego według kryteriów:
  - każde zdanie odsyła do notatki źródłowej, a zdania bez źródła są odrzucane;
  - imiona i nazwiska stron są pseudonimizowane przed wysłaniem;
  - awaria modelu jest jawnie oznaczona;
  - model nie pisze oceny, nie proponuje punktów i nic nie wpisuje do formularza.

  Terminy, punktacja i warunki nigdy nie są liczone przez model.
- **Wcześniejszy kod:** nie wykorzystaliśmy kodu z wcześniejszych projektów ani z innego zadania zespołu.
