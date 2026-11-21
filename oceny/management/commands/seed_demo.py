from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from oceny import rules
from oceny.models import Nieobecnosc, Obserwacja, Ocena, Pracownik, Urzad, ZegarDemo
from oceny.scheduler import zaloz_kolejna
from partner.models import Uzgodnienie, ZdarzenieZadania

# Dane wyłącznie syntetyczne. Hasło jest jawne, więc komenda działa tylko w trybie demo.
HASLO = "demo"
OSOBY = [
    # login, imię, nazwisko, stanowisko, komórka, rodzaj, przełożony, kadry, DG, urzędnik (rok mianowania, stopień, data stopnia)
    ("dyrektor", "Dorota", "Maj", "Dyrektor generalny", "Kierownictwo", "kierujacy", None, False, True, None),
    ("kadry", "Krystyna", "Lipińska", "Główna specjalistka ds. kadr", "Biuro Kadr", "pozostale", "dyrektor", True, False, None),
    ("oceniajaca", "Anna", "Leszczyńska", "Naczelniczka Wydziału Spraw Obywatelskich", "Wydział Spraw Obywatelskich",
     "kierujacy", "dyrektor", False, False, (2015, 4, date(2020, 9, 1))),
    ("oceniany", "Jan", "Borkowski", "Starszy specjalista", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca",
     False, False, (2019, 2, date(2022, 5, 4))),
    ("piotr", "Piotr", "Wysocki", "Specjalista", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca",
     False, False, None),
    # Kierownika urzędu (arkusz A) ocenia jego bezpośredni przełożony spoza urzędu (art. 81 ust. 1), a nie dyrektor
    # generalny. Osoba jest w bazie tylko jako oceniająca do arkusza; nie ma konta do logowania w pokazie.
    ("nadrzedny", "Ewa", "Zawadzka", "Prezes urzędu nadrzędnego (oceniająca spoza urzędu)", "Spoza urzędu: organ nadrzędny",
     "kierujacy", None, False, False, None),
    ("kierownik", "Tomasz", "Kaczmarek", "Kierownik urzędu", "Kierownictwo", "kierownik_urzedu", "nadrzedny", False, False, None),
    ("finanse", "Magdalena", "Czarnecka", "Naczelniczka wydziału", "Wydział Finansów", "kierujacy", "dyrektor", False, False, None),
    ("alicja", "Alicja", "Szulc", "Inspektorka", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca", False, False, None),
    ("marek", "Marek", "Kubiak", "Referent", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca", False, False, None),
    ("natalia", "Natalia", "Wróbel", "Starsza specjalistka", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca", False, False, None),
    ("joanna", "Joanna", "Kurek", "Specjalistka ds. budżetu", "Wydział Finansów", "pozostale", "finanse", False, False, None),
    ("rafal", "Rafał", "Duda", "Referent ds. rozliczeń", "Wydział Finansów", "pozostale", "finanse", False, False, None),
    ("karolina", "Karolina", "Król", "Inspektorka ds. zamówień", "Wydział Finansów", "pozostale", "finanse", False, False, None),
]
LOGINY_DEMO = ["dyrektor", "kadry", "oceniajaca", "oceniany", "piotr"]
BEZ_LOGOWANIA = {"nadrzedny"}
# Konta dodane w tej wersji seeda. Komplet z poprzedniej wersji ma stare daty spraw, więc nie dopisujemy do niego
# nowych spraw (powstałyby duplikaty). Nowy zestaw wczytuje się po wyczyszczeniu bazy.
NOWE_LOGINY = {"nadrzedny"}
NAZWA_URZEDU_DEMO = "Urząd Administracji Publicznej w Bydgoszczy"
NAZWY_URZEDU_DEMO = {NAZWA_URZEDU_DEMO, "Urząd Testowy w Bydgoszczy (DEMO)"}


# Dzień, względem którego datowane są dane HR partnera i etapy spraw; w pokazie zegar demo ustawia się na ten dzień.
DZIEN_DEMO = date(2026, 11, 21)

# Przebiegi spraw do dnia DZIEN_DEMO: (login, początek okresu, etap, cele i oczekiwania z części I,
# kryteria dodatkowe, oceny cząstkowe inne niż domyślne, wnioski do IPRZ, obserwacje oceniającego).
# Sprawy po ocenie mają różne cząstkowe i wnioski będące kolejnym krokiem rozwoju, a nie kopią celów.
PRZEBIEGI_BAZOWE = {
    "oceniany": ("ocena", "Rejestr skarg prowadzony na bieżąco, odpowiedź na skargę w ustawowym terminie. "
                 "Raz na kwartał jedna propozycja uproszczenia obsługi interesantów.",
                 ["orientacja_na_klienta", "kreatywnosc"], {}, "", []),
    "piotr": ("zakonczona", "Przygotowywać sprawozdania kwartalne z obsługi wniosków w terminie.", [],
              {"organizacja_pracy": 5, "rzetelnosc": 7, "wspolpraca": 7},
              "Szkolenie z planowania pracy przy zmiennych priorytetach; cotygodniowe ustalanie kolejności zadań z przełożoną.",
              [("rzetelnosc", 300, "Sprawozdanie za II kwartał bez korekt ze strony wojewody."),
               ("organizacja_pracy", 120, "Dwa sprawozdania oddane po terminie przy równoległej kolejce wniosków.")]),
    "oceniajaca": ("ocena", "Skrócić średni czas obsługi wniosku w wydziale do 14 dni; plan zastępstw na okres urlopowy.",
                   ["myslenie_analityczne"], {}, "", []),
}
PRZEBIEGI = [
    ("kierownik", date(2025, 2, 3), "ocena", "Skrócić ścieżkę akceptacji pism między wydziałami.", [], {}, "", []),
    ("kadry", date(2025, 9, 1), "ocena", "Przenieść teczki ocen okresowych do EZD i co miesiąc sprawdzać zbliżające się terminy.",
     [], {}, "", []),
    ("finanse", date(2024, 12, 9), "ocena", "Uzgadniać z wydziałami prognozę wydatków raz w miesiącu.", [], {}, "", []),
    ("alicja", date(2026, 11, 9), "kryteria", "Raz w miesiącu przeglądać najczęstsze braki we wnioskach.", [], {}, "", []),
    ("marek", date(2026, 11, 16), "start", "", [], {}, "", []),
    ("natalia", date(2024, 11, 18), "zapoznanie", "Przygotować warsztat z weryfikacji wniosków dla nowych pracowników.", [],
     {"wykorzystywanie_wiedzy": 9, "wspolpraca": 9},
     "Szkolenie dla trenerów wewnętrznych; mentoring dla dwóch nowych osób w wydziale w pierwszym półroczu.",
     [("wspolpraca", 400, "Poprowadziła warsztat z weryfikacji wniosków dla pięciu nowych osób."),
      ("wykorzystywanie_wiedzy", 150, "Opracowała ściągę ze zmian w ustawie o dowodach osobistych dla wydziału.")]),
    ("joanna", date(2024, 11, 18), "sprzeciw", "Uzgodnić z wydziałami wspólną listę załączników do korekt budżetu.", [],
     {"organizacja_pracy": 3},
     "Szkolenie z harmonogramowania prac budżetowych; wspólny kalendarz korekt prowadzony z wydziałami.",
     [("organizacja_pracy", 200, "Trzy korekty budżetu złożone w ostatnim dniu terminu, bez rezerwy na uzupełnienia."),
      ("wspolpraca", 90, "Uzgodniła listę załączników do korekt z czterema wydziałami.")]),
    ("rafal", date(2024, 10, 7), "zakonczona", "Przejść szkolenie z raportowania i poprowadzić przegląd miesięczny.", [],
     {"rzetelnosc": 9, "komunikacja": 5},
     "Kurs zaawansowanych funkcji arkusza kalkulacyjnego; samodzielne prowadzenie przeglądu kwartalnego.",
     [("rzetelnosc", 250, "Rozliczenia delegacji bez zwrotów z księgowości przez pół roku."),
      ("komunikacja", 100, "Notatka z przeglądu miesięcznego wymagała dwóch poprawek przed wysłaniem.")]),
    ("karolina", date(2024, 11, 29), "ocena", "Prowadzić wspólny kalendarz publikacji i aktualizować go co tydzień.", [], {}, "", []),
]
# Kolejny okres po ocenie ostatecznej: Rafał ma już wyznaczone kryteria, Piotr czeka na rozmowę (pokaz części I).
KOLEJNE = {"rafal": "Przygotować procedurę rozliczeń delegacji zagranicznych do końca I kwartału."}


def _roboczy(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _chwila(d):
    return timezone.make_aware(datetime.combine(d, time(10, 0))) if d else None


class Command(BaseCommand):
    help = "Tworzy syntetyczny urząd, pracowników i sprawy ocen do demonstracji (tylko OKRES_DEMO=1)."

    def add_arguments(self, parser):
        parser.add_argument("--na-starcie", action="store_true",
                            help="Wczytaj pustą bazę lub uzupełnij rozpoznany starszy zestaw demo.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.OKRES_DEMO:
            raise CommandError("seed_demo działa tylko w trybie demo (OKRES_DEMO=1).")
        if options["na_starcie"] and User.objects.exists():
            urzad = Urzad.biezacy()
            konta = set(Pracownik.objects.values_list("user__username", flat=True))
            if not urzad or urzad.nazwa not in NAZWY_URZEDU_DEMO or not set(LOGINY_DEMO) <= konta:
                self.stdout.write("Pominięto seed: istniejąca baza nie jest rozpoznanym zestawem demo.")
                return
            if {osoba[0] for osoba in OSOBY} - NOWE_LOGINY <= konta:
                if not NOWE_LOGINY <= konta:
                    self.stdout.write("Zestaw demo z poprzedniej wersji pozostawiono bez zmian. "
                                      "Nowe dane: docker compose down -v && docker compose up.")
                return

        Urzad.objects.get_or_create(pk=1, defaults={"nazwa": NAZWA_URZEDU_DEMO, "miejscowosc": "Bydgoszcz"})
        prac = {}
        for login, imie, nazwisko, stanowisko, komorka, rodzaj, przel, kadry, dg, urzednik in OSOBY:
            u, utworzono = User.objects.get_or_create(username=login, defaults={
                "first_name": imie, "last_name": nazwisko, "is_staff": kadry, "is_superuser": kadry,
            })
            if utworzono:
                if login in BEZ_LOGOWANIA:
                    u.set_unusable_password()
                else:
                    u.set_password(HASLO)
                u.save(update_fields=["password"])
            p, _ = Pracownik.objects.get_or_create(user=u, defaults=dict(
                stanowisko=stanowisko, komorka=komorka, rodzaj_stanowiska=rodzaj, przelozony=prac.get(przel),
                dyrektor_generalny=dg, urzednik=bool(urzednik), rok_mianowania=urzednik and urzednik[0],
                stopien_sluzbowy=urzednik and urzednik[1], data_stopnia=urzednik and urzednik[2],
                miejscowosc_pracy="Bydgoszcz"))
            prac[login] = p
        # Przykład KPRM: L4 5–16.10.2026 + urlop 19.10–6.11.2026 (bez przyczyn w systemie)
        jan = prac["oceniany"]
        Nieobecnosc.objects.get_or_create(pracownik=jan, od=date(2026, 10, 5), do=date(2026, 10, 16))
        Nieobecnosc.objects.get_or_create(pracownik=jan, od=date(2026, 10, 19), do=date(2026, 11, 6))
        sprawy = [
            (jan, prac["oceniajaca"], date(2025, 3, 16), "zatrudnienie"),
            (prac["piotr"], prac["oceniajaca"], date(2024, 11, 4), "zatrudnienie"),
            (prac["oceniajaca"], prac["dyrektor"], date(2025, 6, 2), "poprzednia_ocena"),
        ]
        nowe_bazowe = []
        for p, przelozony, poczatek, podstawa in sprawy:
            ocena, utworzona = Ocena.objects.get_or_create(oceniany=p.user, poczatek_okresu=poczatek, defaults=dict(
                arkusz=p.arkusz, oceniajacy=przelozony.user, podstawa_poczatku=podstawa))
            if utworzona:
                nowe_bazowe.append((p.user.username, ocena))
        self._przygotowane_sprawy(prac, nowe_bazowe)
        self._hr_partner(prac)
        self.stdout.write(f"Konta: {', '.join(k for k in prac if k not in BEZ_LOGOWANIA)} (hasło: {HASLO}). "
                          "Logowanie: /logowanie/")

    def _przygotowane_sprawy(self, prac, nowe_bazowe=()):
        # Każdy przebieg dotyczy wyłącznie nowej sprawy. Daty zmieniamy w tej samej transakcji
        # co seed, aby użyć reguł zwykłego obiegu i zachować ustawienia zegara po wczytaniu danych.
        # Stan na DZIEN_DEMO: żadna sprawa nie stoi po terminie, a kolejny okres zaczyna się dopiero po ocenie ostatecznej.
        zegar = ZegarDemo.objects.filter(pk=1).first()
        for login, ocena in nowe_bazowe:
            self._przeprowadz(ocena, *PRZEBIEGI_BAZOWE[login])
        for login, poczatek, *przebieg in PRZEBIEGI:
            osoba = prac[login]
            if osoba.przelozony is None:
                continue
            ocena, utworzona = Ocena.objects.get_or_create(
                oceniany=osoba.user, poczatek_okresu=poczatek,
                defaults={"arkusz": osoba.arkusz, "oceniajacy": osoba.przelozony.user,
                          "podstawa_poczatku": "zatrudnienie", "wersja_regul": rules.DOMYSLNA_WERSJA},
            )
            if utworzona:
                self._przeprowadz(ocena, *przebieg)
        if zegar:
            zegar.save()
        else:
            ZegarDemo.objects.filter(pk=1).delete()

    def _przeprowadz(self, ocena, etap, cele, dodatkowe, punkty_inne, wnioski, obserwacje):
        if etap == "start":
            return
        if dodatkowe:
            ocena.ustaw_kryteria(dodatkowe)
        rozmowa = _roboczy(ocena.poczatek_okresu + timedelta(days=8))
        ZegarDemo(data=rozmowa).save()
        ocena.zatwierdz_kryteria(rozmowa, "Bydgoszcz", cele)
        if etap != "kryteria":
            ocena.potwierdz_kryteria()
        if etap not in ("kryteria", "ocena"):
            for kryterium, dni_przed, tresc in obserwacje:
                Obserwacja.objects.create(ocena=ocena, autor=ocena.oceniajacy, kryterium=kryterium, tresc=tresc,
                                          data=ocena.termin_oceny - timedelta(days=dni_przed))
            dzien_oceny = ocena.termin_oceny
            ZegarDemo(data=dzien_oceny).save()
            punkty = {kod: 7 for kod in ocena.wszystkie_kryteria()} | punkty_inne
            ocena.sporzadz(punkty, dzien_oceny, "", wnioski, miejscowosc="Bydgoszcz")
            if etap != "zapoznanie":
                ocena.potwierdz_zapoznanie("Bydgoszcz")
            if etap == "sprzeciw":
                ZegarDemo(data=dzien_oceny + timedelta(days=1)).save()
                ocena.zloz_sprzeciw("Proszę o ponowne sprawdzenie oceny organizacji pracy z uwzględnieniem harmonogramu korekt budżetu.")
        Ocena.objects.filter(pk=ocena.pk).update(
            kryteria_zatwierdzone_at=_chwila(ocena.data_zatwierdzenia_kryteriow),
            kryteria_potwierdzone_at=_chwila(ocena.data_potwierdzenia_kryteriow),
            sporzadzona_at=_chwila(ocena.data_sporzadzenia))
        # Kolejną sprawę zakładamy dopiero po ocenie ostatecznej (zapoznanie i upływ terminu na sprzeciw).
        if etap == "zakonczona":
            ZegarDemo(data=ocena.termin_sprzeciwu + timedelta(days=1)).save()
            kolejna = zaloz_kolejna(ocena)
            login = ocena.oceniany.username
            if kolejna and login in KOLEJNE:
                self._przeprowadz(kolejna, "ocena", KOLEJNE[login], [], {}, "", [])

    def _hr_partner(self, prac):
        """Fakty do pokazu HR partnera, datowane względem stałego dnia DZIEN_DEMO (scenariusz w DEMO.md),
        niezależnie od dnia wczytania danych."""
        dzis = DZIEN_DEMO
        anna, piotr, jan = prac["oceniajaca"], prac["piotr"], prac["oceniany"]
        alicja = prac["alicja"]
        wpisy = [
            (piotr, 40, "nowe_zadanie", "Przygotowanie sprawozdania z obsługi wniosków za III kwartał"),
            (piotr, 33, "zmiana_priorytetu", "Sprawozdanie przed bieżącymi wnioskami (pilne dla wojewody)"),
            (piotr, 19, "zmiana_priorytetu", "Wnioski o dowody osobiste przed sprawozdaniem (kolejka)"),
            (piotr, 6, "zmiana_priorytetu", "Sprawozdanie znów pierwsze, termin skrócony o tydzień"),
            # Jan był nieobecny 05.10–06.11.2026: wpisy z jego udziałem są sprzed nieobecności albo po powrocie.
            (jan, 5, "przekazanie", "Przejęcie rejestru skarg po odejściu współpracownika"),
            (alicja, 8, "nowe_zadanie", "Przegląd braków w listopadowych wnioskach"),
            (alicja, 3, "przekazanie", "Przejęcie kolejki spraw wymagających uzupełnienia"),
        ]
        for p, dni, rodzaj, opis in wpisy:
            ZdarzenieZadania.objects.get_or_create(
                pracownik=p, autor=anna.user, data=dzis - timedelta(days=dni), rodzaj=rodzaj, opis=opis,
            )
        # Wcześniejsze uzgodnienie Piotra, które nie pomogło (sygnał „możliwy spadek zaangażowania”)
        Uzgodnienie.objects.get_or_create(pracownik=piotr, sygnal="seed:priorytety", defaults={
            "autor": anna.user, "dzialanie": "priorytety",
            "ustalenie": "Lista priorytetów na sierpień uzgadniana w poniedziałki.",
            "data": dzis - timedelta(days=95), "data_sprawdzenia": dzis - timedelta(days=50),
            "wynik": "nie_pomoglo", "notatka_z_wyniku": "Priorytety zmieniały się w trakcie tygodnia.",
        })
        ocena_jana = Ocena.objects.get(oceniany=jan.user, poczatek_okresu=date(2025, 3, 16))
        if not ocena_jana.obserwacje.exists():
            # Osiągnięcie zgłoszone w ostatnim dniu przed nieobecnością (02.10.2026); od tego czasu czeka na docenienie.
            Obserwacja.objects.create(ocena=ocena_jana, autor=jan.user, data=dzis - timedelta(days=50), kryterium="wspolpraca",
                                      tresc="Przeszkoliłem dwie nowe osoby z obsługi rejestru skarg.",
                                      skutek="Zastępstwa w rejestrze działają bez przerw.", udostepniona=True)
            Obserwacja.objects.create(ocena=ocena_jana, autor=anna.user, data=dzis - timedelta(days=60), kryterium="rzetelnosc",
                                      tresc="Raport kwartalny złożony 5 dni po terminie.", skutek="Opóźnienie zbiorczego raportu wydziału.")
        notatki = [
            ("finanse", "zarzadzanie_ludzmi", "Wprowadziła dyżury zastępcze przy zamknięciu miesiąca.",
             "Rozliczenia wpłynęły w terminie mimo urlopów w zespole."),
            ("karolina", "organizacja_pracy", "Uporządkowała harmonogram publikacji zamówień na kolejny kwartał.",
             "Wydziały mogą sprawdzić terminy w jednym miejscu."),
        ]
        for login, kryterium, tresc, skutek in notatki:
            ocena = Ocena.objects.filter(oceniany=prac[login].user).order_by("poczatek_okresu").first()
            if not ocena:
                continue
            Obserwacja.objects.get_or_create(
                ocena=ocena, autor=ocena.oceniajacy, data=dzis - timedelta(days=18),
                kryterium=kryterium, tresc=tresc, defaults={"skutek": skutek, "udostepniona": True},
            )
