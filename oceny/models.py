from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from . import punktacja, rules, terminy, zegar


class Urzad(models.Model):
    """Dane urzędu do nagłówka arkusza. Jeden wiersz (pk=1)."""

    nazwa = models.CharField(max_length=300)
    miejscowosc = models.CharField(max_length=100)

    class Meta:
        verbose_name = verbose_name_plural = "urząd"

    def __str__(self):
        return self.nazwa

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def biezacy(cls) -> "Urzad | None":
        return cls.objects.filter(pk=1).first()


class Pracownik(models.Model):
    """Dane kadrowe członka korpusu służby cywilnej (bez danych o zdrowiu i przyczynach nieobecności)."""

    RODZAJE = [
        ("kierownik_urzedu", "kierownik urzędu (§ 3 ust. 2)"),
        ("kierujacy", "bezpośrednie kierowanie pracownikami (§ 3 ust. 3)"),
        ("pozostale", "pozostałe stanowiska (§ 3 ust. 4)"),
    ]
    ARKUSZ_DLA_RODZAJU = {"kierownik_urzedu": "A", "kierujacy": "B", "pozostale": "C"}

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pracownik")
    komorka = models.CharField("komórka organizacyjna", max_length=200, blank=True)
    stanowisko = models.CharField(max_length=200)
    rodzaj_stanowiska = models.CharField(max_length=20, choices=RODZAJE)
    przelozony = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="podwladni")
    dyrektor_generalny = models.BooleanField(default=False, help_text="Rozpatruje sprzeciwy i widzi statystyki zbiorcze.")
    urzednik = models.BooleanField("urzędnik służby cywilnej (mianowany)", default=False)
    rok_mianowania = models.PositiveSmallIntegerField(null=True, blank=True)
    stopien_sluzbowy = models.PositiveSmallIntegerField(null=True, blank=True)
    data_stopnia = models.DateField("data przyznania stopnia", null=True, blank=True)
    miejscowosc_pracy = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = "pracownicy"

    def __str__(self):
        return self.imie_nazwisko

    @property
    def imie_nazwisko(self) -> str:
        return self.user.get_full_name() or self.user.username

    @property
    def arkusz(self) -> str:
        return self.ARKUSZ_DLA_RODZAJU[self.rodzaj_stanowiska]


class Nieobecnosc(models.Model):
    """Okres usprawiedliwionej nieobecności. Celowo bez przyczyny (np. danych o zdrowiu)."""

    pracownik = models.ForeignKey(Pracownik, on_delete=models.CASCADE, related_name="nieobecnosci")
    od = models.DateField()
    do = models.DateField()

    class Meta:
        verbose_name = "nieobecność usprawiedliwiona"
        verbose_name_plural = "nieobecności usprawiedliwione"
        ordering = ["od"]

    def clean(self):
        if self.od and self.do and self.do < self.od:
            raise ValidationError({"do": "Koniec nieobecności nie może poprzedzać jej początku."})


class Ocena(models.Model):
    arkusz = models.CharField(max_length=1, choices=[("A", "A"), ("B", "B"), ("C", "C")])
    wersja_regul = models.CharField(max_length=20, default=rules.DOMYSLNA_WERSJA)
    oceniany = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="oceny_wlasne")
    oceniajacy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="oceny_sporzadzane")
    PODSTAWY_POCZATKU = [
        ("zatrudnienie", "zatrudnienie na czas nieokreślony"),
        ("mianowanie", "mianowanie"),
        ("poprzednia_ocena", "poprzednia ocena okresowa"),
    ]
    poczatek_okresu = models.DateField("początek okresu oceny", null=True)
    podstawa_poczatku = models.CharField(max_length=20, choices=PODSTAWY_POCZATKU, default="zatrudnienie")
    poprzednia = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="nastepna",
                                      help_text="Poprzednia ocena, od której liczy się ten okres.")
    kryteria_dodatkowe = models.JSONField(default=list, blank=True)
    wersja = models.PositiveSmallIntegerField(default=1, help_text="2 = ocena sporządzona po raz drugi po sprzeciwie.")
    anulowana_powod = models.CharField(max_length=300, blank=True)
    # Zdarzenia kadrowe: terminy ustalone poza regułą podstawową (z podstawą w ZdarzenieKadrowe)
    termin_oceny_zmieniony = models.DateField(null=True, blank=True)
    termin_kryteriow_zmieniony = models.DateField(null=True, blank=True)
    najwczesniej_sporzadzenia = models.DateField(null=True, blank=True)
    # Część I: rozmowa z § 5 ust. 1, potwierdzenie oceniającego, potem ocenianego (§ 6)
    data_rozmowy_rozpoczynajacej = models.DateField(null=True, blank=True)
    kryteria_zatwierdzone_at = models.DateTimeField(null=True, blank=True)
    data_zatwierdzenia_kryteriow = models.DateField(null=True, blank=True)
    miejscowosc_czesc_i = models.CharField(max_length=100, blank=True)
    kryteria_potwierdzone_at = models.DateTimeField(null=True, blank=True)
    data_potwierdzenia_kryteriow = models.DateField(null=True, blank=True)

    # Część II arkusza: {kod kryterium: punkty}
    oceny_czastkowe = models.JSONField(default=dict, blank=True)
    data_rozmowy_oceniajacej = models.DateField(null=True, blank=True)
    uzasadnienie = models.TextField(blank=True)
    wnioski_iprz = models.TextField(blank=True)
    sporzadzona_at = models.DateTimeField(null=True, blank=True)
    data_sporzadzenia = models.DateField(null=True, blank=True)
    srednia = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    poziom = models.CharField(max_length=40, blank=True)
    pozytywna = models.BooleanField(null=True, blank=True)
    okres_od = models.DateField("okres podlegania ocenie od", null=True, blank=True)
    okres_do = models.DateField("okres podlegania ocenie do", null=True, blank=True)
    miejscowosc_czesc_ii = models.CharField(max_length=100, blank=True)
    # Dane poprzedniej oceny okresowej urzędnika (z historii albo wpisane przez oceniającego)
    poprz_ocena = models.CharField(max_length=12, blank=True,
                                   choices=[("pozytywna", "pozytywna"), ("negatywna", "negatywna"), ("brak", "brak")])
    poprz_poziom = models.CharField(max_length=40, blank=True)
    poprz_data = models.DateField(null=True, blank=True)
    # Część III: wniosek o kolejny stopień służbowy (art. 89 ust. 1)
    wniosek_stopien = models.CharField(max_length=12, blank=True,
                                       choices=[("tak", "TAK"), ("nie", "NIE"), ("nie_dotyczy", "NIE DOTYCZY")])
    rok_mianowania = models.PositiveSmallIntegerField(null=True, blank=True)
    stopien_sluzbowy = models.PositiveSmallIntegerField(null=True, blank=True)
    data_stopnia = models.DateField(null=True, blank=True)
    umotywowanie_wniosku = models.TextField(blank=True)
    data_zapoznania = models.DateField(null=True, blank=True)
    miejscowosc_zapoznania = models.CharField(max_length=100, blank=True)
    sposob_zapoznania = models.CharField(
        max_length=20, blank=True,
        choices=[("potwierdzenie", "potwierdzenie przez ocenianego"), ("fikcja", "fikcja zapoznania")],
    )
    uwagi_zapoznania = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "oceny"

    def __str__(self):
        return f"Ocena {self.pk} · arkusz {self.arkusz} · {self.oceniany}"

    def save(self, *args, **kwargs):
        # Arkusz wynika ze stanowiska (§ 3), chyba że kadry wskazały go jawnie.
        if not self.arkusz and hasattr(self.oceniany, "pracownik"):
            self.arkusz = self.oceniany.pracownik.arkusz
        super().save(*args, **kwargs)

    # Terminy cyklu (deterministyczne, z rachunkiem do wglądu)

    @property
    def po_negatywnej(self) -> bool:
        return bool(self.poprzednia and self.poprzednia.pozytywna is False)

    def _ostatnie_zdarzenie(self, *rodzaje):
        return self.zdarzenia_kadrowe.filter(rodzaj__in=rodzaje).order_by("-pk").first()

    def rachunek_kryteriow(self) -> terminy.Rachunek | None:
        if self.termin_kryteriow_zmieniony:
            z = self._ostatnie_zdarzenie("zmiana_stanowiska")
            return terminy.Rachunek(self.termin_kryteriow_zmieniony, (
                terminy.Krok("Zmiana stanowiska z istotną zmianą obowiązków", z.data if z else self.termin_kryteriow_zmieniony),
                terminy.Krok("+ 30 dni na ponowne ustalenie kryteriów i rozmowę", self.termin_kryteriow_zmieniony,
                             "§ 9 ust. 1 rozporządzenia")))
        cfg = rules.load(self.wersja_regul)["terminy"]
        if self.po_negatywnej:
            return terminy.rachunek_dniowy(self.poprzednia.data_sporzadzenia, cfg["kryteria_po_negatywnej_dni"],
                                           "Sporządzenie oceny negatywnej", "§ 7 ust. 2 rozporządzenia")
        if not self.poczatek_okresu:
            return None
        return terminy.rachunek_dniowy(self.poczatek_okresu, cfg["kryteria_dni"],
                                       f"Początek okresu oceny ({self.get_podstawa_poczatku_display()})", "§ 7 ust. 1 rozporządzenia")

    def rachunek_oceny(self) -> terminy.Rachunek | None:
        if self.termin_oceny_zmieniony:
            z = self._ostatnie_zdarzenie("zmiana_terminu", "zmiana_stanowiska")
            bazowy = self._rachunek_oceny_bazowy()
            kroki = list(bazowy.kroki) if bazowy else []
            kroki.append(terminy.Krok(f"Zmiana terminu: {z.opis if z else 'zdarzenie kadrowe'}", self.termin_oceny_zmieniony,
                                      z.podstawa if z else ""))
            return terminy.Rachunek(self.termin_oceny_zmieniony, tuple(kroki))
        return self._rachunek_oceny_bazowy()

    def _rachunek_oceny_bazowy(self) -> terminy.Rachunek | None:
        cfg = rules.load(self.wersja_regul)["terminy"]
        if self.po_negatywnej:
            if not self.poprzednia.zapoznany:
                return None
            return terminy.rachunek_miesieczny(self.poprzednia.data_zapoznania, cfg["ponowna_po_negatywnej_miesiace"],
                                               "Zapoznanie z oceną negatywną", "art. 81 ust. 9 ustawy")
        if not self.poczatek_okresu:
            return None
        nieobecnosci = []
        if hasattr(self.oceniany, "pracownik"):
            nieobecnosci = [terminy.Okres(n.od, n.do) for n in self.oceniany.pracownik.nieobecnosci.all()]
        return terminy.rachunek_terminu_oceny(self.poczatek_okresu, nieobecnosci, self.wersja_regul,
                                              f"Początek okresu oceny ({self.get_podstawa_poczatku_display()})")

    @property
    def termin_oceny(self):
        r = self.rachunek_oceny()
        return r.termin if r else None

    @property
    def etap(self) -> str:
        if self.anulowana_powod:
            return "anulowana"
        if not self.kryteria_zablokowane:
            return "kryteria"
        if not self.sporzadzona:
            return "ocena"
        if not self.zapoznany:
            return "zapoznanie"
        sprzeciw = self.sprzeciw_biezacy
        if sprzeciw:
            return "zakonczona" if sprzeciw.decyzja else "sprzeciw"
        if zegar.dzis() <= self.termin_sprzeciwu:
            return "termin_sprzeciwu"
        return "zakonczona"

    ETAPY = {
        "kryteria": "wyznaczenie kryteriów (część I)",
        "ocena": "rozmowa oceniająca i ocena (część II)",
        "zapoznanie": "zapoznanie z oceną",
        "termin_sprzeciwu": "biegnie termin na sprzeciw",
        "sprzeciw": "sprzeciw w rozpatrzeniu",
        "zakonczona": "zakończona",
        "anulowana": "anulowana",
    }

    @property
    def etap_nazwa(self) -> str:
        return self.ETAPY[self.etap]

    def nastepny_krok(self, user) -> dict | None:
        """Najbliższa czynność w sprawie: opis, termin, kto odpowiada i czy to zadanie tego użytkownika."""
        etap = self.etap
        if etap == "kryteria":
            r = self.rachunek_kryteriow()
            termin = r.termin if r else None
            if self.kryteria_zatwierdzone:
                opis, kto = "Potwierdź rozmowę i zapoznanie z kryteriami", self.oceniany
            else:
                opis, kto = "Przeprowadź rozmowę i wyznacz kryteria", self.oceniajacy
        elif etap == "ocena":
            opis, kto, termin = "Przeprowadź rozmowę oceniającą i sporządź ocenę", self.oceniajacy, self.termin_oceny
        elif etap == "zapoznanie":
            opis, kto, termin = "Zapoznaj się z oceną", self.oceniany, None
        elif etap == "termin_sprzeciwu":
            opis, kto, termin = "Możliwość wniesienia sprzeciwu", self.oceniany, self.termin_sprzeciwu
        elif etap == "sprzeciw":
            dg = Pracownik.objects.filter(dyrektor_generalny=True).select_related("user").first()
            opis, kto, termin = "Rozpatrz sprzeciw (art. 83 ust. 3)", dg and dg.user, self.sprzeciw_biezacy.termin_rozpatrzenia
        else:
            return None
        return {"opis": opis, "kto": kto, "termin": termin, "moj": kto is not None and kto.id == user.id}

    @property
    def kryteria_zatwierdzone(self) -> bool:
        """Oceniający potwierdził rozmowę i kryteria; zwykła edycja kryteriów jest zamknięta."""
        return self.kryteria_zatwierdzone_at is not None

    @property
    def kryteria_zablokowane(self) -> bool:
        """Obie strony potwierdziły część I."""
        return self.kryteria_potwierdzone_at is not None

    @property
    def sporzadzona(self) -> bool:
        return self.sporzadzona_at is not None

    def wszystkie_kryteria(self) -> dict[str, str]:
        """Obowiązkowe z arkusza, potem wybrane dodatkowe, w kolejności ze wzoru."""
        dodatkowe = rules.extra_criteria(self.arkusz, self.wersja_regul)
        return rules.mandatory_criteria(self.arkusz, self.wersja_regul) | {k: dodatkowe[k] for k in self.kryteria_dodatkowe}

    def clean(self):
        cfg = rules.load(self.wersja_regul)["kryteria_dodatkowe"]
        wybrane = self.kryteria_dodatkowe
        if len(wybrane) > cfg["max"]:
            raise ValidationError(f"Można wybrać maksymalnie {cfg['max']} kryteria dodatkowe.")
        if len(set(wybrane)) != len(wybrane):
            raise ValidationError("Kryteria dodatkowe nie mogą się powtarzać.")
        nieznane = set(wybrane) - rules.extra_criteria(self.arkusz, self.wersja_regul).keys()
        if nieznane:
            raise ValidationError(f"Kryteria spoza wykazu lub powielające obowiązkowe: {', '.join(sorted(nieznane))}.")

    def _zapisz_korekte(self, kto, pole: str, przed, po, powod: str):
        if not (kto and kto.is_staff):
            raise PermissionDenied("Korektę wykonuje administrator.")
        if not powod.strip():
            raise ValidationError({"powod": "Podaj powód korekty."})
        Korekta.objects.create(ocena=self, kto=kto, pole=pole, przed=przed, po=po, powod=powod.strip())

    @transaction.atomic
    def ustaw_kryteria(self, kody: list[str], korekta_przez=None, powod: str = ""):
        if self.sporzadzona:
            raise PermissionDenied("Ocena została sporządzona; kryteriów nie można już zmienić.")
        przed = list(self.kryteria_dodatkowe)
        if self.kryteria_zatwierdzone:
            if korekta_przez is None:
                raise PermissionDenied("Kryteria zostały zatwierdzone; zmiana tylko w trybie korekty administratora.")
            self._zapisz_korekte(korekta_przez, "kryteria_dodatkowe", przed, list(kody), powod)
        self.kryteria_dodatkowe = list(kody)
        self.full_clean()
        self.save()

    def zatwierdz_kryteria(self, data_rozmowy, miejscowosc: str = ""):
        """Oceniający potwierdza przeprowadzenie rozmowy z § 5 ust. 1 i zapoznanie ocenianego z kryteriami."""
        if self.kryteria_zatwierdzone:
            raise PermissionDenied("Kryteria zostały już zatwierdzone.")
        dzis = zegar.dzis()
        if data_rozmowy is None:
            raise ValidationError({"data_rozmowy": "Podaj datę rozmowy, w której omówiono kryteria (§ 5 ust. 1)."})
        if data_rozmowy > dzis:
            raise ValidationError({"data_rozmowy": "Rozmowa nie może mieć daty z przyszłości."})
        if self.poczatek_okresu and data_rozmowy < self.poczatek_okresu:
            raise ValidationError({"data_rozmowy": "Rozmowa nie może poprzedzać początku okresu oceny."})
        self.data_rozmowy_rozpoczynajacej = data_rozmowy
        self.miejscowosc_czesc_i = miejscowosc.strip()
        self.kryteria_zatwierdzone_at = timezone.now()
        self.data_zatwierdzenia_kryteriow = dzis
        self.save()

    def potwierdz_kryteria(self):
        """Oceniany potwierdza rozmowę i zapoznanie z kryteriami oraz terminem oceny (§ 6 ust. 2)."""
        if not self.kryteria_zatwierdzone:
            raise PermissionDenied("Oceniający nie zatwierdził jeszcze kryteriów.")
        if self.kryteria_zablokowane:
            raise PermissionDenied("Kryteria zostały już potwierdzone.")
        self.kryteria_potwierdzone_at = timezone.now()
        self.data_potwierdzenia_kryteriow = zegar.dzis()
        self.save(update_fields=["kryteria_potwierdzone_at", "data_potwierdzenia_kryteriow"])

    def podglad_wyniku(self, czastkowe: dict[str, int]) -> punktacja.Wynik | None:
        """Wynik dla kompletu ocen cząstkowych, inaczej None (podgląd nie zgaduje brakujących)."""
        if set(czastkowe) != set(self.wszystkie_kryteria()):
            return None
        try:
            return punktacja.oblicz(list(czastkowe.values()), self.wersja_regul)
        except ValueError:
            return None

    @property
    def oceniany_urzednik(self) -> bool:
        p = getattr(self.oceniany, "pracownik", None)
        return bool(p and p.urzednik)

    def poprzednia_z_historii(self) -> dict | None:
        """Dane poprzedniej oceny, jeśli jest w systemie (pole uzupełniane automatycznie)."""
        if not (self.poprzednia and self.poprzednia.sporzadzona):
            return None
        return {"poprz_ocena": "pozytywna" if self.poprzednia.pozytywna else "negatywna",
                "poprz_poziom": self.poprzednia.poziom, "poprz_data": self.poprzednia.data_sporzadzenia}

    def domyslne_pola(self) -> dict:
        """Wartości domyślne pól części II i III ze schematu KPRM."""
        dzis = zegar.dzis()
        termin = self.termin_oceny
        p = getattr(self.oceniany, "pracownik", None)
        domyslne = {
            # Przypis 6 do wzoru: „od” to data zapoznania ocenianego z kryteriami (część I).
            "okres_od": self.data_potwierdzenia_kryteriow or self.poczatek_okresu,
            "okres_do": min(dzis, termin) if termin else dzis,
            "rok_mianowania": p and p.rok_mianowania, "stopien_sluzbowy": p and p.stopien_sluzbowy,
            "data_stopnia": p and p.data_stopnia,
        }
        if not self.oceniany_urzednik:
            domyslne["wniosek_stopien"] = "nie_dotyczy"
        return domyslne | (self.poprzednia_z_historii() or {})

    def bledy_formalne(self, czastkowe, data_rozmowy, uzasadnienie, wnioski, **pola) -> dict[str, str]:
        """Strażnik formalny przed sporządzeniem oceny (§§ 10-11, art. 89 ust. 1). Zwraca {pole: komunikat}."""
        cfg = rules.load(self.wersja_regul)["punktacja"]
        pola = self.domyslne_pola() | {k: v for k, v in pola.items() if v not in (None, "")}
        bledy = {}
        if not self.kryteria_zablokowane:
            bledy["kryteria"] = "Oceniany nie potwierdził jeszcze kryteriów (§ 7)."
        skala = set(cfg["skala_czastkowa"])
        for kod, nazwa in self.wszystkie_kryteria().items():
            if czastkowe.get(kod) not in skala:
                bledy[f"kryterium_{kod}"] = f"Przyznaj ocenę cząstkową za kryterium „{nazwa}” (§ 11 ust. 1 pkt 1)."
        if data_rozmowy is None:
            bledy["data_rozmowy"] = "Podaj datę rozmowy oceniającej (§ 10)."
        elif data_rozmowy > zegar.dzis():
            bledy["data_rozmowy"] = "Rozmowa oceniająca musi odbyć się przed sporządzeniem oceny lub tego samego dnia (§ 10)."
        elif self.data_rozmowy_rozpoczynajacej and data_rozmowy < self.data_rozmowy_rozpoczynajacej:
            bledy["data_rozmowy"] = "Rozmowa oceniająca nie może poprzedzać rozmowy o kryteriach."
        od, do = pola.get("okres_od"), pola.get("okres_do")
        if not (od and do):
            bledy["okres"] = "Podaj okres, w którym oceniany podlegał ocenie."
        elif od > do or do > zegar.dzis():
            bledy["okres"] = "Okres podlegania ocenie: data „od” nie może być późniejsza niż „do”, a „do” nie może być z przyszłości."
        elif self.poczatek_okresu and od < self.poczatek_okresu:
            bledy["okres"] = "Okres podlegania ocenie nie może zaczynać się przed początkiem okresu oceny."
        if self.najwczesniej_sporzadzenia and zegar.dzis() < self.najwczesniej_sporzadzenia:
            bledy["termin"] = (f"Przy zmianie stanowiska ocenę sporządza się nie wcześniej niż 7 dni przed zmianą "
                               f"(§ 9 ust. 2), tj. od {self.najwczesniej_sporzadzenia:%d.%m.%Y}.")
        if self.po_negatywnej and not self.termin_oceny_zmieniony and (r := self.rachunek_oceny()) and zegar.dzis() < r.termin:
            bledy["termin"] = (f"Ponowną ocenę po ocenie negatywnej sporządza się po upływie 6 miesięcy od zapoznania "
                               f"(art. 81 ust. 9), tj. od {r.termin:%d.%m.%Y}.")
        wynik = self.podglad_wyniku(czastkowe)
        if wynik and not wynik.pozytywna and not uzasadnienie.strip():
            bledy["uzasadnienie"] = "Uzupełnij uzasadnienie oceny negatywnej (§ 11 ust. 3)."
        if cfg["wnioski_iprz_obowiazkowe"] and not wnioski.strip():
            bledy["wnioski_iprz"] = "Wpisz wnioski do indywidualnego programu rozwoju zawodowego (§ 11 ust. 1 pkt 5)."
        if self.oceniany_urzednik:
            bledy |= self._bledy_urzednika(pola, wynik)
        return bledy

    def _bledy_urzednika(self, pola, wynik) -> dict[str, str]:
        bledy = {}
        if pola.get("poprz_ocena") not in ("pozytywna", "negatywna", "brak"):
            bledy["poprz_ocena"] = "Wskaż poprzednią ocenę okresową urzędnika albo „brak”."
        elif pola["poprz_ocena"] != "brak" and not (pola.get("poprz_poziom") and pola.get("poprz_data")):
            bledy["poprz_ocena"] = "Uzupełnij poziom i datę sporządzenia poprzedniej oceny."
        wniosek = pola.get("wniosek_stopien")
        if wniosek not in ("tak", "nie"):
            bledy["wniosek_stopien"] = "Zaznacz, czy do oceny dołączono wniosek o kolejny stopień służbowy."
        elif wniosek == "tak":
            if wynik and not wynik.pozytywna:
                bledy["wniosek_stopien"] = "Wniosek o kolejny stopień służbowy wymaga oceny pozytywnej (art. 89 ust. 1)."
            stopien = pola.get("stopien_sluzbowy")
            if not stopien:
                bledy["stopien_sluzbowy"] = "Wskaż posiadany stopień służbowy."
            elif stopien >= 9:
                bledy["stopien_sluzbowy"] = ("Ocenianemu nie można przyznać kolejnego stopnia służbowego. "
                                             "Oceniany posiada już najwyższy możliwy stopień służbowy.")
            rok = pola.get("rok_mianowania")
            if not rok or not 2008 <= rok <= zegar.dzis().year:
                bledy["rok_mianowania"] = f"Podaj rok mianowania (2008–{zegar.dzis().year})."
            if not pola.get("data_stopnia"):
                bledy["data_stopnia"] = "Podaj datę przyznania posiadanego stopnia służbowego."
            if not (pola.get("umotywowanie_wniosku") or "").strip():
                bledy["umotywowanie_wniosku"] = "Uzupełnij umotywowanie wniosku o kolejny stopień służbowy."
        return bledy

    def obserwacje_dla(self, user):
        return [o for o in self.obserwacje.select_related("autor") if o.widoczna_dla(user)]

    def dodaj_obserwacje(self, autor, data, tresc: str, kryterium: str = "", skutek: str = "", udostepniona: bool = False):
        if autor.id not in (self.oceniajacy_id, self.oceniany_id):
            raise PermissionDenied("Obserwacje dodają strony oceny.")
        if self.sporzadzona:
            raise PermissionDenied("Ocena została sporządzona; okres obserwacji jest zamknięty.")
        if not tresc.strip():
            raise ValidationError({"tresc": "Opisz zaobserwowane działanie."})
        # Osiągnięcie zgłoszone przez ocenianego zawsze trafia do przełożonego.
        o = Obserwacja(ocena=self, autor=autor, data=data or zegar.dzis(), kryterium=kryterium, tresc=tresc.strip(),
                       skutek=skutek.strip(), udostepniona=udostepniona or autor.id == self.oceniany_id)
        o.full_clean()
        o.save()
        return o

    def obserwacje_wg_kryteriow(self, user) -> list[tuple[str, str, list]]:
        """Dla przygotowania rozmowy: kryterium → widoczne obserwacje (puste listy też, jako sygnał do pytania)."""
        widoczne = self.obserwacje_dla(user)
        grupy = [(kod, nazwa, [o for o in widoczne if o.kryterium == kod]) for kod, nazwa in self.wszystkie_kryteria().items()]
        bez = [o for o in widoczne if not o.kryterium]
        if bez:
            grupy.append(("", "Bez przypisanego kryterium", bez))
        return grupy

    @transaction.atomic
    def sporzadz(self, czastkowe: dict[str, int], data_rozmowy, uzasadnienie: str, wnioski: str, **pola):
        if self.sporzadzona:
            raise PermissionDenied("Ocena została już sporządzona.")
        bledy = self.bledy_formalne(czastkowe, data_rozmowy, uzasadnienie, wnioski, **pola)
        if bledy:
            raise ValidationError(bledy)
        wynik = self.podglad_wyniku(czastkowe)
        pola = self.domyslne_pola() | {k: v for k, v in pola.items() if v not in (None, "")}
        for nazwa in ("okres_od", "okres_do", "poprz_data", "rok_mianowania", "stopien_sluzbowy", "data_stopnia"):
            setattr(self, nazwa, pola.get(nazwa))
        if self.oceniany_urzednik:
            self.poprz_ocena = pola["poprz_ocena"]
            if self.poprz_ocena == "brak":
                self.poprz_poziom, self.poprz_data = "", None
            else:
                self.poprz_poziom = pola.get("poprz_poziom") or ""
        else:
            # Sekcje dotyczące urzędnika są nieaktywne dla pracownika służby cywilnej.
            self.poprz_data = self.rok_mianowania = self.stopien_sluzbowy = self.data_stopnia = None
        self.miejscowosc_czesc_ii = (pola.get("miejscowosc") or "").strip()
        if self.oceniany_urzednik:
            self.wniosek_stopien = pola["wniosek_stopien"]
            self.umotywowanie_wniosku = (pola.get("umotywowanie_wniosku") or "").strip() if self.wniosek_stopien == "tak" else ""
        else:
            self.wniosek_stopien = "nie_dotyczy"
        self.oceny_czastkowe = {k: czastkowe[k] for k in self.wszystkie_kryteria()}
        self.data_rozmowy_oceniajacej = data_rozmowy
        self.uzasadnienie = uzasadnienie.strip()
        self.wnioski_iprz = wnioski.strip()
        self.srednia = (Decimal(wynik.srednia.numerator) / wynik.srednia.denominator).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.poziom = wynik.poziom_nazwa
        self.pozytywna = wynik.pozytywna
        self.sporzadzona_at = timezone.now()
        self.data_sporzadzenia = zegar.dzis()
        self.save()

    # § 12 i art. 83 ustawy: zapoznanie i sprzeciw

    @property
    def zapoznany(self) -> bool:
        return self.data_zapoznania is not None

    def _zapoznaj(self, sposob: str, uwagi: str = "", data=None):
        if not self.sporzadzona:
            raise PermissionDenied("Ocena nie została jeszcze sporządzona.")
        if self.zapoznany:
            raise PermissionDenied("Zapoznanie zostało już odnotowane.")
        self.data_zapoznania = data or zegar.dzis()
        self.sposob_zapoznania = sposob
        self.uwagi_zapoznania = uwagi
        self.save(update_fields=["data_zapoznania", "sposob_zapoznania", "uwagi_zapoznania", "miejscowosc_zapoznania"])

    def potwierdz_zapoznanie(self, miejscowosc: str = ""):
        self.miejscowosc_zapoznania = miejscowosc.strip()
        self._zapoznaj("potwierdzenie")

    def odnotuj_fikcje_zapoznania(self, kto, uwagi: str, data_doreczenia):
        """Kadry dokumentują, że informacja o ocenie dotarła, a oceniany nie mógł lub nie chciał potwierdzić.
        Sam upływ czasu nie wystarcza; datą zapoznania jest udokumentowana data doręczenia."""
        if not kto.is_staff:
            raise PermissionDenied("Fikcję zapoznania dokumentuje komórka kadrowa.")
        if not uwagi.strip():
            raise ValidationError({"uwagi": "Opisz, jak informacja o ocenie dotarła do ocenianego i dlaczego nie potwierdził zapoznania."})
        if not data_doreczenia or data_doreczenia > zegar.dzis() or (self.data_sporzadzenia and data_doreczenia < self.data_sporzadzenia):
            raise ValidationError({"data_doreczenia": "Podaj datę doręczenia: nie wcześniejszą niż sporządzenie i nie z przyszłości."})
        self._zapoznaj("fikcja", uwagi.strip(), data_doreczenia)

    @property
    def termin_sprzeciwu(self):
        if not self.zapoznany:
            return None
        return terminy.termin_dniowy(self.data_zapoznania, rules.load(self.wersja_regul)["terminy"]["sprzeciw_dni"])

    def terminy_po_negatywnej(self) -> dict:
        """Kryteria w 7 dni od sporządzenia (§ 7 ust. 2), ponowna ocena po 6 mies. od zapoznania (art. 81 ust. 9)."""
        if self.pozytywna is not False:
            return {}
        cfg = rules.load(self.wersja_regul)["terminy"]
        wynik = {"kryteria_nowego_okresu": terminy.termin_dniowy(self.data_sporzadzenia, cfg["kryteria_po_negatywnej_dni"])}
        if self.zapoznany:
            wynik["ponowna_ocena"] = terminy.termin_miesieczny(self.data_zapoznania, cfg["ponowna_po_negatywnej_miesiace"])
        return wynik

    # Zdarzenia kadrowe (art. 81 ust. 6 i 8, §§ 8–9 rozporządzenia)

    def data_bazowa_szesciu_miesiecy(self) -> tuple:
        """Od kiedy liczyć „więcej niż 6 miesięcy”: ostatnia ocena albo, przy pierwszej, ustalenie kryteriów."""
        if self.poprzednia and self.poprzednia.data_sporzadzenia:
            return self.poprzednia.data_sporzadzenia, "sporządzenie ostatniej oceny"
        return (self.data_rozmowy_rozpoczynajacej or self.poczatek_okresu,
                "ustalenie kryteriów oceny sporządzanej po raz pierwszy")

    def ponad_szesc_miesiecy(self, na_dzien) -> bool:
        baza, _ = self.data_bazowa_szesciu_miesiecy()
        return bool(baza) and na_dzien > terminy.dodaj_miesiace(baza, 6)

    def _zdarzenie(self, kto, rodzaj, data, opis, podstawa, **dane):
        return ZdarzenieKadrowe.objects.create(ocena=self, kto=kto, rodzaj=rodzaj, data=data, opis=opis,
                                               podstawa=podstawa, dane=dane)

    def _powiadom(self, odbiorcy, tresc, klucz):
        for u in odbiorcy:
            Przypomnienie.objects.get_or_create(klucz=f"{klucz}:{u.pk}", defaults=dict(
                ocena=self, odbiorca=u, tresc=tresc, termin=self.termin_oceny, utworzone=zegar.dzis()))

    @transaction.atomic
    def zmien_oceniajacego(self, kto, nowy, data, powod: str = ""):
        if not kto.is_staff:
            raise PermissionDenied("Zmianę podległości wprowadza komórka kadrowa.")
        if self.sporzadzona or self.anulowana_powod:
            raise PermissionDenied("Ocena została już sporządzona.")
        if nowy.pk in (self.oceniany_id, self.oceniajacy_id):
            raise ValidationError({"nowy": "Wskaż innego oceniającego niż obecny i niż oceniany."})
        poprzedni = self.oceniajacy
        z = self._zdarzenie(kto, "zmiana_oceniajacego", data or zegar.dzis(),
                            f"Zmiana oceniającego: {poprzedni.get_full_name()} → {nowy.get_full_name()}. {powod}".strip(),
                            "§ 9 ust. 3 rozporządzenia (ocena według wcześniej wybranych kryteriów)",
                            poprzedni=poprzedni.pk, nowy=nowy.pk)
        self.oceniajacy = nowy
        self.save(update_fields=["oceniajacy"])
        self._powiadom([self.oceniany, nowy], f"Nowy oceniający: {nowy.get_full_name()}. Kryteria oceny bez zmian.",
                       f"zdarzenie:{z.pk}")
        return z

    @transaction.atomic
    def zmiana_stanowiska(self, kto, data_zmiany, nowe_stanowisko: str = "", rodzaj_stanowiska: str = ""):
        """UC-26: art. 81 ust. 6 albo § 9 ust. 1 — rozgałęzienie według progu sześciu miesięcy."""
        if not kto.is_staff:
            raise PermissionDenied("Zmianę stanowiska wprowadza komórka kadrowa.")
        if self.sporzadzona or self.anulowana_powod:
            raise PermissionDenied("Ocena została już sporządzona.")
        if not data_zmiany:
            raise ValidationError({"data_zmiany": "Podaj datę zmiany stanowiska."})
        baza, opis_bazy = self.data_bazowa_szesciu_miesiecy()
        pracownik = getattr(self.oceniany, "pracownik", None)
        dane = {}
        if pracownik and (nowe_stanowisko or rodzaj_stanowiska):
            pracownik.stanowisko = nowe_stanowisko or pracownik.stanowisko
            pracownik.rodzaj_stanowiska = rodzaj_stanowiska or pracownik.rodzaj_stanowiska
            pracownik.save()
        if self.ponad_szesc_miesiecy(data_zmiany):
            self.termin_oceny_zmieniony = terminy.termin_dniowy(data_zmiany, 30)
            self.najwczesniej_sporzadzenia = data_zmiany - timedelta(days=7)
            self.save(update_fields=["termin_oceny_zmieniony", "najwczesniej_sporzadzenia"])
            wariant = (f"od {opis_bazy} ({baza:%d.%m.%Y}) upłynęło więcej niż 6 miesięcy: ocenę sporządza się "
                       f"między {self.najwczesniej_sporzadzenia:%d.%m.%Y} a {self.termin_oceny_zmieniony:%d.%m.%Y}")
            podstawa = "art. 81 ust. 6 ustawy, § 9 ust. 2 rozporządzenia"
        else:
            # Ponowne czynności z §§ 5–6; termin oceny bez zmian. Dotychczasowe kryteria zostają w zdarzeniu.
            dane["poprzednie"] = {"kryteria_dodatkowe": self.kryteria_dodatkowe, "arkusz": self.arkusz}
            self.kryteria_zatwierdzone_at = self.kryteria_potwierdzone_at = None
            self.data_zatwierdzenia_kryteriow = self.data_potwierdzenia_kryteriow = None
            self.data_rozmowy_rozpoczynajacej = None
            if pracownik:
                self.arkusz = pracownik.arkusz
            if set(self.kryteria_dodatkowe) - rules.extra_criteria(self.arkusz, self.wersja_regul).keys():
                self.kryteria_dodatkowe = []
            self.termin_kryteriow_zmieniony = terminy.termin_dniowy(data_zmiany, 30)
            self.save()
            wariant = (f"w okresie 6 miesięcy od {opis_bazy} ({baza:%d.%m.%Y}): ponowne ustalenie kryteriów i rozmowa "
                       f"do {self.termin_kryteriow_zmieniony:%d.%m.%Y}, termin oceny bez zmian")
            podstawa = "§ 9 ust. 1 rozporządzenia"
        z = self._zdarzenie(kto, "zmiana_stanowiska", data_zmiany, f"Zmiana stanowiska {data_zmiany:%d.%m.%Y}; {wariant}",
                            podstawa, **dane)
        self._powiadom([self.oceniany, self.oceniajacy], f"Zmiana stanowiska: {wariant}.", f"zdarzenie:{z.pk}")
        return z

    PODSTAWY_ZMIANY_TERMINU = {
        "1": "zmiana na stanowisku oceniającego w trakcie okresu oceny (art. 81 ust. 8 pkt 1)",
        "2": "przewidywana dłuższa usprawiedliwiona nieobecność ocenianego (art. 81 ust. 8 pkt 2)",
        "3": "przewidywana dłuższa usprawiedliwiona nieobecność oceniającego (art. 81 ust. 8 pkt 3)",
        "4": "wniosek ocenianego o zmianę terminu (art. 81 ust. 8 pkt 4)",
    }

    @transaction.atomic
    def zmien_termin(self, kto, nowy_termin, podstawa: str, uzasadnienie: str = ""):
        if kto.id != self.oceniajacy_id:
            raise PermissionDenied("Termin oceny zmienia oceniający (art. 81 ust. 8).")
        if self.sporzadzona or self.anulowana_powod:
            raise PermissionDenied("Ocena została już sporządzona.")
        if podstawa not in self.PODSTAWY_ZMIANY_TERMINU:
            raise ValidationError({"podstawa": "Wskaż podstawę zmiany terminu z art. 81 ust. 8."})
        if not nowy_termin or nowy_termin <= zegar.dzis():
            raise ValidationError({"nowy_termin": "Nowy termin musi przypadać w przyszłości."})
        if podstawa == "4" and not self.ponad_szesc_miesiecy(zegar.dzis()):
            baza, opis = self.data_bazowa_szesciu_miesiecy()
            raise ValidationError({"podstawa": f"Wniosek ocenianego można uwzględnić, gdy od {opis} ({baza:%d.%m.%Y}) "
                                               "upłynęło więcej niż 6 miesięcy (art. 81 ust. 8 pkt 4)."})
        stary = self.termin_oceny
        self.termin_oceny_zmieniony = nowy_termin
        self.save(update_fields=["termin_oceny_zmieniony"])
        z = self._zdarzenie(kto, "zmiana_terminu", zegar.dzis(),
                            f"{self.PODSTAWY_ZMIANY_TERMINU[podstawa]}. {uzasadnienie}".strip(),
                            "art. 81 ust. 8 ustawy, § 8 rozporządzenia (zawiadomienie ocenianego)",
                            stary=stary.isoformat() if stary else None, nowy=nowy_termin.isoformat())
        self._powiadom([self.oceniany], f"Zmiana terminu oceny na {nowy_termin:%d.%m.%Y}. Zawiadomienie (§ 8) w sprawie.",
                       f"zdarzenie:{z.pk}")
        return z

    @property
    def sprzeciw_biezacy(self) -> "Sprzeciw | None":
        return self.sprzeciwy.filter(wersja=self.wersja).first()

    def zloz_sprzeciw(self, tresc: str) -> "Sprzeciw":
        if not self.zapoznany:
            raise PermissionDenied("Sprzeciw przysługuje od zapoznania z oceną.")
        if self.sprzeciw_biezacy:
            raise PermissionDenied("Sprzeciw od tej oceny został już złożony.")
        if zegar.dzis() > self.termin_sprzeciwu:
            raise PermissionDenied(f"Termin na sprzeciw upłynął {self.termin_sprzeciwu:%d.%m.%Y} (art. 83 ust. 1).")
        if not tresc.strip():
            raise ValidationError({"tresc": "Podaj treść sprzeciwu."})
        return Sprzeciw.objects.create(ocena=self, wersja=self.wersja, data_zlozenia=zegar.dzis(), tresc=tresc.strip())

    POLA_WERSJI = ("oceny_czastkowe", "data_rozmowy_oceniajacej", "okres_od", "okres_do", "uzasadnienie", "wnioski_iprz",
                   "data_sporzadzenia", "srednia", "poziom", "pozytywna", "data_zapoznania", "sposob_zapoznania",
                   "wniosek_stopien", "umotywowanie_wniosku")

    def _archiwizuj(self, powod: str):
        dane = {p: getattr(self, p) for p in self.POLA_WERSJI}
        dane = {k: (v.isoformat() if hasattr(v, "isoformat") else str(v) if isinstance(v, Decimal) else v) for k, v in dane.items()}
        WersjaOceny.objects.create(ocena=self, wersja=self.wersja, dane=dane, powod=powod, utworzona=zegar.dzis())

    @transaction.atomic
    def rozpatrz_sprzeciw(self, kto, decyzja: str, uzasadnienie: str, nowe_czastkowe: dict | None = None):
        """Decyzja dyrektora generalnego (art. 83 ust. 3-4)."""
        if not (getattr(kto, "pracownik", None) and kto.pracownik.dyrektor_generalny):
            raise PermissionDenied("Sprzeciw rozpatruje dyrektor generalny urzędu.")
        if kto.id in (self.oceniany_id, self.oceniajacy_id):
            raise PermissionDenied("Dyrektor generalny będący stroną oceny nie rozpatruje sprzeciwu w tej sprawie.")
        sprzeciw = self.sprzeciw_biezacy
        if not sprzeciw or sprzeciw.decyzja:
            raise PermissionDenied("Brak sprzeciwu oczekującego na rozpatrzenie.")
        if decyzja not in dict(Sprzeciw.DECYZJE):
            raise ValidationError({"decyzja": "Wybierz rozstrzygnięcie."})
        if not uzasadnienie.strip():
            raise ValidationError({"uzasadnienie": "Uzasadnij rozstrzygnięcie sprzeciwu."})
        if decyzja == "ponowne" and self.wersja > 1:
            raise ValidationError({"decyzja": "Ocenę można sporządzić po raz drugi tylko raz (art. 83 ust. 4)."})
        if decyzja == "zmiana":
            nowe_czastkowe = nowe_czastkowe or {}
            wynik = self.podglad_wyniku(nowe_czastkowe)
            if wynik is None:
                raise ValidationError({"czastkowe": "Przyznaj zmienione oceny cząstkowe za wszystkie kryteria."})
            self._archiwizuj(f"zmiana oceny po uwzględnieniu sprzeciwu z {sprzeciw.data_zlozenia:%d.%m.%Y}")
            self.oceny_czastkowe = {k: nowe_czastkowe[k] for k in self.wszystkie_kryteria()}
            self.srednia = (Decimal(wynik.srednia.numerator) / wynik.srednia.denominator).quantize(Decimal("0.01"), ROUND_HALF_UP)
            self.poziom, self.pozytywna = wynik.poziom_nazwa, wynik.pozytywna
            if not wynik.pozytywna and not self.uzasadnienie:
                self.uzasadnienie = uzasadnienie.strip()
            if not wynik.pozytywna:
                self.wniosek_stopien = "nie" if self.oceniany_urzednik else "nie_dotyczy"
                self.umotywowanie_wniosku = ""
            # Zmienioną ocenę oceniany poznaje ponownie (nowa data zapoznania); kolejny sprzeciw nie przysługuje.
            self.data_zapoznania, self.sposob_zapoznania = None, ""
            self.uwagi_zapoznania = self.miejscowosc_zapoznania = ""
            self.save()
        elif decyzja == "ponowne":
            self._archiwizuj(f"sporządzenie po raz drugi po uwzględnieniu sprzeciwu z {sprzeciw.data_zlozenia:%d.%m.%Y}")
            # Powrót do etapu „rozmowa oceniająca i dokonanie oceny”; część I i kryteria bez zmian.
            for pole in self.POLA_WERSJI:
                pole_modelu = self._meta.get_field(pole)
                setattr(self, pole, {} if pole == "oceny_czastkowe" else None if pole_modelu.null else "")
            self.sporzadzona_at = None
            self.uwagi_zapoznania = self.miejscowosc_zapoznania = ""
            self.wersja += 1
            self.save()
            # Kolejna sprawa liczona od uchylonej oceny traci podstawę: anulujemy ją (z historią i obserwacjami),
            # a scheduler założy nową po ponownym sporządzeniu.
            for nastepna in Ocena.objects.filter(poprzednia=self):
                nastepna.anulowana_powod = (f"Anulowana {zegar.dzis():%d.%m.%Y}: ocenę z {sprzeciw.data_zlozenia:%d.%m.%Y} "
                                            f"sporządza się po raz drugi (sprawa {self.pk}).")
                nastepna.poprzednia = None
                nastepna.save(update_fields=["anulowana_powod", "poprzednia"])
        sprzeciw.decyzja, sprzeciw.data_decyzji = decyzja, zegar.dzis()
        sprzeciw.uzasadnienie_decyzji, sprzeciw.rozpatrujacy = uzasadnienie.strip(), kto
        sprzeciw.save()
        return sprzeciw


class Korekta(models.Model):
    """Ślad zmiany pola po zablokowaniu (tryb korekty administratora)."""

    ocena = models.ForeignKey(Ocena, on_delete=models.CASCADE, related_name="korekty")
    kto = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kiedy = models.DateTimeField(auto_now_add=True)
    pole = models.CharField(max_length=60)
    przed = models.JSONField()
    po = models.JSONField()
    powod = models.TextField()

    class Meta:
        verbose_name_plural = "korekty"
        ordering = ["-kiedy"]


class Sprzeciw(models.Model):
    """Sprzeciw do dyrektora generalnego urzędu (art. 83). Jeden na każdą wersję oceny."""

    DECYZJE = [
        ("zmiana", "uwzględniony: zmiana oceny"),
        ("ponowne", "uwzględniony: sporządzenie oceny po raz drugi"),
        ("nieuwzgledniony", "nieuwzględniony"),
    ]
    ocena = models.ForeignKey(Ocena, on_delete=models.CASCADE, related_name="sprzeciwy")
    wersja = models.PositiveSmallIntegerField(default=1)
    data_zlozenia = models.DateField()
    tresc = models.TextField()
    decyzja = models.CharField(max_length=20, choices=DECYZJE, blank=True)
    data_decyzji = models.DateField(null=True, blank=True)
    uzasadnienie_decyzji = models.TextField(blank=True)
    rozpatrujacy = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "sprzeciwy"

    def _dni(self, klucz):
        return rules.load(self.ocena.wersja_regul)["terminy"][klucz]

    @property
    def termin_rozpatrzenia(self):
        return terminy.termin_dniowy(self.data_zlozenia, self._dni("rozpatrzenie_sprzeciwu_dni"))

    @property
    def termin_odwolania(self):
        """Art. 83 ust. 5: 14 dni od doręczenia decyzji o nieuwzględnieniu albo od upływu terminu rozpatrzenia."""
        dni = self._dni("odwolanie_do_sadu_dni")
        if self.decyzja == "nieuwzgledniony":
            return terminy.termin_dniowy(self.data_decyzji, dni)
        if not self.decyzja and zegar.dzis() > self.termin_rozpatrzenia:
            return terminy.termin_dniowy(self.termin_rozpatrzenia, dni)
        return None


class WersjaOceny(models.Model):
    """Zapis oceny sprzed zmiany lub ponownego sporządzenia po sprzeciwie (historia do akt)."""

    ocena = models.ForeignKey(Ocena, on_delete=models.CASCADE, related_name="wersje")
    wersja = models.PositiveSmallIntegerField()
    dane = models.JSONField()
    powod = models.CharField(max_length=200)
    utworzona = models.DateField()

    class Meta:
        verbose_name_plural = "wersje ocen"
        ordering = ["wersja"]


class ZegarDemo(models.Model):
    """Przesunięta data systemowa, działa tylko przy OKRES_DEMO=1. Jeden wiersz (pk=1)."""

    data = models.DateField(null=True, blank=True, help_text="Puste = data rzeczywista.")

    class Meta:
        verbose_name = verbose_name_plural = "zegar demo"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class Obserwacja(models.Model):
    """Datowana notatka z okresu oceny. Notatka przełożonego jest prywatna, dopóki jej nie udostępni;
    osiągnięcie zgłoszone przez ocenianego widzą obie strony."""

    ocena = models.ForeignKey(Ocena, on_delete=models.CASCADE, related_name="obserwacje")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data = models.DateField()
    kryterium = models.CharField(max_length=60, blank=True)
    tresc = models.TextField("co się wydarzyło")
    skutek = models.TextField("jaki był skutek", blank=True)
    udostepniona = models.BooleanField(default=False)
    utworzona_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "obserwacje"
        ordering = ["data", "pk"]

    @property
    def od_ocenianego(self) -> bool:
        return self.autor_id == self.ocena.oceniany_id

    def widoczna_dla(self, user) -> bool:
        # Tylko strony oceny; kadry i DG nie czytają notatek (statystyki są zbiorcze).
        if user.id == self.autor_id:
            return True
        return self.udostepniona and user.id in (self.ocena.oceniany_id, self.ocena.oceniajacy_id)

    def clean(self):
        if self.kryterium and self.kryterium not in self.ocena.wszystkie_kryteria():
            raise ValidationError({"kryterium": "Wybierz kryterium z tej oceny."})
        if self.data and self.ocena.poczatek_okresu and self.data < self.ocena.poczatek_okresu:
            raise ValidationError({"data": "Obserwacja sprzed początku okresu oceny."})
        if self.data and self.data > zegar.dzis():
            raise ValidationError({"data": "Obserwacja nie może mieć daty z przyszłości."})


class Przypomnienie(models.Model):
    """Powiadomienie od schedulera. Klucz zapobiega zdublowaniu przy ponownym uruchomieniu."""

    ocena = models.ForeignKey(Ocena, on_delete=models.CASCADE, related_name="przypomnienia")
    odbiorca = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="przypomnienia")
    klucz = models.CharField(max_length=120, unique=True)
    tresc = models.CharField(max_length=300)
    termin = models.DateField(null=True, blank=True)
    utworzone = models.DateField()
    przeczytane = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "przypomnienia"
        ordering = ["przeczytane", "termin"]


class ZdarzenieKadrowe(models.Model):
    """Zmiana oceniającego, stanowiska albo terminu: z podstawą prawną, do akt i do zawiadomień."""

    RODZAJE = [("zmiana_oceniajacego", "zmiana oceniającego"), ("zmiana_stanowiska", "zmiana stanowiska"),
               ("zmiana_terminu", "zmiana terminu oceny")]
    ocena = models.ForeignKey(Ocena, on_delete=models.CASCADE, related_name="zdarzenia_kadrowe")
    rodzaj = models.CharField(max_length=30, choices=RODZAJE)
    data = models.DateField()
    kto = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    opis = models.TextField()
    podstawa = models.CharField(max_length=200)
    dane = models.JSONField(default=dict)

    class Meta:
        verbose_name_plural = "zdarzenia kadrowe"
        ordering = ["data", "pk"]
