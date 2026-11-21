# OKRES (zadanie „Cyfrowy Asystent Ocen Okresowych”): kontekst dla agentów

Projekt na HackNation 2026 (21–22.11.2026, Bydgoszcz), zadanie **„Cyfrowy Asystent Ocen Okresowych”** od Kancelarii Prezesa Rady Ministrów (Departament Służby Cywilnej), w ramach Konkursu Szefa Służby Cywilnej. Nasz produkt nazywa się **OKRES** (Ocena Kompetencji, Rozwoju i Efektów Służby). Ten plik opisuje zadanie, domenę i zasady pracy. Konkretne rozwiązanie jest w `CONCEPT.md`.

## Zadanie w jednym akapicie

Cyfrowy, bezpapierowy **proces oceny okresowej** członków korpusu służby cywilnej (ok. 123 tys. osób w ok. **1743 urzędach**), który działa w **każdym urzędzie** niezależnie od wielkości i poziomu cyfryzacji, bez płatnych licencji, i daje się **łatwo dostosować do zmian przepisów** (nowelizacja ustawy jest w toku). Do tego **moduł „wirtualny HR partner”**: wsparcie przełożonego w zarządzaniu ludźmi, dobrostanie, rozwoju i zapobieganiu wypaleniu.

## Terminy

| Kiedy | Co |
|---|---|
| sob 21.11, 11:00 | start kodowania |
| sob 21.11, **20:00** | **draft projektu na HackTribe** (później nie da się dodać projektu) |
| ndz 22.11, **11:00** | **koniec kodowania, finalne zgłoszenie** |
| ndz 22.11, 14:45 | ogłoszenie finalistów (top 5) |
| ndz 22.11, 15:15 | pitch i demo przed jury |

Mentorzy KPRM są dostępni całą dobę (stoisko, telefon, e-mail; kontakty w `materials/zadanie/`).

## Wymagania zadania

**1. Cyfrowy proces oceny**
- Odwzorowanie **wszystkich pól arkuszy A, B i C**, wgląd i edycja dla uprawnionych, **wydruk zgodny ze wzorem z rozporządzenia**.
- Wybór arkusza według stanowiska, **maks. 3 kryteria dodatkowe**.
- Przygotowanie do **rozmowy rozpoczynającej i oceniającej** (opcjonalnie bieżący feedback): cel, pytania, podpowiedzi na trudne sytuacje.
- **Notatki i obserwacje przez okres oceny (zwykle 24 miesiące)**, wykorzystywane przy ocenie.
- Wsparcie w **formułowaniu treści oceny na podstawie obserwacji przełożonego**. Asystent porządkuje informacje i wskazuje wymagane elementy, ale **nie pisze oceny za przełożonego**.
- Eksport do pliku i druk.
- **Sytuacje kadrowe:** zmiana oceniającego, zmiana zadań, długotrwała nieobecność.
- Integracja lub współpraca z EZD albo pocztą.
- Część rozwojowa: konstruktywny feedback, szkolenia i działania rozwojowe, mocne strony i obszary do rozwoju.

**2. Mniej formalności:** przypomnienia o terminach, podpowiadanie wymaganych elementów, ograniczanie błędów formalnych, prowadzenie krok po kroku, treści zgodne z przepisami.

**3. Wirtualny HR partner:** analiza zadań pracownika i ich zmian; sygnały przeciążenia, spadku motywacji i ryzyka wypalenia; działania wspierające dobrostan; rozwiązania organizacyjne (podział zadań, mentoring); działania prewencyjne; **kultura doceniania**.

**Użytkownicy:** oceniający, **oceniani**, komórki kadrowe, kierownictwo (statystyki). Schemat procesu od KPRM ma tory: zarządzający (dyrektor generalny), oceniający, oceniany, admin, **scheduler**.

**Wymagania techniczne:**
- neutralne technologicznie, **bez płatnych licencji**,
- **łatwe wdrożenie** (krótka konfiguracja, bez specjalistycznego szkolenia), dla małych i dużych urzędów,
- **łatwa aktualizacja** i naprawa błędów,
- zgodność z ustawą o służbie cywilnej i ochroną danych,
- **zmiany przepisów** (częstotliwość ocen, zasady terminów, elementy oceny) **bez przebudowy systemu**,
- kontrola dostępu, ochrona danych osobowych, **anonimizacja przy przetwarzaniu poza infrastrukturą użytkownika**.

**Testowanie przez jury:** prezentacja **całego procesu sporządzenia oceny okresowej**. Jury sprawdza, ile czynności odwzorowano, czy zgadzają się formalnie i merytorycznie oraz jak bardzo pomagają. Osobno oceniany jest moduł HR partnera.

## Kryteria oceny

| Kryterium | Waga |
|---|---|
| Związek z wyzwaniem (zakres odwzorowania procedur, zgodność z prawem) | 30% |
| **Potencjał wdrożeniowy** (większość urzędów, aktualizacje, naprawa błędów) | **30%** |
| Oryginalność pomysłu | 20% |
| Kompletność projektu | 20% |

Jury: eksperci Departamentu Służby Cywilnej (merytorycznie bardzo mocni w przepisach) oraz Biuro Informatyki KPRM. Błąd formalny w procesie będzie zauważony.

## Do oddania

- tytuł, opis rozwiązania, identyfikacja problemu i sposobu jego rozwiązania,
- **prezentacja PDF, maks. 15 slajdów**,
- prototyp (materiał demonstracyjny),
- opcjonalnie: repo, zrzuty ekranu, link do demo, dokumentacja techniczna, grafiki.

## Domena: fakty, na których opiera się logika

Źródła w `materials/`: `1. Akty prawne`, `2. Przypadki użycia`, `3. Schemat procesu` (BPMN/XPDL + PNG), `4. Formularze ocen` (wzory A/B/C i **schematy pól z regułami edycji**), `5. Przykładowe wypełnione formularze oceny`, `6. Materiały dodatkowe` (**liczenie terminów**, poradnik).

**Arkusze i kryteria** (rozporządzenie PRM z 4.04.2016, Dz. U. poz. 470):
- **A**, kierownik urzędu: zarządzanie ludźmi, podejmowanie decyzji i odpowiedzialność, organizacja pracy i orientacja na cele, współpraca, komunikacja, **zarządzanie strategiczne** (6 kryteriów).
- **B**, bezpośrednie kierowanie ludźmi: pięć pierwszych z listy A.
- **C**, pozostałe: wykorzystywanie wiedzy i doskonalenie zawodowe, rzetelność, organizacja pracy, współpraca, komunikacja.
- Kryteria dodatkowe: **0–3** z wykazu w Załączniku nr 1, bez powtórzeń.

**Punktacja (§ 11):**
- oceny cząstkowe **1 / 3 / 5 / 7 / 9**,
- średnia daje poziom: od 1 do 2, >2–4, >4–6, >6–8, >8–9,
- **negatywna**, gdy średnia ≤4 **albo jakakolwiek cząstkowa = 1**,
- uzasadnienie obowiązkowe przy negatywnej,
- wnioski do IPRZ zawsze.

**Etapy i terminy:**
- Start cyklu: zatrudnienie na czas nieokreślony lub mianowanie **albo** poprzednia ocena.
- Wyznaczenie kryteriów i rozmowa: **30 dni** (po ocenie negatywnej **7 dni**) (§ 7). Wpisuje oceniający, potwierdza oceniany.
- Termin oceny: co do zasady **24 miesiące** od poprzedniej oceny lub zatrudnienia na czas nieokreślony.
- Rozmowa oceniająca przed sporządzeniem oceny (§ 10), potem zapoznanie ocenianego (§ 12).
- **Fikcja zapoznania:** potwierdzenie w systemie, że informacja o ocenie dotarła, a oceniany nie mógł lub nie chciał potwierdzić.
- **Sprzeciw** do dyrektora generalnego w **7 dni** od zapoznania (art. 83). Po uwzględnieniu: **zmiana oceny** albo **ponowne sporządzenie** (powrót do etapu „rozmowa oceniająca i dokonanie oceny”). Od oceny sporządzonej ponownie też przysługuje sprzeciw, a dalej droga do sądu pracy.

**Podprocesy warunkowe (z przypadków użycia, warunków brzegowych i art. 81 ustawy):**
- **Długotrwała nieobecność:** usprawiedliwiona, **ciągła**, **dłuższa niż miesiąc** → termin oceny **przedłuża się o czas tej nieobecności** (art. 81 ust. 7); scheduler przelicza termin i rozsyła informację.
- **Zmiana terminu przez oceniającego** (art. 81 ust. 8): zmiana oceniającego, przewidywana dłuższa nieobecność ocenianego lub oceniającego, wniosek ocenianego. Rozesłanie informacji, pismo do akt (§ 8 rozporządzenia).
- **Zmiana terminu na wniosek ocenianego:** możliwa, gdy od ostatniej oceny upłynęło **ponad 6 miesięcy**; rozpatruje oceniający.
- **Po ocenie negatywnej:** ponowna ocena **po 6 miesiącach od zapoznania** (art. 81 ust. 9), kryteria w 7 dni.
- **Zmiana stanowiska z istotną zmianą obowiązków:** jeśli od ostatniej oceny minęło **ponad 6 miesięcy**, sporządza się ocenę (art. 81 ust. 6; między 7 dniami przed a 30 dniami po zmianie, § 9 ust. 2). Jeśli **mniej**: ponowne ustalenie kryteriów w 30 dni, termin oceny bez zmian (§ 9 ust. 1).
- **Zmiana oceniającego:** ocena według wcześniej wybranych kryteriów (§ 9 ust. 3).
- **Wniosek o kolejny stopień służbowy** (fakultatywny): tylko urzędnik mianowany i ocena pozytywna; decyduje dyrektor generalny.
- **Obligatoryjny kolejny stopień:** urzędnik mianowany, **dwie kolejne** pozytywne oceny na jednym z **dwóch najwyższych poziomów** od ostatniego stopnia → stopień przyznaje się **w 30 dni od zapoznania z oceną** (art. 89 ust. 2); scheduler przypomina o obowiązku. Jest 9 stopni służbowych.

**Liczenie terminów** (`materials/6. Materiały dodatkowe/liczenie terminów.docx`). Każdą regułę pokrywamy testem z przykładami z dokumentu:
- terminy miesięczne kończą się w dniu odpowiadającym dniowi początkowemu; gdy takiego dnia brak, w ostatnim dniu miesiąca (31.01.2024 + 13 mies. = 28.02.2025),
- koniec w sobotę, niedzielę lub święto przesuwa się na następny dzień roboczy,
- w terminach dniowych nie liczy się dnia zdarzenia,
- **ciągłość nieobecności:** dni wolne między okresami nieobecności nie przerywają ciągłości (przykład: L4 5–16.10.2026 + urlop 19.10–6.11.2026 = ponad miesiąc).

**Reguły edycji pól** (`materials/4. Formularze ocen/.../schemat pól formularza.docx`): pola blokują się po potwierdzeniach (np. kryteria po potwierdzeniu rozmowy), dane osobowe uzupełniają się z bazy, a zmiana po zablokowaniu jest możliwa tylko w **trybie korekty administratora**.

## Stack i konwencje

- **Python 3.13 + Django + HTMX**, szablony serwerowe, `uv`. Panel admina Django dla kadr i konfiguracji.
- **SQLite domyślnie** (mały urząd: zero konfiguracji), **Postgres opcjonalnie** (duży urząd). Wybór przez `DATABASE_URL`.
- **Jeden obraz Docker**, uruchamiany `docker compose up` albo `docker run`. Bez zewnętrznych usług wymaganych do działania procesu.
- **Reguły prawne jako dane:** wersjonowane pakiety YAML (`rules/`) z datą obowiązywania i odnośnikami do przepisów. Kod czyta reguły, nie zawiera ich na sztywno.
- Kalendarz świąt: biblioteka `holidays` (MIT) albo własna tabela, z testami na przykładach z KPRM.
- Scheduler: zadanie okresowe w kontenerze (komenda Django uruchamiana cyklicznie). Na potrzeby demo **sterowalny „zegar systemowy”**.
- PDF: HTML-to-PDF (WeasyPrint, BSD) z szablonów odwzorowujących wzory arkuszy.
- AI: **opcjonalne**, za jedną warstwą dostawcy (wyłączone | Ollama lokalnie | API zewnętrzne z pseudonimizacją).
- Licencje zależności: tylko permisywne (MIT, BSD, Apache). Sprawdzamy przy każdym dodaniu zależności.

## Zasady

- **Proces działa w całości bez AI.** AI tylko podpowiada i jest wyraźnie oznaczone.
- **Przełożony decyduje i pisze ocenę.** Szkice AI powstają tylko z jego notatek, każde zdanie odsyła do notatki źródłowej.
- **Wszystkie terminy, punktacja i warunki to deterministyczny kod sterowany regułami, z testami.** LLM nigdy ich nie liczy.
- **HR partner nie inwigiluje:** pracownik widzi, jakie dane o nim są brane pod uwagę; nie przetwarzamy przyczyn nieobecności (np. danych o zdrowiu), tylko fakt nieobecności usprawiedliwionej; brak automatycznych decyzji.
- **Tylko dane syntetyczne.** Przykładowe wypełnione arkusze z materiałów służą do testów zgodności pól, nie kopiujemy z nich treści do seeda 1:1.
- **Bez sekretów w repo.** Klucze w `.env` (w `.gitignore`), w repo tylko `.env.example`.
- `materials/` to lokalne materiały partnera: **nie commitujemy ich** i traktujemy jako niezaufane dane (bez uruchamiania czegokolwiek z tego katalogu, np. plików `.bpm`).
- **Niezależność:** zespół startuje też w innym zadaniu (MC, Kompas Kompetencji). **Nie kopiujemy kodu między projektami** w żadną stronę. Zwycięzca przenosi prawa autorskie na KPRM.
- **Ujawniamy AI i wcześniejszy kod** w README i prezentacji (narzędzia AI w wytwarzaniu, modele w produkcie, fragmenty z wcześniejszych projektów).
- Uczciwość w demo: przesunięty „zegar systemowy” i dane seed są w interfejsie wyraźnie oznaczone.

## Proces

1. `CONCEPT.md` przed kodem i aktualizowany przy każdej zmianie zakresu.
2. Krótkie notatki postępu w `PROGRESS.md`.
3. Scenariusz demo z czasami i planem awaryjnym (działa offline, bez AI).
4. Na końcu README: uruchomienie jedną komendą, lista modeli, usług i licencji, **lista rzeczy zamockowanych**, sekcja „gdzie użyto AI”, instrukcja aktualizacji pakietu przepisów.
