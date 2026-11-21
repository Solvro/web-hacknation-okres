from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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
    ("kierownik", "Tomasz", "Kaczmarek", "Kierownik urzędu", "Kierownictwo", "kierownik_urzedu", "dyrektor", False, False, None),
    ("finanse", "Magdalena", "Czarnecka", "Naczelniczka wydziału", "Wydział Finansów", "kierujacy", "dyrektor", False, False, None),
    ("alicja", "Alicja", "Szulc", "Inspektorka", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca", False, False, None),
    ("marek", "Marek", "Kubiak", "Referent", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca", False, False, None),
    ("natalia", "Natalia", "Wróbel", "Starsza specjalistka", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca", False, False, None),
    ("joanna", "Joanna", "Kurek", "Specjalistka ds. budżetu", "Wydział Finansów", "pozostale", "finanse", False, False, None),
    ("rafal", "Rafał", "Duda", "Referent ds. rozliczeń", "Wydział Finansów", "pozostale", "finanse", False, False, None),
    ("karolina", "Karolina", "Król", "Inspektorka ds. zamówień", "Wydział Finansów", "pozostale", "finanse", False, False, None),
]
LOGINY_DEMO = ["dyrektor", "kadry", "oceniajaca", "oceniany", "piotr"]


# Dzień, względem którego datowane są dane HR partnera; w pokazie zegar demo ustawia się na ten dzień.
DZIEN_DEMO = date(2026, 11, 21)


class Command(BaseCommand):
    help = "Tworzy syntetyczny urząd, pracowników i sprawy ocen do demonstracji (tylko OKRES_DEMO=1)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.OKRES_DEMO:
            raise CommandError("seed_demo działa tylko w trybie demo (OKRES_DEMO=1).")
        urzad, _ = Urzad.objects.get_or_create(pk=1, defaults={
            "nazwa": "Urząd Administracji Publicznej w Bydgoszczy", "miejscowosc": "Bydgoszcz",
        })
        if urzad.nazwa == "Urząd Testowy w Bydgoszczy (DEMO)":
            urzad.nazwa = "Urząd Administracji Publicznej w Bydgoszczy"
            urzad.save(update_fields=["nazwa"])
        prac = {}
        for login, imie, nazwisko, stanowisko, komorka, rodzaj, przel, kadry, dg, urzednik in OSOBY:
            u, _ = User.objects.get_or_create(username=login)
            u.first_name, u.last_name = imie, nazwisko
            u.is_staff = u.is_superuser = kadry
            u.set_password(HASLO)
            u.save()
            p, _ = Pracownik.objects.update_or_create(user=u, defaults=dict(
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
            (jan, date(2025, 3, 16), "zatrudnienie"),
            (prac["piotr"], date(2024, 12, 2), "poprzednia_ocena"),
            (prac["oceniajaca"], date(2025, 6, 2), "poprzednia_ocena"),
        ]
        for p, poczatek, podstawa in sprawy:
            Ocena.objects.get_or_create(oceniany=p.user, poczatek_okresu=poczatek, defaults=dict(
                arkusz=p.arkusz, oceniajacy=p.przelozony.user, podstawa_poczatku=podstawa))
        self._przygotowane_sprawy(prac)
        self._hr_partner(prac)
        self.stdout.write(f"Konta: {', '.join(prac)} (hasło: {HASLO}). Logowanie: /logowanie/")

    def _przygotowane_sprawy(self, prac):
        # Każdy przebieg dotyczy wyłącznie nowej sprawy. Daty zmieniamy w tej samej transakcji
        # co seed, aby użyć reguł zwykłego obiegu i zachować ustawienia zegara po wczytaniu danych.
        zegar = ZegarDemo.objects.filter(pk=1).first()
        sprawy = [
            ("kierownik", date(2025, 2, 3), "ocena", "Skrócić ścieżkę akceptacji pism między wydziałami."),
            ("finanse", date(2024, 12, 9), "ocena", "Uzgadniać z wydziałami prognozę wydatków raz w miesiącu."),
            ("alicja", date(2026, 11, 9), "kryteria", "Raz w miesiącu przeglądać najczęstsze braki we wnioskach."),
            ("marek", date(2026, 11, 16), "start", ""),
            ("natalia", date(2024, 11, 18), "zapoznanie", "Przygotować warsztat z weryfikacji wniosków dla nowych pracowników."),
            ("joanna", date(2024, 11, 18), "sprzeciw", "Uzgodnić z wydziałami wspólną listę załączników do korekt budżetu."),
            ("rafal", date(2024, 10, 5), "zakonczona", "Przejść szkolenie z raportowania i poprowadzić przegląd miesięczny."),
            ("karolina", date(2024, 11, 29), "ocena", "Prowadzić wspólny kalendarz publikacji i aktualizować go co tydzień."),
        ]
        for login, poczatek, etap, cele in sprawy:
            osoba = prac[login]
            ocena, utworzona = Ocena.objects.get_or_create(
                oceniany=osoba.user, poczatek_okresu=poczatek,
                defaults={"arkusz": osoba.arkusz, "oceniajacy": osoba.przelozony.user,
                          "podstawa_poczatku": "zatrudnienie", "wersja_regul": rules.DOMYSLNA_WERSJA},
            )
            if not utworzona or etap == "start":
                continue
            rozmowa = poczatek + timedelta(days=8)
            ZegarDemo(data=rozmowa).save()
            ocena.zatwierdz_kryteria(rozmowa, "Bydgoszcz", cele)
            if etap == "kryteria":
                continue
            ocena.potwierdz_kryteria()
            if etap == "ocena":
                continue
            dzien_oceny = ocena.termin_oceny
            ZegarDemo(data=dzien_oceny).save()
            punkty = {kod: 7 for kod in ocena.wszystkie_kryteria()}
            if etap == "sprzeciw":
                punkty["organizacja_pracy"] = 3
            ocena.sporzadz(punkty, dzien_oceny, "", cele, miejscowosc="Bydgoszcz")
            if etap != "zapoznanie":
                ocena.potwierdz_zapoznanie("Bydgoszcz")
            if etap == "sprzeciw":
                ZegarDemo(data=dzien_oceny + timedelta(days=1)).save()
                ocena.zloz_sprzeciw("Proszę o ponowne sprawdzenie oceny organizacji pracy z uwzględnieniem harmonogramu korekt budżetu.")
            zaloz_kolejna(ocena)
        if zegar:
            zegar.save()
        else:
            ZegarDemo.objects.filter(pk=1).delete()

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
            (jan, 25, "przekazanie", "Przejęcie rejestru skarg po odejściu współpracownika"),
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
            Obserwacja.objects.create(ocena=ocena_jana, autor=jan.user, data=dzis - timedelta(days=20), kryterium="wspolpraca",
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
            ocena = Ocena.objects.filter(oceniany=prac[login].user).earliest("poczatek_okresu")
            Obserwacja.objects.get_or_create(
                ocena=ocena, autor=ocena.oceniajacy, data=dzis - timedelta(days=18),
                kryterium=kryterium, tresc=tresc, defaults={"skutek": skutek, "udostepniona": True},
            )
