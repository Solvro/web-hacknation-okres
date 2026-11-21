from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from oceny.models import Nieobecnosc, Ocena, Pracownik, Urzad

# Dane wyłącznie syntetyczne. Hasło jest jawne, więc komenda działa tylko w trybie demo.
HASLO = "demo"
OSOBY = [
    # login, imię, nazwisko, stanowisko, komórka, rodzaj, przełożony, kadry, DG, urzędnik (rok mianowania, stopień, data stopnia)
    ("dyrektor", "Dorota", "Dyrektorska", "Dyrektor generalny", "Kierownictwo", "kierujacy", None, False, True, None),
    ("kadry", "Krystyna", "Kadrowa", "Główna specjalistka ds. kadr", "Biuro Kadr", "pozostale", "dyrektor", True, False, None),
    ("oceniajaca", "Anna", "Syntetyczna", "Naczelniczka Wydziału Spraw Obywatelskich", "Wydział Spraw Obywatelskich",
     "kierujacy", "dyrektor", False, False, (2015, 4, date(2020, 9, 1))),
    ("oceniany", "Jan", "Testowy", "Starszy specjalista", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca",
     False, False, (2019, 2, date(2022, 5, 4))),
    ("piotr", "Piotr", "Przykładowy", "Specjalista", "Wydział Spraw Obywatelskich", "pozostale", "oceniajaca",
     False, False, None),
]
LOGINY_DEMO = [o[0] for o in OSOBY]


class Command(BaseCommand):
    help = "Tworzy syntetyczny urząd, pracowników i sprawy ocen do demonstracji (tylko OKRES_DEMO=1)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.OKRES_DEMO:
            raise CommandError("seed_demo działa tylko w trybie demo (OKRES_DEMO=1).")
        Urzad(nazwa="Urząd Testowy w Bydgoszczy (DEMO)", miejscowosc="Bydgoszcz").save()
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
        jan.nieobecnosci.all().delete()
        Nieobecnosc.objects.create(pracownik=jan, od=date(2026, 10, 5), do=date(2026, 10, 16))
        Nieobecnosc.objects.create(pracownik=jan, od=date(2026, 10, 19), do=date(2026, 11, 6))
        sprawy = [
            (jan, date(2025, 3, 16), "zatrudnienie"),
            (prac["piotr"], date(2024, 12, 2), "poprzednia_ocena"),
            (prac["oceniajaca"], date(2025, 6, 2), "poprzednia_ocena"),
        ]
        for p, poczatek, podstawa in sprawy:
            Ocena.objects.get_or_create(oceniany=p.user, poczatek_okresu=poczatek, defaults=dict(
                arkusz=p.arkusz, oceniajacy=p.przelozony.user, podstawa_poczatku=podstawa))
        self.stdout.write(f"Konta: {', '.join(LOGINY_DEMO)} (hasło: {HASLO}). Logowanie: /logowanie/")
