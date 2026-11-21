# Scenariusz pokazu (3 minuty)

Przygotowanie: `docker compose up` z `OKRES_DEMO=1` na czystym wolumenie (seed wczyta się sam) albo `uv run python manage.py seed_demo`. Przeglądarka 1280×720. Do przestawiania zegara w panelu kadr użyj konta `kadry`. Jeśli pokazujesz dwie role jednocześnie, otwórz je w osobnych profilach przeglądarki lub zwykłym i prywatnym oknie. Karty z tego samego profilu współdzielą sesję. Pasek „Tryb demonstracyjny” pokazuje ustawioną datę. Dane użyte w pokazie są syntetyczne.

| Czas | Rola | Co robimy | Co widzi jury |
|---|---|---|---|
| przed | kadry | Zegar demo: **01.04.2025** | pasek z przesuniętą datą |
| 0:00–0:30 | `oceniajaca` | Moje sprawy → Jan Borkowski. „Przygotuj się do rozmowy” (agenda z § 5). Wybór 2 kryteriów dodatkowych (lista bez obowiązkowych), data rozmowy, oczekiwania i cele (§ 5 ust. 1 pkt 3–4), potwierdzenie | blokada kryteriów, informacja o korekcie administratora |
| | `oceniany` | potwierdzenie części I, „Część I do druku / PDF” | wydruk części I według wzoru C; oczekiwania i cele z rozmowy widoczne dla obu stron |
| 0:30–0:55 | dowolna | „Terminy, dane i dokumenty” → „Jak obliczono termin?” przy terminie oceny | 16.03.2025 + 24 mies. = 16.03.2027, + 33 dni nieobecności (przykład KPRM, bez przyczyn), 18.04.2027 to niedziela → **19.04.2027** |
| przed 0:55 | kadry | Zegar demo: **21.11.2026** (dane HR partnera z seeda są datowane względem tego dnia) | |
| 0:55–1:25 | `oceniajaca` | Zespół · HR partner: Piotr „3 zmiany priorytetu w 6 tygodni” → zdarzenia źródłowe → „Ustal działanie” → uzgodnienie „odciążenie” z datą sprawdzenia; u Piotra też „możliwy spadek zaangażowania” (wcześniejsze uzgodnienie nie pomogło, z zastrzeżeniem, że to nie diagnoza); u Jana „Osiągnięcie czeka na docenienie” → „Dodaj docenienie” → „Doceń” | sygnał ze źródłami, pytanie do rozmowy |
| | `piotr` | Mój dobrostan i rozwój | te same fakty i uzgodnienie, pole na własną perspektywę |
| przed 1:25 | kadry | Zegar demo: **12.04.2027** | |
| 1:25–2:20 | `oceniajaca` | sprawa Jana → przygotowanie do rozmowy oceniającej (cele z części I, obserwacje według kryteriów). Część II: oceny cząstkowe, jedna **1** przy średniej > 6 | „powyżej oczekiwań · ocena negatywna” i wymóg uzasadnienia (§ 11 ust. 3); przy 1 propozycje do IPRZ z katalogu w sekcji podpowiedzi, „Wstaw” dopisuje punkt wyjścia do pola wniosków; przy 7/9 mocne strony |
| | | „Podpowiedzi do uzasadnienia i wniosków” → „Uporządkuj obserwacje”: zestawienie z odnośnikami do notatek; wpisanie uzasadnienia i wniosków do IPRZ; Jan jest urzędnikiem → poprzednia ocena, wniosek o stopień NIE | strażnik formalny blokuje braki z podstawą prawną |
| | | Arkusz do druku | arkusz C z X w polach, „powyżej 6 do 8 punktów”, NEGATYWNA |
| 2:20–2:40 | `oceniany` | potwierdzenie zapoznania | termin sprzeciwu 7 dni z przesunięciem na dzień roboczy; po negatywnej: kryteria w 7 dni od sporządzenia, ponowna ocena po 6 mies. od zapoznania |
| | kadry | „Sprawdź przypomnienia (demo)” | nowa sprawa po ocenie negatywnej, przypomnienia |
| 2:40–3:00 | dowolna | sprawa → „Terminy, dane i dokumenty” → „Porównaj wersje” | ten sam początek: 19.04.2027 (stan prawny, z przedłużeniem o nieobecność) obok 16.03.2026 (symulacja cyklu 12 mies.; nieobecność wypada po terminie); obie wersje przeszły `sprawdz_reguly` |

Na pytania mamy przygotowane:
- konto `dyrektor`: sprzeciw → zmiana oceny albo sporządzenie po raz drugi, historia wersji, statystyki;
- sytuacje kadrowe: zmiana stanowiska przed upływem 6 miesięcy i po nim, zmiana terminu z zawiadomieniem § 8;
- wydruki arkuszy A i B;
- `manage.py test oceny partner`.

## Plan awaryjny

- **Brak sieci:** wszystko działa lokalnie (htmx z pliku, bez fontów zewnętrznych, AI domyślnie wyłączone).
- **Awaria hostingu:** lokalny obraz przez `docker compose up`.
- **Awaria laptopa:** nagranie pokazu z tej samej wersji i wydruki A/B/C zapisane do PDF przed pokazem.
- **Zepsute dane w trakcie:** usuń wolumen (`docker compose down -v`) i uruchom ponownie. Seed wczyta się w kilka sekund.

Cały scenariusz przeszedł 21.11.2026 automatycznie w przeglądarce (Chrome, 1280×720, Playwright) na świeżej bazie z seedem: bez błędów JS i odpowiedzi 5xx, daty i wyniki jak w tabeli (średnia 6,43, termin sprzeciwu 19.04.2027, kryteria nowego okresu do 19.04.2027, ponowna ocena 12.10.2027). Zegar przestawia się w panelu kadr (`/admin/` → Zegar demo). Przed pokazem trzeba jeszcze zrobić próbę z projektorem.
