# OKRES: koncepcja (wersja 2, sob 21.11, popołudnie)

> **Proces oceny jako system, nie formularz.** Przepisy są danymi, terminy liczą się same, każdy urząd uruchamia całość jednym kontenerem, a nowelizację wgrywa się jak aktualizację, bez przebudowy systemu.

**OKRES** (*Ocena Kompetencji, Rozwoju i Efektów Służby*) to nasze rozwiązanie zadania „Cyfrowy Asystent Ocen Okresowych” (KPRM, Departament Służby Cywilnej).

- „Okres” to słowo z samej domeny: okres oceny, 24-miesięczny (a po nowelizacji być może 12-miesięczny) cykl. Rozwinięcie nazwy opisuje trzy części systemu: ocenę, rozwój i efekty.
- Na slajdach i w nagłówku: **„OKRES – Ocena Kompetencji, Rozwoju i Efektów Służby”**. W tekście: OKRES (wersalikami).
- Hasło na pitch: **„Nowelizacja to nowy plik, nie nowy przetarg.”**

Zmiany względem wersji 1: dopasowanie do składu jury, podpisane pakiety przepisów z własnymi testami, formularz (schemat pól) też jako dane, strażnik formalny z odnośnikami do §, panel sprawozdawczy, system wizualny z kontrastem WCAG, konkretne parametry serwerów i modeli, zaktualizowane ryzyka. Wiedza o projekcie nowelizacji (UDER 102) jest wpięta w demo.

---

## 1. Dla kogo gramy: jury

Źródło: `../hacknation-mentorzy.md`, sekcja 14 (oficjalnej listy jury nie ma, to hipoteza ze stanowisk). Pliku `../hacknation-jury.md` nie ma; ocena jury jest właśnie w `hacknation-mentorzy.md`.

| Osoba (prawdopodobnie w jury) | Kim jest | O co zapyta | Czym go przekonujemy |
|---|---|---|---|
| **Joanna Skrzyńska**, naczelnik wydziału, DSC KPRM | właścicielka procedury, autorka materiałów | „czy to jest zgodne z rozporządzeniem?”, „co przy fikcji zapoznania?”, „a ocena po sprzeciwie?” | **macierz pokrycia** wszystkich przypadków użycia z ich PDF-u, każde pole z regułą edycji ze schematu pól, każde ostrzeżenie z § lub art.; wydruk 1:1 ze wzorem |
| **Michał Włochal**, dyrektor, Zachodniopomorski UW | praktyk: prowadzi urząd, w którym to będzie działać | „ile to kosztuje mój urząd?”, „kto to zainstaluje?”, „co z kadrami, które mają 300 ocen w roku?” | **kreator pierwszego uruchomienia** (15 minut, import CSV), panel kadr z listą „co się dzieje w tym tygodniu”, zero licencji, działa bez informatyka |
| **Kamil Kazimierczuk**, radca, DSC (sprawozdawczość; jedyny „merytoryczny i techniczny”) | zbiera dane od urzędów do sprawozdań | „skąd mam dane do sprawozdania?”, „czy dane są spójne między urzędami?” | **panel kierownictwa + eksport do sprawozdania** (wspólny format dla wszystkich instancji), audyt zmian, jednolity słownik pól z pakietu |
| **Maciej Szczygieł**, naczelnik, Biuro Informatyki KPRM (techniczny) | będzie to utrzymywał lub odbierał | „jak aktualizujecie?”, „jak to zabezpieczacie?”, „licencje?”, „gdzie idą dane do AI?” | jeden obraz OCI, SBOM i lista licencji, **podpisane pakiety przepisów**, migracje automatyczne, AI wyłączone domyślnie i lokalne, pseudonimizacja przy zewnętrznym API |
| mentorzy: Magdalena Pruszyńska-Gora (psycholog, asesorka AC/DC), Jacek Pawłowski, Julia Tyszko, Karolina Świszcz | merytoryka HR i procedury | „czy HR partner nie jest inwigilacją?”, „czy podpowiedzi są zgodne ze standardami ZZL?” | sygnały jawne dla pracownika, bez danych o zdrowiu, bez automatycznych decyzji; katalog działań odwołuje się do **Zarządzenia nr 6 SSC (standardy ZZL), rozdz. „System informacji zwrotnej”** |

**Wnioski dla całego projektu:**

1. To jury **zna przepisy lepiej niż my**. Jeden błąd formalny na demo kosztuje więcej niż brak efektownej funkcji. Każdą regułę konsultujemy z mentorami w sobotę wieczorem i w nocy (są dostępni 24 h).
2. **Potencjał wdrożeniowy (30%) ocenia praktyk i informatyk.** Pokazujemy instalację, aktualizację i zmianę przepisów **na żywo**, a nie na slajdzie.
3. Jury nie jest zespołem ML. **AI nie jest gwiazdą**, tylko dyskretnym, wyraźnie oznaczonym pomocnikiem. Gwiazdą jest proces, który się nie myli.
4. Słownictwo z rozporządzenia, nie z IT: „sporządzenie oceny na piśmie”, „zapoznanie”, „część I arkusza”, „akta osobowe”, a nie „workflow”, „ticket”, „submit”.

---

## 2. Problem

- Oceny w ok. **1743 urzędach** (ok. 123 tys. osób, mediana ok. 70 osób na urząd) powstają głównie **na papierze**, czasem odręcznie. Dla wielu urzędów barierą jest obieg dokumentów cyfrowych i poświadczeń.
- Uwagę pochłaniają formalności: terminy, pola, podpisy. Brakuje jej na jakość oceny i rozwój pracownika.
- Sytuacje kadrowe (nieobecności, zmiana przełożonego, zmiana stanowiska, sprzeciw) łatwo prowadzą do **błędów formalnych**.
- Przełożeni mają kłopot z informacją zwrotną, doborem kryteriów dodatkowych i wnioskami do IPRZ. Sygnały przeciążenia i wypalenia giną.
- **Nowelizacja jest w toku.** Projekt z 20.04.2026 (UDER 102) według dostępnych omówień skraca cykl do **12 miesięcy**, uchyla art. 81 i wprowadza art. 81a, obejmuje ocenami także wyższe stanowiska, a do ocen niezakończonych stosuje przepisy dotychczasowe. Przyjęcie zaplanowano na III kw. 2026. **Narzędzie z regułami wpisanymi w kod zestarzeje się przed wdrożeniem.**

## 3. Użytkownicy (tory ze schematu BPMN KPRM)

| Rola | Co robi w systemie |
|---|---|
| **Oceniający** | wybiera arkusz (podpowiedź) i kryteria dodatkowe, prowadzi dziennik obserwacji, przygotowuje rozmowy, sporządza ocenę, korzysta z HR partnera |
| **Oceniany** | potwierdza rozmowę i zapoznanie, prowadzi listę własnych osiągnięć, składa wniosek o zmianę terminu, widzi licznik sprzeciwu, opcjonalnie robi check-in |
| **Kadry (admin)** | dane pracowników i podległości, nieobecności, zastępstwa, tryb korekty, pakiety przepisów, katalog działań rozwojowych, archiwizacja |
| **Zarządzający (dyrektor generalny)** | rozpatruje sprzeciwy (14 dni) i wnioski o stopień, widzi statystyki, eksportuje dane do sprawozdania |
| **Scheduler** | przypomnienia, przeliczenia terminów, zawiadomienia (§ 8), obowiązek przyznania stopnia (art. 89 ust. 2) |

## 4. Główna idea produktu (cztery filary)

1. **Silnik sprawy** odwzorowujący przypadki użycia i schemat BPMN KPRM: każda ocena to sprawa z osią zdarzeń, etapami, blokadami pól i pełnym audytem.
2. **Przepisy i formularz jako dane:** wersjonowany **pakiet przepisów** (YAML) z datą obowiązywania, odnośnikami do przepisów, **schematem pól arkusza z regułami edycji** i **własnym zestawem testów**. Nowelizacja to nowy pakiet, nie nowy kod.
3. **Jeden kontener, zero zależności zewnętrznych:** SQLite w małym urzędzie, Postgres i SSO w dużym, AI to opcjonalny dodatek, domyślnie wyłączony.
4. **HR partner oparty na jawnych sygnałach,** nie na czarnej skrzynce. Pracownik widzi, co system o nim bierze pod uwagę.

---

## 5. Kryteria → jak je spełniamy

| Kryterium | Waga | Jak je spełniamy | Dowód na demo / w zgłoszeniu |
|---|---|---|---|
| **Związek z wyzwaniem i zgodność z prawem** | 30% | macierz pokrycia **wszystkich** przypadków użycia KPRM (stałe etapy, podprocesy, ogólne, użytkowe); terminy według dokumentu „liczenie terminów” z testami na ich przykładach; reguły edycji 1:1 ze schematów pól A/B/C; **strażnik formalny** z § przy każdym komunikacie; wydruk zgodny ze wzorem z rozporządzenia | strona `/pokrycie` w aplikacji (status z testów, nie z ręki); PDF obok wzoru; próba zatwierdzenia negatywnej oceny bez uzasadnienia → blokada z „§ 11 ust. 3” |
| **Potencjał wdrożeniowy** | **30%** | jeden obraz, `docker run` albo `docker compose up`; **kreator pierwszego uruchomienia**; import CSV; SQLite → Postgres bez zmian kodu; **podpisane pakiety przepisów** dystrybuowane centralnie przez KPRM; migracje przy starcie; licencje wyłącznie permisywne + SBOM; WCAG 2.1 AA (ustawa o dostępności cyfrowej); AI opcjonalne i lokalne | na scenie: wgranie pakietu „projekt nowelizacji (12 mies.)”, testy pakietu przechodzą, nowe sprawy liczą się po nowemu, rozpoczęte zostają przy starych regułach; slajd z wymaganiami sprzętowymi małego, średniego i dużego urzędu |
| **Oryginalność** | 20% | pakiet przepisów **niesie własne testy** i podpis (jak aktualizacja sygnatur antywirusa); **zegar symulacji** (24 miesiące w 2 minuty); HR partner z jawnymi sygnałami i „prawem wglądu” pracownika; **tryb hybrydowy papier + cyfra** z kodem QR; przygotowanie rozmowy z flagami jakości obserwacji (luka, efekt świeżości) | alert „3 zmiany zakresu w 6 tygodni” z wyjaśnieniem i działaniem z katalogu; wydruk z QR prowadzącym do sprawy |
| **Kompletność** | 20% | pełen cykl z podprocesami (nieobecność, zmiana terminu ×2, zmiana stanowiska, zmiana oceniającego, sprzeciw ze zmianą i ponownym sporządzeniem, stopień fakultatywny i obligatoryjny); 5 ról; arkusze A, B, C; dziennik; IPRZ; statystyki; eksporty; README, dokumentacja wdrożeniowa, film | demo od zatrudnienia do akt osobowych; macierz pokrycia z liczbą „X/Y przypadków użycia” |

**Czego nie budujemy, bo jury tego nie ocenia:** aplikacji mobilnej, własnego e-podpisu, czatu jako głównego interfejsu, rozbudowanej analityki ML, ładnych animacji.

---

## 6. Pokrycie przypadków użycia KPRM

Na podstawie `materials/2. Przypadki użycia` (opis + warunki brzegowe). Ta tabela żyje także w aplikacji jako `/pokrycie`: każdy wiersz ma identyfikator (`UC-xx`), ekran i test, a status bierze się z ostatniego przebiegu testów.

| ID | Przypadek użycia | Warunek brzegowy / reguła | Realizacja | Prio |
|---|---|---|---|---|
| UC-01 | wyznaczenie kryteriów oceny | start: umowa na czas nieokreślony lub mianowanie **albo** poprzednia ocena | sprawa zakładana automatycznie przez scheduler | P0 |
| UC-02 | (scheduler) przypomnienie o kryteriach | 30 dni, po negatywnej 7 dni (§ 7) | przypomnienia T-7, T-2, T+0 | P0 |
| UC-03 | (opcjonalnie) zaproszenie na rozmowę | – | zaproszenie e-mail + `.ics` | P1 |
| UC-04 | informacja o kryteriach i rozmowie | wprowadza oceniający; checklista § 5 ust. 1 | część I arkusza, max 3 kryteria bez powtórzeń, termin domyślny z pakietu | P0 |
| UC-05 | potwierdzenie rozmowy i zapoznania z kryteriami | potwierdza oceniany (§ 6 ust. 2) | blokada kryteriów i terminu; kopia części I do ocenianego | P0 |
| UC-06 | (scheduler) przypomnienie o terminie oceny | 24 mies. od poprzedniej oceny / zatrudnienia | T-60, T-30, T-7 dni | P0 |
| UC-07 | (opcjonalnie) zaproszenie na rozmowę oceniającą | – | jak UC-03 | P1 |
| UC-08 | rozmowa oceniająca i dokonanie oceny | checklista § 10; § 11 | część II, punktacja, poziom, wynik z pakietu; strażnik formalny | P0 |
| UC-09 | potwierdzenie zapoznania z oceną | potwierdza oceniany (§ 12) | blokada, start licznika sprzeciwu 7 dni (art. 83 ust. 1) | P0 |
| UC-10 | (opcjonalnie) fikcja zapoznania | informacja dotarła, oceniany nie mógł lub nie chciał potwierdzić | oświadczenie kadr/oceniającego z datą i sposobem doręczenia, adnotacja na arkuszu | P0 |
| UC-11 | długotrwała nieobecność → zmiana terminu | usprawiedliwiona, ciągła, > 1 mies.; termin + czas nieobecności (art. 81 ust. 7) | import nieobecności, scalanie ciągłości (dni wolne nie przerywają), przeliczenie, powiadomienia | P0 |
| UC-12 | zmiana terminu przez oceniającego | art. 81 ust. 8 pkt 1–3; > 6 mies. od ostatniej oceny | formularz z podstawą + **zawiadomienie § 8** (PDF do arkusza) | P1 |
| UC-13 | zmiana terminu na wniosek ocenianego | art. 81 ust. 8 pkt 4; > 6 mies. | wniosek → rozpatrzenie → zawiadomienie § 8 | P1 |
| UC-14 | wniosek o kolejny stopień (fakultatywny) | urzędnik mianowany **i** ocena pozytywna (art. 89 ust. 1) | część III arkusza, umotywowanie obowiązkowe, powiadomienie DG | P1 |
| UC-15 | obligatoryjny kolejny stopień | mianowany, **dwie kolejne** oceny na dwóch najwyższych poziomach od ostatniego stopnia (art. 89 ust. 2) | scheduler: przypomnienie DG, termin 30 dni od zapoznania; blokada przy 9. stopniu | P0 |
| UC-16 | zmiana oceny po uwzględnieniu sprzeciwu | art. 83 ust. 4; sprzeciw rozpatrzony w 14 dni (ust. 3) | DG: decyzja → tryb zmiany, nowa wersja arkusza, powiadomienie | P1 |
| UC-17 | ponowne sporządzenie oceny po sprzeciwie | j.w.; od ponownej też sprzeciw | anulowanie, powrót do etapu „rozmowa oceniająca i dokonanie oceny”, historia wersji | P1 |
| UC-18 | wprowadzenie danych pracownika, podległości | – | panel kadr + import CSV | P0 |
| UC-19 | edycja danych, zmiany podległości, zastępstwa | zmiana oceniającego: kryteria bez zmian (§ 9 ust. 3) | przekazanie sprawy z notatkami (za zgodą) i informacja dla ocenianego | P1 |
| UC-20 | aktualizacja nieobecności | tylko fakt i okres, **bez przyczyny** | CSV / ręcznie | P0 |
| UC-21 | archiwizacja / pobranie danych | akta osobowe | paczka ZIP: PDF + JSON + audyt; eksport do EZD (opisany) | P1 |
| UC-22 | statystyki | – | panel DG + eksport do sprawozdania | P1 |
| UC-23 | wgląd w historię ocen, formularz, pobranie, wydruk | wydruk zgodny ze wzorem | PDF z szablonu pakietu | P0 |
| UC-24 | lista pracowników (szukanie, sortowanie) | – | tabela HTMX z filtrami „termin w 30 dni”, „po terminie” | P0 |
| UC-25 | usunięcie danych pracownika | retencja akt osobowych | usunięcie z pozostawieniem zanonimizowanych statystyk | P1 |
| UC-26 | **zmiana stanowiska z istotną zmianą obowiązków** (spoza listy, z art. 81 ust. 6 i § 9) | > 6 mies.: ocena (−7…+30 dni); < 6 mies.: nowe kryteria w 30 dni, termin bez zmian | kreator zdarzenia kadrowego z rozgałęzieniem | P1 |
| UC-27 | **ponowna ocena po negatywnej** (art. 81 ust. 9) | 6 mies. od zapoznania, kryteria w 7 dni | automatyczne założenie sprawy | P0 |

---

## 7. Pakiety przepisów (serce „potencjału wdrożeniowego”)

### Co jest w pakiecie

```
rules/
  sc-2016-470/                 # rozporządzenie PRM z 4.04.2016 (Dz. U. poz. 470) + ustawa (Dz. U. 2026 poz. 590)
    manifest.yaml              # id, wersja, obowiązuje_od, obowiązuje_do, podstawa prawna, autor, podpis
    cycle.yaml                 # długość cyklu, terminy (kryteria 30/7 dni), ponowna ocena po negatywnej, przesunięcia
    sheets.yaml                # arkusze A/B/C, kryteria obowiązkowe, wykaz kryteriów dodatkowych (Zał. 1) z opisami
    scoring.yaml               # skala 1/3/5/7/9, przedziały średniej, warunki negatywnej
    forms/                     # schemat pól A/B/C: pole → kto, na jakim etapie, kiedy blokada, źródło danych
      sheet_b.yaml
    templates/                 # szablony wydruku HTML zgodne ze wzorami z załączników 2–4
    texts.yaml                 # pouczenia (art. 83), treść zawiadomienia § 8, oświadczenia
    tests/                     # przykłady z dokumentu „liczenie terminów” + przypadki graniczne
      deadlines.yaml
      scoring.yaml
  projekt-nowelizacji-demo/    # HIPOTETYCZNY pakiet: cykl 12 mies., ocena wyższych stanowisk; oznaczony jako przykład
```

Przykład (`cycle.yaml`, fragment):

```yaml
review_cycle:
  length: { months: 24 }
  basis: "art. 81 ust. 4 ustawy o służbie cywilnej"
criteria_setting:
  default: { days: 30, basis: "§ 7 pkt 1 rozporządzenia" }
  after_negative: { days: 7, basis: "§ 7 pkt 2 rozporządzenia" }
long_absence:
  min_length: { months: 1, strict: true }   # „dłużej niż miesiąc”
  continuity: weekends_and_holidays_bridge  # wg „liczenie terminów” KPRM
  effect: extend_deadline_by_absence
  basis: "art. 81 ust. 7"
```

### Jak to działa

- Silnik zna **operacje** (dodaj miesiące wg kodeksu cywilnego, przesuń na dzień roboczy, policz dni od zdarzenia, scal nieobecności), a pakiet mówi, **których i z jakimi parametrami** użyć. Nowe przepisy, które da się wyrazić tymi operacjami, nie wymagają kodu. Nowy typ reguły wymaga nowej operacji: to zmiana kodu, ale lokalna i z testem.
- **Każda sprawa zapamiętuje pakiet**, według którego się toczy (wzór: przepis przejściowy § 13 i zapowiedź z projektu nowelizacji „do ocen niezakończonych stosuje się przepisy dotychczasowe”). Reguła przejściowa też jest w manifeście.
- **Pakiet niesie własne testy.** Przy wgraniu system uruchamia je i odrzuca pakiet, jeśli którykolwiek nie przechodzi. Panel kadr pokazuje wynik: „27/27 testów zgodnych”.
- **Podpis:** KPRM (DSC) publikuje pakiet podpisany kluczem Ed25519 (biblioteka `cryptography`, Apache/BSD). Instancja urzędu przyjmuje tylko pakiety z zaufanym podpisem. Urząd nie musi rozumieć YAML-a: dostaje plik i klika „wgraj”, albo instancja sama pobiera nowy pakiet z publicznego adresu (opcjonalnie).
- **Diff pakietów** w panelu: „zmienia się: długość cyklu 24 → 12 mies.; dotyczy 14 nowych spraw; 31 rozpoczętych zostaje przy dotychczasowych przepisach”.
- Na demo: **hipotetyczny pakiet „projekt nowelizacji (demo)”**, wyraźnie opisany jako przykład oparty na publicznych omówieniach UDER 102, a nie treść ustawy.

### Formularz jako dane

Schemat pól z `materials/4. Formularze ocen/.../schemat pól formularza.docx` przenosimy 1:1 do `forms/sheet_*.yaml`:

```yaml
- field: additional_criteria
  part: I
  editable_by: evaluator
  editable_in: [criteria_setting]
  lock_after: criteria_confirmed_by_employee
  rules: [max_3, unique, from_catalog]
  correction: admin_only
- field: justification
  part: II
  required_if: "result == 'negative'"
  block_submit_message: "Uzasadnienie jest obowiązkowe przy ocenie negatywnej (§ 11 ust. 3)."
```

Na tej podstawie generujemy formularz HTML, blokady, komunikaty strażnika **i** wydruk. Zmiana wzoru arkusza w nowelizacji = zmiana tego pliku i szablonu.

> Zauważyliśmy, że w schemacie pól arkusza B pole „UZASADNIENIE PRZYZNANEJ OCENY” występuje dwukrotnie z różnymi regułami. Przyjmujemy wersję z blokadą przy ocenie negatywnej (zgodną z § 11 ust. 3) i pytamy mentorów. Takie znaleziska pokazujemy jury jako dowód, że czytaliśmy materiały dokładnie.

---

## 8. Strażnik formalny i prowadzenie krok po kroku

- **Lista kontrolna etapu** po prawej stronie każdego ekranu sprawy: co jest wymagane, co zrobione, co blokuje przejście dalej. Każdy punkt z podstawą prawną (link do treści przepisu w pakiecie).
- **Blokady twarde** (nie da się przejść): brak uzasadnienia przy negatywnej, brak wniosków do IPRZ, powtórzone kryterium, więcej niż 3 kryteria dodatkowe, wniosek o stopień przy ocenie negatywnej lub u pracownika (nie urzędnika), wniosek przy 9. stopniu, brak umotywowania wniosku o stopień.
- **Ostrzeżenia miękkie** (można przejść po potwierdzeniu): termin minął, okres oceny krótszy niż 6 mies., data rozmowy po dacie oceny, kryterium oceniane bez żadnej notatki.
- **Oś sprawy:** poziomy pasek etapów (kryteria → rozmowa → obserwacje → rozmowa oceniająca → ocena → zapoznanie → sprzeciw → akta) z datami „do kiedy” liczonymi z pakietu i z podpowiedzią, dlaczego taki termin („16.03.2026 → poniedziałek 16.03.2026; termin 24 mies. od 16.03.2024, art. 81 ust. 4”).
- **Wyjaśnienie każdego terminu:** kliknięcie daty pokazuje rachunek krok po kroku (start, +24 mies., nieobecność 05.10–06.11.2026 = 33 dni, przesunięcie z soboty na poniedziałek). Dla jury to dowód, że nie liczymy „na oko”.

## 9. Notatki i przygotowanie rozmów

- **Dziennik obserwacji:** szybka notatka (tekst, data, kryterium, wydźwięk: pozytywna, neutralna, do poprawy). Widzi ją tylko oceniający. Przy zmianie oceniającego przekazanie notatek wymaga decyzji (domyślnie: tylko lista dat i kryteriów, bez treści).
- **Lista osiągnięć ocenianego:** oceniany sam dopisuje, co zrobił, i decyduje, czy udostępnić przełożonemu przed rozmową.
- **Rozmowy bieżące (feedback):** scheduler proponuje krótką rozmowę co kwartał, zgodnie z rekomendacją cyklicznej informacji zwrotnej w standardach ZZL (Zarządzenie nr 6 SSC). Notatka z rozmowy trafia do dziennika.
- **Przed rozmową rozpoczynającą:** checklista § 5 ust. 1 (obowiązki z OSP, kryteria, oczekiwania, cele), **pomoc w doborze kryteriów dodatkowych** (opisy z Zał. 1 obok siebie, pytania pomocnicze: „Czy stanowisko wymaga wystąpień publicznych?”), agenda do druku.
- **Przed rozmową oceniającą:** checklista § 10, zestawienie notatek per kryterium i **flagi jakości obserwacji** (deterministyczne, bez AI): kryterium bez notatki; ponad 60% notatek z ostatnich 2 miesięcy (efekt świeżości); w kryterium wyłącznie negatywne notatki; brak notatek dłużej niż 6 miesięcy.
- **Biblioteka trudnych rozmów** (statyczna, bez AI, konfigurowalna przez urząd): ocena negatywna, pracownik się nie zgadza, emocje, sprawy osobiste, powrót po długiej nieobecności. Każda karta: cel, struktura, przykładowe sformułowania, czego unikać.
- **Szkic uzasadnienia i wniosków do IPRZ** (AI, opcjonalne): powstaje **tylko z notatek przełożonego**. Każde zdanie ma odnośnik do notatki źródłowej, zdania bez źródła są odrzucane. Szkic trafia do pola dopiero po kliknięciu „wstaw i edytuję”, oznaczony fioletowym znacznikiem „szkic AI”, który znika po edycji przez człowieka. Bez AI ten sam ekran działa jako uporządkowane zestawienie notatek do ręcznego przepisania.

## 10. Wirtualny HR partner

Moduł oceniany osobno, więc ma własny ekran („Zespół”) i własny moment w demo.

**Źródła sygnałów:** wyłącznie dane już będące w systemie albo dobrowolne.

| Źródło | Przykład sygnału (reguła z `partner.yaml`) | Działanie z katalogu |
|---|---|---|
| zmiany zakresu zadań (zdarzenia kadrowe, notatki „zmiana zadań”) | ≥ 3 zmiany zakresu lub priorytetów w 6 tygodni | rozmowa o priorytetach, przesunięcie zadania, odciążenie |
| nieobecności (fakt i długość, bez przyczyny) | powrót po nieobecności > 1 mies. | rozmowa powitalna, plan wdrożenia, przegląd celów |
| dobrowolny check-in ocenianego (1 klik co 2 tygodnie, skala 1–5, może wyłączyć) | spadek w 3 kolejnych check-inach | rozmowa wspierająca, mentoring, informacja o programie wsparcia psychologicznego urzędu |
| notatki przełożonego | brak pozytywnej notatki przez 4 miesiące | **docenienie**: konkretna podpowiedź, za co i jak |
| wynik oceny | kryterium na poziomie „poniżej oczekiwań” | działania rozwojowe z katalogu do IPRZ |
| kamienie milowe | zakończony projekt, rocznica zatrudnienia, nowy stopień | podpowiedź docenienia |
| obciążenie zespołu | jeden pracownik ma ≥ 40% zadań oznaczonych „pilne” w zespole | podział zadań, zastępstwo, wsparcie zespołu |

- Każdy sygnał ma **wyjaśnienie** (jakie dane, jaka reguła, z jakiego okresu) i **status**: „omówione”, „zaplanowane działanie”, „nieaktualne”. Sygnał nigdy nie trafia do arkusza oceny ani do kadr.
- **Kultura doceniania:** „Kalendarz docenienia” dla przełożonego (kto dawno nie usłyszał dobrego słowa, jakie są okazje) i karta „podziękowanie” do wysłania pracownikowi z systemu.
- **Katalog działań** każdy urząd konfiguruje sam: własne szkolenia, KSAP, mentoring, programy wsparcia. W seedzie kilkanaście pozycji ogólnych.
- **Prawo wglądu:** w profilu ocenianego jest sekcja „Jakie dane o mnie są brane pod uwagę” z listą kategorii i przełącznikiem check-inu.
- **Opcjonalne AI:** „porozmawiaj o sytuacji w zespole”. Model dostaje wyłącznie **zanonimizowane sygnały** (np. „Osoba A: 3 zmiany zakresu, spadek check-inów”) i może proponować tylko działania z katalogu, z odnośnikiem do sygnału. Gdy dane nie wystarczają, mówi to wprost.
- Na slajd: skrócona analiza RODO (minimalizacja, brak danych o zdrowiu, brak profilowania z automatycznymi decyzjami w rozumieniu art. 22 RODO, rola IOD, retencja sygnałów 12 mies.).

---

## 11. Wdrażalność (dla dyrektora urzędu i dla Biura Informatyki)

### Trzy profile urzędu, jedna baza kodu

| Profil | Przykład | Konfiguracja | Wymagania sprzętowe (szacunek) |
|---|---|---|---|
| **mały** (do 50 osób) | inspekcja powiatowa, urząd skarbowy | `docker run`, SQLite na wolumenie, login i hasło, AI wyłączone, druk z QR | 1 vCPU, 1 GB RAM, 2 GB dysku; nawet istniejący serwer plików |
| **średni** (50–1000) | urząd wojewódzki, urząd centralny | `docker compose`: aplikacja + Postgres, SMTP, LDAP/AD, opcjonalnie Ollama | 2 vCPU, 2–4 GB RAM, 10 GB |
| **duży** (1000+) | ministerstwo | Postgres, SSO (OIDC lub LDAP), eksport do EZD RP, model lokalny na GPU albo zewnętrzny z pseudonimizacją | 4 vCPU, 4–8 GB RAM; AI: GPU 12 GB VRAM (opcjonalnie) |

Obciążenie jest małe: przy 123 tys. osób i cyklu 24 mies. to ok. 5 tys. ocen miesięcznie **w całym kraju**. Mediana urzędu to kilka ocen w tygodniu.

**Wariant centralny (do rozmowy z KPRM):** ta sama aplikacja uruchamiana przez KPRM lub COI jako **osobna instancja na urząd** na infrastrukturze rządowej, dla urzędów bez własnego informatyka. Izolujemy instancjami, nie kodem: nie ma wielodostępności, więc nie ma ryzyka wycieku między urzędami.

### Wdrożenie w 15 minut

1. `docker run -p 8000:8000 -v okres:/data ghcr.io/…/okres:1.0.0`
2. **Kreator pierwszego uruchomienia:** nazwa urzędu, miejscowość (do pól „miejscowość” w arkuszu), konto administratora kadr, wybór pakietu przepisów.
3. Import CSV pracowników, podległości i nieobecności (szablony do pobrania w kreatorze, udokumentowany format; Excel → „zapisz jako CSV”).
4. System zakłada sprawy i liczy terminy dla wszystkich. Kadry widzą listę „co trzeba zrobić w tym tygodniu”.

### Aktualizacja i naprawa błędów

- **Kod:** nowa wersja obrazu (semver), migracje bazy uruchamiane automatycznie przy starcie, kopia bazy przed migracją. Powrót do poprzedniej wersji: poprzedni tag obrazu + kopia.
- **Przepisy:** nowy podpisany pakiet, bez zmiany obrazu (sekcja 7).
- **Zgłaszanie błędów:** w stopce „zgłoś błąd” z identyfikatorem wersji obrazu i pakietu (bez danych osobowych).
- Repozytorium z CI: testy (w tym testy pakietów), lint, skan zależności, SBOM (CycloneDX), lista licencji generowana automatycznie.

### Integracje

- **Poczta:** powiadomienia przez SMTP urzędu + zaproszenia `.ics`; w demo log wiadomości w interfejsie.
- **EZD (w tym EZD RP):** eksport paczki sprawy (PDF arkusza + metadane JSON + audyt) gotowej do zarejestrowania w EZD. Integracja przez API EZD RP opisana; do rozmowy z mentorami NASK (piaskownica). Na demo zamockowane.
- **Systemy kadrowe:** CSV jako minimum, API REST (OpenAPI) do importu i eksportu dla urzędów z integracją.
- **Sprawozdawczość:** eksport zbiorczy (liczba ocen, rozkład poziomów, oceny negatywne, sprzeciwy i ich wynik, stopnie fakultatywne i obligatoryjne, terminowość) w jednolitym formacie dla wszystkich instancji, do sprawozdania dyrektora generalnego (dawniej przez SWEZ_HR). **Format do potwierdzenia z Kamilem Kazimierczukiem.**

### Podpisy i tryb hybrydowy

- Urząd **bez** obiegu cyfrowego: system drukuje arkusz zgodny ze wzorem z kodem QR (identyfikator sprawy i wersja), podpisy odręczne, skan wgrywany do sprawy. Proces i terminy i tak prowadzi system.
- Urząd **z** e-podpisem: eksport PDF do podpisu kwalifikowanego lub profilem zaufanym (opisane, zamockowane).
- Potwierdzenia w systemie (zalogowany użytkownik + znacznik czasu + audyt) jako dowód czynności. Czy to wystarcza jako „podpis” w rozumieniu § 6 i § 12: **pytanie do mentorów**.

### Bezpieczeństwo i ochrona danych

- Role i uprawnienia per pole (z `forms/*.yaml`) i per sprawa; oceniany widzi tylko swoje sprawy, oceniający tylko podległych.
- **Audyt** każdej zmiany pola, każdej korekty administratora (z obowiązkowym powodem) i każdego odczytu arkusza przez kadry.
- Hasła: Argon2; sesje HttpOnly/Secure; CSRF Django; nagłówki bezpieczeństwa; limit prób logowania.
- **Anonimizacja przy przetwarzaniu poza infrastrukturą urzędu:** warstwa pseudonimizacji przed każdym wywołaniem zewnętrznego API (imiona, nazwiska, komórki, stanowiska, daty → tokeny; mapa zostaje lokalnie; odpowiedź jest odtwarzana lokalnie). Domyślnie AI wyłączone, drugi w kolejności tryb to model lokalny.
- Kopie zapasowe: komenda `okres backup` (zaszyfrowany plik), w compose zadanie nocne.
- Dostępność: **WCAG 2.1 AA** (ustawa z 4.04.2019 o dostępności cyfrowej), deklaracja dostępności w stopce, pełna obsługa klawiaturą, test axe w CI.

---

## 12. System wizualny

**Kierunek:** urzędowy, spokojny, czytelny: „jak dobrze zaprojektowany druk urzędowy”. Kolorystyka nawiązuje do barw państwowych i portalu gov.pl (biel, granat, czerwień tylko jako akcent), ale nie kopiuje znaku gov.pl ani logo służby cywilnej (zgodność z identyfikacją gov.pl do sprawdzenia z mentorami). Wszystkie pary tekst/tło sprawdzone skryptem kontrastu (WCAG 2.1, próg AA 4,5:1).

| Token | Kolor | Użycie | Kontrast |
|---|---|---|---|
| `--okres-granat` | `#0B3A6E` | nagłówek, logo, przyciski główne (biały tekst) | 11,4:1 z białym |
| `--okres-niebieski` | `#1A5DAB` | linki, fokus, aktywny etap na osi sprawy | 6,6:1 z białym |
| `--okres-tekst` | `#1A1F29` | tekst podstawowy | 16,5:1 |
| `--okres-tekst-2` | `#4A5363` | tekst pomocniczy, **pola zablokowane** (na `#ECEEF2` z ikoną kłódki) | 7,8:1 / 7,2:1 na `#F4F6F9` |
| `--okres-tlo` / `--okres-tlo-2` | `#FFFFFF` / `#F4F6F9` | tło / panele boczne, lista kontrolna | – |
| `--okres-ramka` | `#D0D7E1` | obramowania, siatka arkusza | – |
| `--okres-czerwien` | `#B3122E` | **tylko**: termin przekroczony, blokada formalna, błąd (tło `#FDECEF`) | 6,9:1 / 6,1:1 |
| `--okres-zielen` | `#1B6B3A` | etap zakończony, test pakietu zaliczony (tło `#E8F4EC`) | 6,5:1 / 5,8:1 |
| `--okres-bursztyn` | `#8A4B00` na `#FFF3D6` | ostrzeżenie miękkie, termin w ciągu 7 dni | 6,2:1 |
| `--okres-morski` | `#0F6B6B` (tło `#E6F4F3`) | **moduł HR partnera** (osobny kolor = „doradztwo, nie procedura”) | 6,3:1 / 5,6:1 |
| `--okres-fiolet` | `#5B3FA0` (tło `#F1EDFA`) | **wyłącznie treści AI**: znacznik „szkic AI”, ramka podpowiedzi | 7,9:1 / 6,9:1 |
| `--okres-demo` | pasek `#FFF3D6` z tekstem `#8A4B00` | **„Tryb demonstracyjny: zegar przesunięty na 14.03.2028, dane fikcyjne”** zawsze na górze | 6,2:1 |

**Zasady:**
- Kolor nigdy nie jest jedynym nośnikiem informacji: status zawsze ma też ikonę i słowo („zablokowane”, „po terminie”).
- Ocena negatywna **nie** jest na czerwono. Wynik to treść decyzji przełożonego, nie alarm; czerwień rezerwujemy dla błędów procesu.
- AI ma jeden kolor i jedną etykietę w całym systemie, żeby jury i użytkownik od razu widzieli, co pochodzi od modelu.
- **Typografia:** stos systemowy w interfejsie (`system-ui, "Segoe UI", Roboto, sans-serif`), bez pobierania fontów z sieci (działa offline i w zamkniętych sieciach urzędów). W PDF: **Liberation Sans** (OFL) dołączony do obrazu, żeby wydruk wyglądał tak samo wszędzie. Bazowy rozmiar 16 px, interlinia 1,5.
- **Logo:** słowo „OKRES” wersalikami w granacie, z cienką poziomą osią i znacznikiem „dziś” (motyw osi okresu oceny). Bez godła i bez barw flagi w znaku.
- **Układ:** desktop first (komputery w urzędach), responsywnie do tabletu; trzy kolumny na ekranie sprawy: oś etapów u góry, formularz w środku, lista kontrolna po prawej. Wydruk to osobny szablon zgodny ze wzorem, nie „print CSS” ekranu.

---

## 13. Architektura i technologia

```
                ┌──────────────────────── jeden obraz OCI (python:3.13-slim, wersja przypięta) ───────────────────────┐
 przeglądarka ─▶│ gunicorn → Django 5.2 LTS + HTMX (szablony serwerowe)            okres scheduler (pętla co 5 min) │
                │  ├─ cases/      silnik sprawy: etapy, zdarzenia, blokady pól, audyt, wersje arkusza                 │
                │  ├─ rules/      loader pakietów, walidacja schematu, podpis Ed25519, testy pakietu, diff             │
                │  ├─ deadlines/  operacje kalendarzowe, święta PL, ciągłość nieobecności, „wyjaśnij termin”           │
                │  ├─ forms_pdf/  formularze z forms/*.yaml, wydruk HTML → PDF (WeasyPrint)                            │
                │  ├─ notes/      dziennik obserwacji, osiągnięcia ocenianego, rozmowy bieżące                         │
                │  ├─ partner/    sygnały z partner.yaml, katalog działań, check-iny, docenienia                       │
                │  ├─ reports/    statystyki DG, eksport do sprawozdania, paczka do EZD                                │
                │  ├─ ai/         dostawca: off | ollama | openai-compatible (+ pseudonimizacja), cytowanie notatek    │
                │  └─ demo/       zegar symulacji, przełącznik ról, reset danych (tylko DEMO_MODE=1)                   │
                └───────────── SQLite (/data) albo Postgres (DATABASE_URL) ─── Django admin = panel kadr i konfiguracji ┘
```

| Warstwa | Wybór | Licencja | Dlaczego |
|---|---|---|---|
| język / framework | Python 3.13, Django 5.2 LTS | PSF, BSD-3 | wbudowany panel admina, migracje, auth, długie wsparcie (LTS do 04.2028) |
| interakcje | HTMX 2 (plik statyczny w repo) | 0BSD | dynamika bez SPA i bez łańcucha npm: mniej zależności do audytu |
| CSS | własne tokeny, CSS bez preprocesora | – | zero kroku budowania frontu |
| PDF | WeasyPrint | BSD-3 | HTML → PDF zgodny ze wzorem |
| święta | `holidays` | MIT | polskie święta + testy na przykładach KPRM |
| daty | `python-dateutil` (`relativedelta`) | Apache-2.0 / BSD | dodawanie miesięcy z „ostatnim dniem miesiąca” |
| YAML / walidacja | PyYAML + `pydantic` | MIT | typowany schemat pakietu, czytelne błędy |
| podpis pakietów | `cryptography` (Ed25519) | Apache-2.0 / BSD | podpis pakietów przepisów |
| hasła | `argon2-cffi` | MIT | – |
| serwer | gunicorn + WhiteNoise | MIT | jeden proces, statyki bez nginx |
| baza | SQLite / Postgres (`psycopg` LGPL, tylko jako biblioteka, dynamicznie) | public domain / PostgreSQL | **do sprawdzenia:** psycopg 3 jest na LGPL-3.0; dopuszczalne przy linkowaniu dynamicznym, ale wpisujemy na listę licencji jawnie |
| SSO (P2) | `django-auth-ldap` (BSD-2) / OIDC (`mozilla-django-oidc` to MPL-2.0: unikamy, rozważamy `authlib` BSD) | – | – |
| testy | pytest, pytest-django, Playwright (smoke demo) | MIT / Apache | – |
| narzędzia | uv, ruff, pip-audit, CycloneDX | MIT/Apache | skan zależności, SBOM |

**Zasady techniczne:** jedna komenda startu; migracje przy starcie; konfiguracja wyłącznie przez zmienne środowiskowe (`DATABASE_URL`, `AI_PROVIDER`, `OLLAMA_URL`, `SMTP_URL`, `DEMO_MODE`, `RULES_TRUSTED_KEYS`); obraz bez tagu `latest` w dokumentacji (tylko semver); healthcheck `/healthz`; logi na stdout w JSON.

---

## 14. AI w produkcie (opcjonalne, za jedną warstwą)

| Tryb | Kiedy | Co wychodzi poza urząd |
|---|---|---|
| `off` (domyślny) | mały urząd, brak GPU | nic; wszystkie ekrany działają, szkice zastępuje zestawienie notatek |
| `ollama` (lokalnie) | urząd ma GPU albo serwer centralny w sieci rządowej | nic |
| `openai-compatible` | urząd świadomie wybiera zewnętrzne API | wyłącznie tekst po pseudonimizacji; mapa tokenów zostaje lokalnie |

**Funkcje AI (wszystkie fioletowe, wszystkie z cytatami):**
1. szkic uzasadnienia i wniosków do IPRZ z notatek (każde zdanie → notatka; zdania bez źródła odrzucane walidatorem),
2. przeformułowanie notatki na język opisowy, bez ocen osobowości (podpowiedź „opisz zachowanie, nie cechę”),
3. rozmowa z HR partnerem na zanonimizowanych sygnałach, działania tylko z katalogu.

**Czego AI nie robi nigdy:** nie liczy terminów ani punktów, nie wybiera poziomu oceny, nie zatwierdza niczego, nie widzi danych innych niż przekazane jawnie, nie dostaje przyczyn nieobecności.

**Model:**
- docelowo **Bielik 11B v2.x Instruct** (polski model otwarty, Apache-2.0) w Q4_K_M przez Ollamę: dobry polski język urzędowy, licencja bez opłat; alternatywa **Qwen3 8B** (Apache-2.0), gdy GPU ma 10 GB.
- parametry: kontekst 8k, temperatura 0,2, odpowiedź w JSON (zdania + identyfikatory notatek), limit czasu 25 s, a po jego przekroczeniu komunikat „AI niedostępne, kontynuuj bez szkicu” (nigdy nie udajemy wyniku).
- **Ewaluacja na zbiorze syntetycznym** (20 zestawów notatek): odsetek zdań z poprawnym cytatem, odsetek zdań bez źródła po walidatorze (cel: 0), czas odpowiedzi. Wynik w README.

---

## 15. Infrastruktura demo (konkretnie, stan na sob ~13:00)

Źródła: `../SERVERS.md`, `../solvro-infra-hackathon.md`.

| Element | Gdzie | Parametry | Uwagi |
|---|---|---|---|
| aplikacja demo | **`solvro-stacja-web`** (10.21.36.12, 16 vCPU Ryzen 9 7950X, ok. 11 GiB RAM wolne, 163 GB dysku) przez **Coolify 4.7.6** (`devops.solvro.pl`), projekt **Hackatony**, nowe środowisko **`okres`** | Dockerfile z repo; limit 1 vCPU / 768 MB (zużycie spodziewane < 300 MB); wolumen `/data` na SQLite; healthcheck `/healthz` | domena **`okres.b.solvro.pl`**, Let's Encrypt automatycznie; build na `solvro-build-server` (16 równoległych buildów), żeby nie obciążać produkcji |
| baza | SQLite w wolumenie | – | celowo: pokazujemy wariant „mały urząd”. Postgres pokazujemy lokalnie w `docker compose` (profil `postgres`) |
| AI | **`solvro-stacja`** (10.21.37.1), Ollama na GPU (RTX 3060 12 GB albo 3080 10 GB: niepotwierdzone) | 3060: `bielik-11b-v2.x-instruct:Q4_K_M` (~6,7 GB) + KV 8k (~1,5 GB); 3080: Qwen3 8B Q4_K_M (~5 GB); `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=24h` | **teraz nieosiągalna** (ping, :22 i :11434 timeout; `ollama.b.solvro.pl` → 502). Aplikacja woła `http://10.21.37.1:11434` po stronie serwera; Ollamy nie wystawiamy jury |
| współdzielenie | ta sama Ollama obsługuje też projekt Azymut (zadanie MC) | `OLLAMA_MAX_LOADED_MODELS=2` | wspólny jest tylko host i model; **kod osobny** (AGENTS.md) |
| plan B dla AI | Ollama na laptopie zespołu (Apple Silicon) + tunel WireGuard tylko na czas demo | Qwen3 8B albo Bielik 4.5B | jeśli stacja nie wróci do ~20:00 |
| plan C | `AI_PROVIDER=off` | – | demo procesu w całości bez AI; to i tak nasz główny przekaz |

**Tryb demonstracyjny (`DEMO_MODE=1`):**
- pasek „Tryb demonstracyjny” zawsze widoczny, z bieżącą datą symulacji,
- **przełącznik ról** („Zaloguj jako: oceniający / oceniany / kadry / dyrektor generalny”) bez haseł, żeby jury mogło samo przeklikać proces z linku,
- **zegar symulacji** (+1 dzień, +1 miesiąc, „skocz do następnego terminu”), który uruchamia scheduler dla przesuniętej daty,
- przycisk „przywróć dane demonstracyjne” (deterministyczny seed),
- dane: fikcyjny „Urząd Wojewódzki w Okresowie”, ok. 12 osób w różnych etapach (w tym jedna osoba ze sprzeciwem, jedna przed obligatoryjnym stopniem, jedna po długiej nieobecności z przykładu KPRM).

---

## 16. Zakres MVP

**P0, musi działać na demo (do niedz. ~6:00):**
- pakiet `sc-2016-470` (cykl, arkusze B i C, punktacja, schemat pól B i C) z testami z „liczenia terminów”,
- silnik sprawy: kryteria → potwierdzenie → dziennik → rozmowa oceniająca → ocena → zapoznanie / fikcja zapoznania → licznik sprzeciwu,
- strażnik formalny (blokady twarde i miękkie) i oś sprawy z wyjaśnieniem terminów,
- długotrwała nieobecność (ciągłość, przesunięcie, powiadomienia), ponowna ocena po negatywnej, obligatoryjny stopień,
- scheduler + zegar symulacji + przełącznik ról + seed,
- wydruk PDF arkusza B i C zgodny ze wzorem,
- panel kadr (lista pracowników, import CSV, nieobecności), wgranie pakietu z testami,
- HR partner: 3 sygnały (zmiany zakresu, brak pozytywnej notatki, check-in) + katalog + prawo wglądu,
- pakiet `projekt-nowelizacji-demo` i przełączenie na żywo,
- strona `/pokrycie`,
- wdrożenie na `okres.b.solvro.pl`.

**P1 (niedz. 6:00–10:00, w kolejności):**
1. sprzeciw: zmiana oceny i ponowne sporządzenie (UC-16, UC-17),
2. zmiana terminu przez oceniającego i na wniosek ocenianego + zawiadomienie § 8 (UC-12, UC-13),
3. arkusz A, wniosek fakultatywny o stopień (część III),
4. szkic uzasadnienia i IPRZ z AI z cytatami,
5. panel dyrektora generalnego + eksport do sprawozdania,
6. zmiana stanowiska, zmiana oceniającego (UC-19, UC-26),
7. kreator pierwszego uruchomienia, druk z QR, `.ics`, paczka do EZD,
8. podpis Ed25519 pakietów, diff pakietów.

**P2 (opisane w prezentacji, niezbudowane):** SSO (LDAP/OIDC), integracja z API EZD RP, podpis kwalifikowany, wariant centralny KPRM, czat HR partnera.

## 17. Poza zakresem

Prawdziwe integracje z EZD i systemami kadrowymi, e-podpis, **pierwsza ocena w służbie cywilnej** (inny proces, inne rozporządzenie; nie jest wymagana w zadaniu, a przy okazji to obszar projektu Azymut, z którym nie chcemy się pokrywać), wskaźniki behawioralne do kryteriów (jak wyżej), aplikacja mobilna, rzeczywista wysyłka e-maili (log + `.ics`).

**Rozdzielenie od Azymutu (zadanie MC):** Azymut to ekran wskaźników zachowań, analiza OSP i RAG z paragrafami. OKRES to silnik procesu, terminów i przepisów jako danych oraz HR partner. Inne zadanie, inny kod, inna architektura (Django vs Next.js).

---

## 18. Scenariusz demo (≈ 3 min, pełen proces)

Persony: **Anna Nowak** (naczelniczka wydziału, oceniająca), **Piotr Zieliński** (główny specjalista, oceniany, urzędnik mianowany), **Ewa Kowalczyk** (kadry), **dyrektor generalny**. Wszystko fikcyjne.

| Czas | Kto | Co pokazujemy | Kryterium |
|---|---|---|---|
| 0:00–0:15 | – | terminal: `docker run …` → kreator → import CSV 12 osób → system liczy terminy dla wszystkich | wdrożenie |
| 0:15–0:45 | kadry → oceniająca → oceniany | scheduler przypomina o kryteriach (30 dni, § 7); Anna wybiera arkusz C (podpowiedź z danych stanowiska), dobiera 2 kryteria dodatkowe z opisami z Zał. 1; checklista § 5; Piotr potwierdza → **pola się blokują** (kłódka, „tryb korekty administratora”) | zgodność |
| 0:45–1:10 | zegar +10 mies. | dziennik obserwacji; kadry importują L4 05–16.10.2026 + urlop 19.10–06.11.2026 (przykład KPRM) → „nieobecność ciągła 33 dni” → termin przesunięty, rachunek krok po kroku, powiadomienia | zgodność, kompletność |
| 1:10–1:35 | oceniająca, ekran „Zespół” | HR partner (morski kolor): „3 zmiany zakresu w 6 tyg. + spadek check-inów” z wyjaśnieniem → działanie z katalogu; „ostatnia pozytywna notatka 4 mies. temu” → podpowiedź docenienia; podgląd „co widzi pracownik” | HR partner, oryginalność |
| 1:35–2:15 | zegar → termin oceny | przygotowanie rozmowy (flaga: kryterium bez notatek, efekt świeżości); ocena; próba zatwierdzenia z cząstkową 1 bez uzasadnienia → **blokada § 11 ust. 3**; uzupełnienie; (opcjonalnie) fioletowy szkic IPRZ z cytatami notatek; **PDF obok wzoru z rozporządzenia** | zgodność |
| 2:15–2:35 | oceniany → scheduler | zapoznanie, licznik sprzeciwu 7 dni; drugi pracownik: scheduler wykrywa **obligatoryjny stopień** (2 kolejne oceny na najwyższych poziomach) i przypomina DG o 30 dniach | kompletność |
| 2:35–3:00 | kadry | **wgranie pakietu „projekt nowelizacji (demo)”**: 27/27 testów pakietu zaliczone, diff „cykl 24 → 12 mies.”, nowe sprawy liczą się po nowemu, rozpoczęte zostają przy dotychczasowych przepisach. Na koniec `/pokrycie`: „25/27 przypadków użycia KPRM” | wdrożenie, oryginalność |

**Plan awaryjny:** demo działa offline i bez AI (lokalny `docker compose` na laptopie, seed deterministyczny); film z przebiegu nagrany w niedzielę rano; zrzuty ekranu w prezentacji.

## 19. Prezentacja (PDF, maks. 15 slajdów)

1. OKRES: tytuł, hasło, zespół.
2. Problem: papier, terminy, błędy formalne, nowelizacja w toku (liczby z opisu zadania).
3. Rozwiązanie w jednym zdaniu + 4 filary.
4. Proces end-to-end: oś sprawy z torami BPMN (oceniający, oceniany, kadry, DG, scheduler).
5. **Macierz pokrycia przypadków użycia** (zrzut `/pokrycie`).
6. Zgodność formalna: strażnik, blokady z §, terminy z rachunkiem, wydruk obok wzoru.
7. Notatki i rozmowy: dziennik, flagi jakości obserwacji, biblioteka trudnych rozmów.
8. **Wirtualny HR partner**: sygnały, wyjaśnienia, kultura doceniania, prawo wglądu.
9. AI: opcjonalne, lokalne, z cytatami; czego nigdy nie robi; wyniki ewaluacji.
10. **Przepisy jako dane**: pakiet, testy, podpis, przełączenie na nowelizację.
11. **Wdrożenie w każdym z 1743 urzędów**: trzy profile, wymagania sprzętowe, 15 minut, wariant centralny.
12. Aktualizacje, bezpieczeństwo, RODO, WCAG, licencje (SBOM).
13. Integracje: poczta, EZD RP, CSV/API, sprawozdawczość.
14. Plan rozwoju z KPRM: pilotaż w 3 urzędach różnej wielkości → pakiet po nowelizacji → wariant centralny.
15. Ujawnienia: użycie AI w wytwarzaniu i w produkcie, co jest zamockowane, linki (demo, repo, film).

---

## 20. Harmonogram zespołu (sob → niedz)

| Do kiedy | Cel |
|---|---|
| sob 16:00 | szkielet Django, modele, loader pakietu, testy terminów z „liczenia terminów” na zielono |
| sob 18:00 | ścieżka główna arkusza C bez PDF; seed; zegar; przełącznik ról; pierwszy deploy na `okres.b.solvro.pl` |
| **sob 20:00** | **draft na HackTribe** (tytuł, opis, problem, link do demo) |
| sob 20:00–22:00 | konsultacja reguł z mentorami KPRM (lista pytań z sekcji 21) |
| niedz 02:00 | nieobecności, stopień obligatoryjny, strażnik, PDF B/C, HR partner (3 sygnały) |
| niedz 06:00 | pakiet nowelizacji + przełączenie, `/pokrycie`, panel kadr; **zamrożenie P0** |
| niedz 09:00 | P1 według kolejności, README, film, slajdy |
| **niedz 10:30** | **zgłoszenie finalne** (bufor 30 min przed 11:00) |

## 21. Otwarte pytania do mentorów KPRM (sobota wieczór)

1. Czy potwierdzenie w systemie (zalogowany użytkownik + znacznik czasu + audyt) można traktować jak „podpis” z § 6 ust. 2 i § 12, czy potrzebny jest wydruk z podpisami lub podpis elektroniczny?
2. Fikcja zapoznania: jaki dokument ją potwierdza (notatka służbowa, data doręczenia, świadek) i od kiedy biegnie 7 dni na sprzeciw?
3. Kilka osobnych nieobecności > 1 mies. w jednym cyklu: czy przedłużenia się sumują?
4. Czy przy przedłużeniu o czas nieobecności liczymy dni kalendarzowe nieobecności i czy przesunięcie na dzień roboczy stosujemy po dodaniu?
5. W schemacie pól arkusza B pole „Uzasadnienie przyznanej oceny” występuje dwukrotnie z różnymi regułami. Która wersja obowiązuje?
6. Czy znane są już kierunki nowelizacji (cykl 12 mies., art. 81a, oceny wyższych stanowisk) na tyle, żeby pakiet demonstracyjny je odwzorował?
7. Jaki format danych do sprawozdania dyrektora generalnego byłby najbardziej przydatny (pytanie do Kamila Kazimierczuka)?
8. Czy dobrowolny check-in nastroju jest akceptowalny w urzędach, czy lepiej oprzeć HR partnera tylko na danych procesowych?
9. Czy przekazanie notatek poprzedniego oceniającego nowemu (§ 9 ust. 3) jest dopuszczalne, a jeśli tak, w jakim zakresie?

## 22. Ryzyka

| Ryzyko | Mitigacja |
|---|---|
| błąd formalny zauważony przez ekspertów DSC | testy na przykładach KPRM, konsultacja reguł w sobotę wieczorem, strażnik formalny z § przy każdym komunikacie, demo przećwiczone na konkretnych datach |
| zakres podprocesów za duży na 24 h | P0 = ścieżka główna + nieobecność + stopień obligatoryjny + przełączenie pakietu; reszta to przejścia w tym samym silniku; P1 w ustalonej kolejności |
| stacja z GPU nie wróci | plan B (laptop + tunel), plan C (AI off); AI nie jest w ścieżce krytycznej demo |
| HR partner odebrany jako inwigilacja | prawo wglądu, brak danych o zdrowiu, brak automatycznych decyzji, sygnały nie trafiają do oceny ani kadr, slajd RODO |
| „przepisy jako dane” odebrane jako przerost formy | pokazać to na żywo na jednym przykładzie (12 mies.) w 25 sekund, z testami pakietu |
| zespół zna lepiej Next.js niż Django | Django wybrane świadomie (panel admina, jeden proces, łatwe utrzymanie w urzędzie, brak łańcucha npm); szablony + HTMX są proste |
| produkcja Solvro na tym samym hoście | limit zasobów w Coolify, build na build serverze, SQLite bez dodatkowych usług |
| treść projektu nowelizacji mogła się zmienić | pakiet opisany jako hipotetyczny, oparty na publicznych omówieniach UDER 102 |

## 23. Źródła

- Materiały KPRM: `materials/` (zadanie, akty prawne, przypadki użycia, schemat procesu, schematy pól, liczenie terminów).
- Jury i mentorzy: `../hacknation-mentorzy.md`, sekcja 14.
- Serwery: `../SERVERS.md`, `../solvro-infra-hackathon.md`.
- Nowelizacja (do weryfikacji): [gov.pl: projekt ustawy o zmianie ustawy o służbie cywilnej](https://www.gov.pl/web/premier/projekt-ustawy-o-zmianie-ustawy-o-sluzbie-cywilnej), [Serwis SC: nowelizacja w wykazie prac](https://www.gov.pl/web/sluzbacywilna/nowelizacja-ustawy-o-sluzbie-cywilnej-wpisana-do-wykazu-prac-legislacyjnych-i-programowych-rady-ministrow), [DSK Kancelaria: zmiany w służbie cywilnej](https://dsk-kancelaria.pl/blog/kobieta-50-zmiany-w-sluzbie-cywilnej/), [FSP: uwagi do nowelizacji](https://sprawnepanstwo.pl/index.php/2026/05/21/nowelizacja-ustawy-o-sluzbie-cywilnej-uwagi-fsp/).
