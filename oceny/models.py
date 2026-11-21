from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from . import punktacja, rules


class Ocena(models.Model):
    arkusz = models.CharField(max_length=1, choices=[("A", "A"), ("B", "B"), ("C", "C")])
    wersja_regul = models.CharField(max_length=20, default=rules.DOMYSLNA_WERSJA)
    oceniany = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="oceny_wlasne")
    oceniajacy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="oceny_sporzadzane")
    kryteria_dodatkowe = models.JSONField(default=list, blank=True)
    kryteria_potwierdzone_at = models.DateTimeField(null=True, blank=True)

    # Część II arkusza: {kod kryterium: punkty}
    oceny_czastkowe = models.JSONField(default=dict, blank=True)
    data_rozmowy_oceniajacej = models.DateField(null=True, blank=True)
    uzasadnienie = models.TextField(blank=True)
    wnioski_iprz = models.TextField(blank=True)
    sporzadzona_at = models.DateTimeField(null=True, blank=True)
    srednia = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    poziom = models.CharField(max_length=40, blank=True)
    pozytywna = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "oceny"

    def __str__(self):
        return f"Ocena {self.pk} · arkusz {self.arkusz} · {self.oceniany}"

    @property
    def kryteria_zablokowane(self) -> bool:
        return self.kryteria_potwierdzone_at is not None

    @property
    def sporzadzona(self) -> bool:
        return self.sporzadzona_at is not None

    def wszystkie_kryteria(self) -> dict[str, str]:
        """Obowiązkowe z arkusza, potem wybrane dodatkowe, w kolejności ze wzoru."""
        dodatkowe = rules.extra_criteria(self.wersja_regul)
        return rules.mandatory_criteria(self.arkusz, self.wersja_regul) | {k: dodatkowe[k] for k in self.kryteria_dodatkowe}

    def clean(self):
        cfg = rules.load(self.wersja_regul)["kryteria_dodatkowe"]
        wybrane = self.kryteria_dodatkowe
        if len(wybrane) > cfg["max"]:
            raise ValidationError(f"Można wybrać maksymalnie {cfg['max']} kryteria dodatkowe.")
        if len(set(wybrane)) != len(wybrane):
            raise ValidationError("Kryteria dodatkowe nie mogą się powtarzać.")
        nieznane = set(wybrane) - rules.extra_criteria(self.wersja_regul).keys()
        if nieznane:
            raise ValidationError(f"Kryteria spoza wykazu: {', '.join(sorted(nieznane))}.")

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
        if self.kryteria_zablokowane:
            if korekta_przez is None:
                raise PermissionDenied("Kryteria potwierdzone przez ocenianego; zmiana tylko w trybie korekty administratora.")
            self._zapisz_korekte(korekta_przez, "kryteria_dodatkowe", przed, list(kody), powod)
        self.kryteria_dodatkowe = list(kody)
        self.full_clean()
        self.save()

    def potwierdz_kryteria(self):
        if self.kryteria_zablokowane:
            raise PermissionDenied("Kryteria zostały już potwierdzone.")
        self.kryteria_potwierdzone_at = timezone.now()
        self.save(update_fields=["kryteria_potwierdzone_at"])

    def podglad_wyniku(self, czastkowe: dict[str, int]) -> punktacja.Wynik | None:
        """Wynik dla kompletu ocen cząstkowych, inaczej None (podgląd nie zgaduje brakujących)."""
        if set(czastkowe) != set(self.wszystkie_kryteria()):
            return None
        try:
            return punktacja.oblicz(list(czastkowe.values()), self.wersja_regul)
        except ValueError:
            return None

    def bledy_formalne(self, czastkowe, data_rozmowy, uzasadnienie, wnioski) -> dict[str, str]:
        """Strażnik formalny przed sporządzeniem oceny (§§ 10-11). Zwraca {pole: komunikat}."""
        cfg = rules.load(self.wersja_regul)["punktacja"]
        bledy = {}
        if not self.kryteria_zablokowane:
            bledy["kryteria"] = "Oceniany nie potwierdził jeszcze kryteriów (§ 7)."
        skala = set(cfg["skala_czastkowa"])
        for kod, nazwa in self.wszystkie_kryteria().items():
            if czastkowe.get(kod) not in skala:
                bledy[f"kryterium_{kod}"] = f"Przyznaj ocenę cząstkową za kryterium „{nazwa}” (§ 11 ust. 1 pkt 1)."
        if data_rozmowy is None:
            bledy["data_rozmowy"] = "Podaj datę rozmowy oceniającej (§ 10)."
        elif data_rozmowy > timezone.localdate():
            bledy["data_rozmowy"] = "Rozmowa oceniająca musi odbyć się przed sporządzeniem oceny lub tego samego dnia (§ 10)."
        wynik = self.podglad_wyniku(czastkowe)
        if wynik and not wynik.pozytywna and not uzasadnienie.strip():
            bledy["uzasadnienie"] = "Uzupełnij uzasadnienie oceny negatywnej (§ 11 ust. 3)."
        if cfg["wnioski_iprz_obowiazkowe"] and not wnioski.strip():
            bledy["wnioski_iprz"] = "Wpisz wnioski do indywidualnego programu rozwoju zawodowego (§ 11 ust. 1 pkt 5)."
        return bledy

    @transaction.atomic
    def sporzadz(self, czastkowe: dict[str, int], data_rozmowy, uzasadnienie: str, wnioski: str):
        if self.sporzadzona:
            raise PermissionDenied("Ocena została już sporządzona.")
        bledy = self.bledy_formalne(czastkowe, data_rozmowy, uzasadnienie, wnioski)
        if bledy:
            raise ValidationError(bledy)
        wynik = self.podglad_wyniku(czastkowe)
        self.oceny_czastkowe = {k: czastkowe[k] for k in self.wszystkie_kryteria()}
        self.data_rozmowy_oceniajacej = data_rozmowy
        self.uzasadnienie = uzasadnienie.strip()
        self.wnioski_iprz = wnioski.strip()
        self.srednia = (Decimal(wynik.srednia.numerator) / wynik.srednia.denominator).quantize(Decimal("0.01"), ROUND_HALF_UP)
        self.poziom = wynik.poziom_nazwa
        self.pozytywna = wynik.pozytywna
        self.sporzadzona_at = timezone.now()
        self.save()


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
