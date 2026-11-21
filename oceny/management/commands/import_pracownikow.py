"""Import pracowników z CSV (UC-18). Kolumny (nagłówek, separator ;):
login;imie;nazwisko;email;komorka;stanowisko;rodzaj_stanowiska;przelozony;urzednik;rok_mianowania;stopien;data_stopnia
rodzaj_stanowiska: kierownik_urzedu | kierujacy | pozostale; przelozony: login; urzednik: tak/nie; data_stopnia: RRRR-MM-DD.
Ponowny import aktualizuje dane (idempotentny). Hasła nie są importowane: konta logują się po nadaniu hasła lub przez SSO.
"""

import csv
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from oceny.models import Pracownik

WYMAGANE = {"login", "imie", "nazwisko", "stanowisko", "rodzaj_stanowiska"}


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("plik")

    @transaction.atomic
    def handle(self, *args, **options):
        with open(options["plik"], encoding="utf-8-sig", newline="") as f:
            wiersze = list(csv.DictReader(f, delimiter=";"))
        if not wiersze or not WYMAGANE <= set(wiersze[0]):
            raise CommandError(f"Brak wymaganych kolumn: {', '.join(sorted(WYMAGANE))}.")
        rodzaje = dict(Pracownik.RODZAJE)
        prac = {}
        for nr, w in enumerate(wiersze, start=2):
            if w["rodzaj_stanowiska"] not in rodzaje:
                raise CommandError(f"Wiersz {nr}: nieznany rodzaj stanowiska „{w['rodzaj_stanowiska']}”.")
            u, _ = User.objects.get_or_create(username=w["login"].strip())
            u.first_name, u.last_name, u.email = w["imie"].strip(), w["nazwisko"].strip(), (w.get("email") or "").strip()
            u.save()
            urzednik = (w.get("urzednik") or "").strip().lower() in ("tak", "1", "t")
            prac[u.username] = Pracownik.objects.update_or_create(user=u, defaults=dict(
                komorka=(w.get("komorka") or "").strip(), stanowisko=w["stanowisko"].strip(),
                rodzaj_stanowiska=w["rodzaj_stanowiska"], urzednik=urzednik,
                rok_mianowania=int(w["rok_mianowania"]) if urzednik and w.get("rok_mianowania") else None,
                stopien_sluzbowy=int(w["stopien"]) if urzednik and w.get("stopien") else None,
                data_stopnia=date.fromisoformat(w["data_stopnia"]) if urzednik and w.get("data_stopnia") else None,
            ))[0]
        for nr, w in enumerate(wiersze, start=2):
            if login := (w.get("przelozony") or "").strip():
                przel = prac.get(login) or Pracownik.objects.filter(user__username=login).first()
                if not przel:
                    raise CommandError(f"Wiersz {nr}: nieznany przełożony „{login}”.")
                prac[w["login"].strip()].przelozony = przel
                prac[w["login"].strip()].save(update_fields=["przelozony"])
        self.stdout.write(f"Zaimportowano lub zaktualizowano pracowników: {len(prac)}")
