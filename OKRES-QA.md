# OKRES – raport QA wdrożenia (https://okres.b.solvro.pl)

Data testu: 21.11.2026 (zegar demo bez przesunięcia). Konta: `oceniajaca`, `oceniany`, `piotr`, `kadry`, `dyrektor` (hasło `demo`).
Metoda: sesje HTTP per rola (crawl wszystkich linków + żądania HTMX jak z przeglądarki), sondy walidacji wyłącznie z **niepoprawnymi** danymi (żeby nie zmieniać wspólnego demo), odczyt kodu tam, gdzie poprawny zapis zmieniłby stan demo (zatwierdzenie kryteriów, sporządzenie oceny, zapoznanie, sprzeciw, fikcja, scheduler). Nic nie zostało zapisane w bazie.

Wynik ogólny: żaden link w żadnej roli nie zwraca 4xx/5xx; kontrola dostępu trzyma (oceniany dostaje 404 na cudze sprawy, 403 na statystyki, panel kadr przekierowuje do logowania); prywatne notatki oceniającego nie przeciekają do przygotowania rozmowy u ocenianego. Problemy to głównie spójność danych demo, walidacja dat i teksty.

Skala: **Wysoka** = jury może to zauważyć w demo albo podważa zgodność z prawem; **Średnia** = błąd logiki/UX w ścieżce; **Niska** = tekst, kosmetyka.

---

## Wysoka

### H1. Sprawy Jana i Piotra (główne konta demo) są „po terminie” na etapie kryteriów od 1,5–2 lat
- **Rola:** oceniany, piotr, oceniajaca, kadry. **URL:** `/oceny/`, `/oceny/1/`, `/oceny/2/`
- **Kroki:** zaloguj się jako `oceniany` lub `piotr` → Moje sprawy.
- **Oczekiwane:** demo pokazuje realistyczny proces: kryteria ustalone w okresie, dziś bieżący etap.
- **Faktycznie:** Jan: termin ustalenia kryteriów 15.04.2025 „Po terminie”; Piotr: 02.01.2025 „Po terminie”, a termin oceny Piotra to 02.12.2026 (za 11 dni), mimo że kryteriów nigdy nie wyznaczono. Cały okres oceny minął bez części I, co oznacza naruszenie § 7 pkt 1 w danych pokazowych. Tak samo Anna (arkusz B, 02.07.2025). Statystyki: „Po terminie 4”.
- **Poprawka:** w `seed_demo` przesunąć początki okresów Jana, Piotra i Anny tak, żeby termin kryteriów wypadał za kilka dni (np. początek okresu = dziś − 20 dni), albo ustawić te sprawy jako mające zatwierdzone kryteria. Termin 30 dni dla Piotra (02.12.2026) i nieobecność Jana (rachunek terminu) można zachować przez przypisanie im innych dat okresu.
- ✅ naprawione: seed odtwarza stan na 21.11.2026 bez spraw po terminie (statystyki: „po_terminie 0”). Jan ma uzgodnioną część I z 24.03.2025 (termin oceny 19.04.2027 z nieobecnością bez zmian), Anna z 10.06.2025. Piotr ma ocenę zakończoną 04.11.2026 i nowy okres z kryteriami do 04.12.2026, więc na nim pokazujemy część I bez przestawiania zegara (`DEMO.md`). Testy obiegu startują od etapu kryteriów przez `oceny/pomoc_testow.py`; spójność seeda sprawdza `SpojnoscDanychDemoTest`.

### H2. Osiągnięcie i wpis w dzienniku Jana leżą w środku jego nieobecności
- **Rola:** oceniany, oceniajaca. **URL:** `/partner/ja/`, `/partner/zespol/`, `/oceny/1/`
- **Faktycznie:** nieobecność usprawiedliwiona 05.10–06.11.2026, a „Przeszkoliłem dwie nowe osoby…” ma datę 01.11.2026, a „Przejęcie rejestru skarg” w dzienniku zadań 27.10.2026. Sygnał „Powrót po 33 dniach nieobecności” stoi obok aktywności z tego samego okresu.
- **Poprawka:** przenieść te dwa wpisy w seedzie na daty po 06.11.2026 (np. 12.11 i 16.11).
- ✅ naprawione: „Przejęcie rejestru skarg” w dzienniku ma datę 16.11.2026 (po powrocie). Osiągnięcie ma datę 02.10.2026, ostatni dzień przed nieobecnością, a nie 12.11, bo sygnał „czeka na docenienie” wymaga 14 dni bez reakcji. Treść („zastępstwa działają bez przerw”) pasuje do nieobecności.

### H3. Obserwacje i osiągnięcia: brak walidacji daty
✅ naprawione: nieczytelna data daje błąd „Nie rozpoznano daty…” zamiast dzisiejszej (`oceny/daty.py`, też dziennik HR partnera), zakres okresu oceny z czytelnym komunikatem, `min`/`max` i domyślnie dziś w polu daty; testy `oceny/test_obserwacje.py`, `partner/tests.py`.
- **Rola:** oceniajaca, oceniany (każdy, kto dodaje obserwację). **URL:** `POST /oceny/<pk>/obserwacje/` (formularz „Dodaj obserwację” / „Zgłoś osiągnięcie”)
- **Kroki:** wpisz datę 01.01.1999 albo datę z przyszłości (np. 2030) i treść → Zapisz.
- **Oczekiwane:** odrzucenie daty spoza okresu oceny (od `poczatek_okresu` do dziś), jak przy dacie rozmowy w części I.
- **Faktycznie:** `Ocena.dodaj_obserwacje` (`oceny/models.py:505`) nie sprawdza zakresu; niepoprawny format daty jest po cichu zamieniany na dzisiejszą (`views.dodaj_obserwacje`). Notatka sprzed okresu trafia do przygotowania rozmowy oceniającej i do podpowiedzi oceny.
- **Poprawka:** w `dodaj_obserwacje` rzucić `ValidationError({"data": ...})` dla `data > dzis` i `data < poczatek_okresu`; przy błędnym formacie zwracać błąd zamiast podstawiać dziś. Dodać `min`/`max` w `<input type="date">`.

### H4. Dyrektor generalny ocenia kierownika urzędu (arkusz A)
- **Rola:** dyrektor, kadry. **URL:** `/oceny/4/`, `/admin/oceny/pracownik/`
- **Faktycznie:** Tomasz Kaczmarek „Kierownik urzędu” (Kierownictwo, arkusz A) ma przełożonego i oceniającego Dorotę Dyrektorską (DG); widnieje też w jej zespole w HR partnerze. W urzędzie to DG podlega kierownikowi urzędu, a kierownika urzędu ocenia osoba spoza urzędu (organ nadrzędny). Ekspert z KPRM/DSC zauważy to natychmiast.
- **Poprawka:** w seedzie oceniającym kierownika urzędu powinna być osoba zewnętrzna (np. konto „Minister / organ nadrzędny”, bez logowania demo) albo zmienić stanowisko Tomasza na takie, któremu odpowiada arkusz B. Pokazanie arkusza A można zostawić jako sam wydruk.
- ✅ naprawione: Tomasza (arkusz A) ocenia bezpośrednia przełożona spoza urzędu, Ewa Zawadzka, „Prezes urzędu nadrzędnego (oceniająca spoza urzędu)”, bez hasła i bez logowania w pokazie (art. 81 ust. 1). Tomasz nie występuje już w zespole DG w HR partnerze, a wydruk arkusza A podaje oceniającą spoza urzędu.

### H5. Nowy okres oceny zakładany, zanim poprzednia ocena jest ostateczna
- **Rola:** kadry, dyrektor, oceniajaca. **URL:** `/oceny/11/` (Joanna Kurek), `/oceny/9/` (Natalia Wróbel)
- **Faktycznie:** Joanna ma sprzeciw w rozpatrzeniu (sprawa 10), a jednocześnie nową sprawę „Kryteria” (11) z okresem liczonym od 18.11.2026. Natalia ma ocenę czekającą na zapoznanie (8) i już nową sprawę (9). Na liście oceniającej Natalia pojawia się dwa razy, z „Termin —” przy jednej z pozycji. Jeśli DG wybierze „Uwzględniam i kieruję do ponownej oceny”, okres w sprawie 11 będzie błędny.
- **Poprawka:** scheduler zakłada kolejną sprawę dopiero po zakończeniu poprzedniej (zapoznanie + 7 dni bez sprzeciwu albo rozstrzygnięcie sprzeciwu). Alternatywa: oznaczać ją jako „wstępna” i przeliczać przy ponownej ocenie. Na liście grupować sprawy jednej osoby.
- ✅ naprawione: `scheduler.zaloz_kolejna` zakłada kolejny okres od razu tylko po ocenie negatywnej (kryteria w 7 dni, § 7 pkt 2), a w pozostałych przypadkach po ocenie ostatecznej. Seed nie zakłada już spraw Natalii i Joanny, więc Natalia jest raz na liście. Kolejne sprawy mają tylko oceny zakończone (Piotr, Rafał). Grupowanie listy pozostaje w zakresie UI.

---

## Średnia

### M1. Zmiana oceniającego: lista dopuszcza każdego pracownika
✅ naprawione: lista i walidacja w modelu (`Ocena.kandydaci_na_oceniajacego`) dopuszczają tylko osoby na stanowiskach kierowniczych (A/B), bez ocenianego, obecnego oceniającego i podwładnych ocenianego; test `oceny/test_kadrowe.py`.
- **Rola:** kadry. **URL:** `/oceny/11/` → „Zmiana oceniającego (§ 9 ust. 3)”
- **Faktycznie:** lista „Nowy oceniający” zawiera m.in. Jana, Piotra, Rafała i Karolinę (specjalistów, w tym współpracowników z tego samego wydziału ocenianej) oraz kadrową.
- **Poprawka:** ograniczyć listę do bezpośrednich przełożonych lub osób na stanowiskach kierowniczych (rodzaj stanowiska ≠ „pozostałe”), wykluczyć ocenianego, a wyjątki dopuszczać z uzasadnieniem.

### M2. Część I można zatwierdzić bez miejscowości
✅ naprawione: puste pole „Miejscowość” daje błąd „Podaj miejscowość rozmowy…” (pole `required`), wywołanie bez formularza bierze miejsce pracy oceniającego lub siedzibę urzędu; testy `oceny/test_obieg.py`.
- **Rola:** oceniajaca. **URL:** `POST /oceny/<pk>/kryteria/zatwierdz/`
- **Faktycznie:** `zatwierdz_kryteria` wymaga daty rozmowy, ale nie miejscowości, a wzór arkusza ma pole „miejscowość, data” przy potwierdzeniu.
- **Poprawka:** wymagać `miejscowosc` albo domyślnie podstawiać miejscowość urzędu (`Urzad.miejscowosc`).

### M3. Formularze działają tylko z JavaScriptem (HTMX)
✅ naprawione: wszystkie formularze HTMX mają `method="post"`, `action` i `{% csrf_token %}` (też „Potwierdź kryteria”), a `oceny.bez_js.FragmentBezJsMiddleware` osadza odpowiedź bez HTMX w pełnej stronie z wynikiem lub błędem i odnośnikiem powrotu; test `oceny/test_bez_js.py`.
- **Rola:** wszystkie. **URL:** każda sprawa (`/oceny/<pk>/`), `/partner/zespol/`
- **Faktycznie:** formularze kryteriów, obserwacji, terminu i HR partnera mają tylko `hx-post`, bez `action`/`method`. Gdy JS się nie załaduje (polityka urzędu, wolne łącze, czytnik ekranu w trybie przeglądania), wysłanie formularza robi GET na bieżący adres i dane przepadają bez komunikatu.
- **Poprawka:** dodać `method="post" action="{{ to samo co hx-post }}"`, a w widokach przy braku `HX-Request` robić redirect na sprawę (progressive enhancement).

### M4. Uczestnicy bez sprawy: kadrowa Krystyna Kadrowa
- **Rola:** kadry, dyrektor. **URL:** `/admin/oceny/pracownik/`, `/oceny/statystyki/`
- **Faktycznie:** 13 pracowników, 14 spraw, ale Krystyna (arkusz C, przełożona: DG) nie ma żadnej sprawy. Nic tego nie sygnalizuje: ani statystyki, ani panel kadr nie mają pozycji „pracownicy bez otwartej oceny”. DG słusznie nie ma sprawy, ale też tego nie wyjaśniono.
- **Poprawka:** dodać sprawę Krystyny w seedzie, a w statystykach kafelek „Pracownicy bez bieżącej sprawy” (z wyłączeniem DG i z adnotacją dlaczego).
- ✅ naprawione (panel kadr): na liście pracowników kolumna „Bieżąca sprawa” (nr i etap albo pogrubione „brak bieżącej sprawy”) i filtr „bieżąca sprawa: brak / jest”. Flaga obejmuje wszystkich, także DG, bez adnotacji prawnej. Sprawa Krystyny w seedzie i kafelek w statystykach należą do zakresu danych i statystyk, nie do tej poprawki.
- ✅ naprawione (seed): Krystyna ma sprawę (okres od 01.09.2025, oceniająca DG, etap części II). Bez sprawy zostają DG i oceniająca spoza urzędu. Kafelka w statystykach nie dodano (zakres statystyk i UI).

### M5. Znaczniki czasu w panelu kadr przeczą datom w sprawie
✅ naprawione: lista w panelu pokazuje daty z arkusza (`data_potwierdzenia_kryteriow`, `data_sporzadzenia`), a techniczne znaczniki `*_at` są ukryte w formularzu sprawy (zostają w bazie i eksporcie); test `oceny/test_sprawy.py` (`PanelKadrDatyTest`).
- **Rola:** kadry. **URL:** `/admin/oceny/ocena/`
- **Faktycznie:** „Kryteria potwierdzone at” i „Sporzadzona at” = „21 listopada 2026 18:22” (moment seedowania) dla spraw, które w UI mają rozmowę 26.11.2024 i ocenę 05.10.2026 (Rafał, sprawa 12).
- **Poprawka:** w seedzie ustawiać `*_at` zgodnie z datami biznesowymi albo w panelu pokazywać `data_zatwierdzenia_kryteriow` / datę sporządzenia zamiast technicznych timestampów.

### M6. Teksty dla oceniającego wyświetlane ocenianemu
- **Rola:** oceniany, piotr. **URL:** `/oceny/1/`, `/oceny/1/przygotowanie/rozpoczynajaca/`
- **Faktycznie:** pracownik widzi „Brak obserwacji. Zapytaj w rozmowie o przykład…”, „Zapisz uzgodnione oczekiwania prostym językiem”, „Kryteria dodatkowe wybieraj pod faktyczne zadania” oraz w „Wersje przepisów” instrukcję dla kadr z `manage.py sprawdz_reguly`.
- **Poprawka:** warunkować podpowiedzi rolą; ocenianemu pokazać np. „Brak wpisów. Możesz zgłosić własny przykład.” i ukryć techniczną informację o pakietach.
- ✅ naprawione: podpowiedź pustej listy zależy od roli (oceniany: „Brak wpisów. Możesz zgłosić własny przykład.”, kadry/DG: „Brak wpisów.”); w przygotowaniu oceniany dostaje własne wskazówki (`wskazowki_ocenianego` w `rules/rozmowy.yaml`) bez stopki o pakiecie; zdanie o `manage.py sprawdz_reguly` i panelu kadr widzą tylko kadry.

### M7. Sygnał „czeka na docenienie” zadaje pytanie, na które już jest odpowiedź
- **Rola:** oceniajaca, oceniany. **URL:** `/partner/zespol/`, `/partner/ja/`
- **Faktycznie:** pytanie do rozmowy „Jaki był skutek tego działania…?”, a osiągnięcie ma już wpisany skutek („Zastępstwa w rejestrze działają bez przerw”). Pod sygnałem jest formularz „Dodaj docenienie”, a niżej drugi identyczny „Doceń bez sygnału”.
- **Poprawka:** gdy skutek jest wypełniony, użyć innego pytania (np. „Co z tego doświadczenia warto przenieść na zespół?”). W sygnale zostawić jeden formularz docenienia i ukryć drugi dla tej osoby.
- ✅ naprawione: przy wpisanym skutku sygnał pyta „Co z tego doświadczenia warto przenieść na cały zespół?” (`pytanie_gdy_skutek` w `rules/hr_partner.yaml`), skutek widać w źródłach i jest przenoszony do docenienia bez ponownego pytania; „Doceń bez sygnału” jest ukryte na karcie osoby, która ma sygnał docenienia. Test w `partner/tests.py`.

### M8. Nieprawidłowy rodzaj terminu daje 200 zamiast 404
✅ naprawione: nieznany `rodzaj` w `/termin/…/`, `/przygotowanie/…/` i `/kadrowe/…/` daje 404 przed sprawdzaniem uprawnień; testy `oceny/test_sprawy.py` (`NieznaneAdresyTest`).
- **Rola:** każda. **URL:** `/oceny/1/termin/xyz/`
- **Faktycznie:** zwraca wyjaśnienie terminu oceny (fallback), a nie błąd. `/oceny/1/przygotowanie/xyz/` zwraca natomiast 403 zamiast 404. Te przypadki brzegowe są niespójne.
- **Poprawka:** dla nieznanego `rodzaj` zwracać `Http404` w obu widokach.

---

## Niska

### L1. Tytuł „Moje sprawy” dla kadr i DG, którzy widzą wszystkie sprawy
- **Rola:** kadry. **URL:** `/oceny/` → lista 14 spraw cudzych. **Poprawka:** dla kadr nagłówek „Sprawy w urzędzie”.
- ✅ naprawione: tytuł listy, pozycja menu i link powrotu zależą od roli: kadry „Sprawy w urzędzie”, DG „Moje sprawy i decyzje” (widzi też sprzeciwy i wnioski do decyzji), pozostali „Moje sprawy”.

### L2. Pytania w przygotowaniu rozmowy tylko w rodzaju męskim
- **Rola:** dyrektor, oceniajaca. **URL:** `/oceny/5/przygotowanie/oceniajaca/` (Magdalena Czarnecka)
- „Z którego zadania jesteś najbardziej zadowolony”, „Jakie zadanie chciałbyś przejąć?”. **Poprawka:** formy neutralne („Które zadanie daje Ci najwięcej satysfakcji?”, „Jakie zadanie chcesz przejąć?”) w `rules/rozmowy.yaml`.
- ✅ naprawione: w `rules/rozmowy.yaml` „Które zadanie dało Ci najwięcej satysfakcji i dlaczego?” i „Jakie nowe zadanie chcesz przejąć?”; innych form tylko męskich w regułach i szablonach nie ma.

### L3. Podwójna interpunkcja w podpowiedzi
- **URL:** `/oceny/5/przygotowanie/oceniajaca/`: `zapytaj o przykład dla wskaźnika „…ryzyka.”.` **Poprawka:** usunąć kropkę po cudzysłowie albo końcową kropkę ze wskaźnika.
- ✅ naprawione: „Brak obserwacji. Zapytaj o przykład dla wskaźnika: „…ryzyka.”” bez kropki po cudzysłowie (`przygotowanie.html`).

### L4. Panel kadr: nieprzetłumaczone i bez polskich znaków nagłówki
- **URL:** `/admin/oceny/ocena/`, `/admin/oceny/pracownik/`. Kolumny „Oceniajacy”, „Kryteria potwierdzone at”, „Sporzadzona at”, „Imie nazwisko”, „Przelozony”; w kolumnach oceniany/oceniający pokazywane są loginy („karolina”, „finanse”) zamiast nazwisk; akcja „- Select an option -”; tytuł „Wybierz ocena do zmiany”. **Poprawka:** `verbose_name`/`short_description` w admin, `__str__` użytkownika = imię i nazwisko, `verbose_name_plural` z odmianą („ocenę”).
- ✅ naprawione: tylko w `oceny/admin.py` i `oceny/apps.py`, bez zmian modeli i migracji. Kolumny list mają polskie nagłówki, a oceniany, oceniający, przełożony i autor korekty są pokazani z imienia i nazwiska. Etykiety pól formularzy, także tylko do odczytu, mają polskie znaki (`Meta.labels`). Tytuły są w bierniku („Wybierz ocenę do zmiany”, „Zmień ocenę”, „Wybierz pracownika do zmiany”). Pusta opcja list to „— wybierz —” (Django 6.1 nie ma tłumaczenia „Select an option”). `User.__str__` zwraca imię i nazwisko, więc nagłówek sprawy brzmi „Ocena 1 · arkusz C · Jan Borkowski”. Test: `oceny/test_panel_kadr.py`.

### L5. Zbędne zdanie na stronie HR partnera
- **URL:** `/partner/zespol/`: „Zapisy są dostępne w HR partnerze.”, czyli na tej samej stronie. **Poprawka:** usunąć albo napisać, kto widzi zapisy.
- ✅ naprawione: zamiast tego „Pracownik widzi te same fakty, uzgodnienia i docenienia w zakładce „Mój dobrostan i rozwój”. Sygnały nie trafiają do oceny okresowej ani do raportów kadr.”

### L6. Zaproszenie do kalendarza po odbytej rozmowie
✅ naprawione: zaproszenie na rozmowę rozpoczynającą znika po zatwierdzeniu części I (na oceniającą po sporządzeniu), pole daty ma `min` = dziś, a `zaproszenie.ics` odrzuca datę z przeszłości i odbytą rozmowę; test `oceny/test_sprawy.py` (`ZaproszenieKalendarzTest`).
- **URL:** `/oceny/6/` (Alicja Szulc: rozmowa 17.11.2026 już potwierdzona), wciąż widać „Zaproszenie do kalendarza”. **Poprawka:** ukrywać po zatwierdzeniu części I.

### L7. Strona 403 bez szablonu
✅ naprawione: `handler403` (`oceny.views.brak_uprawnien`) renderuje `templates/403.html` z komunikatem z `PermissionDenied` i powrotem do listy; HTMX dostaje sam tekst, który `okres.js` pokazuje jako komunikat (`htmx:responseError`); testy `oceny/test_sprawy.py` (`BrakUprawnienTest`).
- **URL:** np. `POST /oceny/1/kryteria/zatwierdz/` jako oceniany zwraca gołe „403 Forbidden”, a w HTMX nic się nie wyświetla. **Poprawka:** szablon `403.html` z komunikatem z `PermissionDenied` i obsługa `htmx:responseError` (toast).

### L8. Dwie listy okresów nieobecności i jeden sygnał
- **URL:** `/partner/ja/` (Jan): dane źródłowe pokazują 05.10–16.10 i 19.10–06.11, a sygnał „33 dni ciągłej nieobecności”. Poprawne (weekend łączy okresy), ale niewyjaśnione. **Poprawka:** dopisać „(okresy połączone, przerwa to dni wolne)”.
- ⚠️ nie naprawione w danych: dane są poprawne (przykład KPRM), a brakuje tylko wyjaśnienia w szablonie HR partnera, czyli w zakresie UI, nie seeda.

### L9. Wnioski do IPRZ są kopią celów z części I
- **URL:** `/oceny/8/`, `/oceny/10/`, `/oceny/12/`: „Wnioski dotyczące IPRZ” są dosłownie tym samym tekstem co „Oczekiwania i cele”. Natalia i Rafał mają same „7” przy zerze obserwacji. **Poprawka:** zróżnicować dane seedu (wnioski jako kolejny krok rozwoju, 1–2 obserwacje na kryterium).
- ✅ naprawione: każda sporządzona ocena w seedzie ma wnioski do IPRZ inne niż cele (kolejny krok rozwoju), dwie obserwacje oceniającego z okresu i zróżnicowane cząstkowe (Natalia 7,80, Rafał 7,00, Piotr 6,60, Joanna 6,20).

---

## Nie przetestowane na żywo (celowo)
Zatwierdzenie kryteriów (pozytywne), potwierdzenie przez ocenianego, sporządzenie oceny, zapoznanie, fikcja zapoznania, rozstrzygnięcie sprzeciwu, scheduler, zegar demo i korekta administratora zmieniają współdzielony stan demo. Zostały sprawdzone tylko kodem i walidacją negatywną (duplikat kryterium daje komunikat „Kryteria dodatkowe nie mogą się powtarzać.”, pusta obserwacja daje „Opisz zaobserwowane działanie.”). Zalecany przebieg pełnej ścieżki na lokalnej kopii (`docker compose up`) przed pitchem.

## Sprawdzone bez uwag
- Eksport „Paczka do akt / EZD” (`/oceny/<pk>/eksport.zip`): `arkusz.html`, `dane.json`, `CZYTAJ.txt`, nazwa `ocena-<pk>.zip`. Oceniany nie pobierze cudzej paczki (404).
- Wydruk arkusza A/B/C i kopii części I (`/wydruk/`, `?czesc=I`) renderuje się dla wszystkich 14 spraw.
- Limit 3 kryteriów dodatkowych i brak powtórzeń są egzekwowane na serwerze (`full_clean` modelu), nie tylko w UI.
- Punktacja (skala 1/3/5/7/9, średnia 6,20 = „powyżej oczekiwań”, cząstkowa 3 nie blokuje oceny pozytywnej) zgodna z `rules/2016-04-04.yaml`.
- Rachunek terminów (np. Jan: +24 mies., +33 dni nieobecności, przesunięcie z niedzieli 18.04.2027 na 19.04.2027) jest spójny.
