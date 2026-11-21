from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models

from oceny import zegar
from oceny.models import Pracownik

from . import reguly


def _jest_przelozonym(user, pracownik: Pracownik) -> bool:
    p = getattr(user, "pracownik", None)
    return bool(p and pracownik.przelozony_id == p.pk)


class ZdarzenieZadania(models.Model):
    """Wpis w dzienniku zadań: fakt organizacyjny, widoczny dla pracownika, którego dotyczy."""

    pracownik = models.ForeignKey(Pracownik, on_delete=models.CASCADE, related_name="zdarzenia_zadan")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data = models.DateField()
    rodzaj = models.CharField(max_length=30)
    opis = models.CharField(max_length=300)

    class Meta:
        verbose_name = "zdarzenie w dzienniku zadań"
        verbose_name_plural = "dziennik zadań"
        ordering = ["-data", "-pk"]

    @property
    def rodzaj_nazwa(self) -> str:
        return reguly.rodzaje_zdarzen().get(self.rodzaj, self.rodzaj)

    def clean(self):
        if self.rodzaj not in reguly.rodzaje_zdarzen():
            raise ValidationError({"rodzaj": "Nieznany rodzaj zdarzenia."})
        if self.data and self.data > zegar.dzis():
            raise ValidationError({"data": "Zdarzenie nie może mieć daty z przyszłości."})

    @classmethod
    def dodaj(cls, autor, pracownik, data, rodzaj, opis):
        if not _jest_przelozonym(autor, pracownik):
            raise PermissionDenied("Dziennik zadań prowadzi bezpośredni przełożony.")
        if not opis.strip():
            raise ValidationError({"opis": "Opisz zadanie lub zmianę."})
        z = cls(pracownik=pracownik, autor=autor, data=data or zegar.dzis(), rodzaj=rodzaj, opis=opis.strip())
        z.full_clean()
        z.save()
        return z


class Uzgodnienie(models.Model):
    """Działanie uzgodnione w rozmowie po sygnale. Pracownik widzi je i może dopisać swoją perspektywę."""

    WYNIKI = [("pomoglo", "pomogło"), ("czesciowo", "częściowo"), ("nie_pomoglo", "nie pomogło")]
    pracownik = models.ForeignKey(Pracownik, on_delete=models.CASCADE, related_name="uzgodnienia")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    sygnal = models.CharField(max_length=100, help_text="Klucz sygnału, który był powodem rozmowy.")
    dzialanie = models.CharField(max_length=40)
    ustalenie = models.TextField()
    data = models.DateField()
    data_sprawdzenia = models.DateField()
    perspektywa_pracownika = models.TextField(blank=True)
    wynik = models.CharField(max_length=20, choices=WYNIKI, blank=True)
    notatka_z_wyniku = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "uzgodnienia"
        ordering = ["-data", "-pk"]

    @property
    def dzialanie_nazwa(self) -> str:
        return reguly.dzialania().get(self.dzialanie, {}).get("nazwa", self.dzialanie)

    def clean(self):
        if self.dzialanie not in reguly.dzialania():
            raise ValidationError({"dzialanie": "Wybierz działanie z katalogu."})
        if self.data_sprawdzenia and self.data and self.data_sprawdzenia < self.data:
            raise ValidationError({"data_sprawdzenia": "Sprawdzenie efektu nie może poprzedzać uzgodnienia."})

    @classmethod
    def zapisz(cls, autor, pracownik, sygnal, dzialanie, ustalenie, data_sprawdzenia):
        if not _jest_przelozonym(autor, pracownik):
            raise PermissionDenied("Uzgodnienie zapisuje bezpośredni przełożony.")
        if not ustalenie.strip():
            raise ValidationError({"ustalenie": "Opisz, co ustaliliście."})
        if not data_sprawdzenia:
            raise ValidationError({"data_sprawdzenia": "Podaj datę sprawdzenia efektu."})
        u = cls(pracownik=pracownik, autor=autor, sygnal=sygnal, dzialanie=dzialanie, ustalenie=ustalenie.strip(),
                data=zegar.dzis(), data_sprawdzenia=data_sprawdzenia)
        u.full_clean()
        u.save()
        return u

    def dopisz_perspektywe(self, user, tekst: str):
        if user.id != self.pracownik.user_id:
            raise PermissionDenied("Perspektywę dopisuje pracownik, którego dotyczy uzgodnienie.")
        self.perspektywa_pracownika = tekst.strip()
        self.save(update_fields=["perspektywa_pracownika"])

    def zapisz_wynik(self, user, wynik: str, notatka: str = ""):
        if not _jest_przelozonym(user, self.pracownik):
            raise PermissionDenied("Wynik zapisuje przełożony.")
        if wynik not in dict(self.WYNIKI):
            raise ValidationError({"wynik": "Wybierz wynik."})
        self.wynik, self.notatka_z_wyniku = wynik, notatka.strip()
        self.save(update_fields=["wynik", "notatka_z_wyniku"])


class Docenienie(models.Model):
    """Konkretne docenienie od przełożonego, widoczne dla pracownika."""

    pracownik = models.ForeignKey(Pracownik, on_delete=models.CASCADE, related_name="docenienia")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data = models.DateField()
    za_co = models.TextField()
    skutek = models.TextField(blank=True)
    obserwacja = models.ForeignKey("oceny.Obserwacja", null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="docenienia")

    class Meta:
        verbose_name_plural = "docenienia"
        ordering = ["-data", "-pk"]

    @classmethod
    def dodaj(cls, autor, pracownik, za_co, skutek="", obserwacja=None):
        if not _jest_przelozonym(autor, pracownik):
            raise PermissionDenied("Docenia bezpośredni przełożony.")
        if not za_co.strip():
            raise ValidationError({"za_co": "Napisz, za co doceniasz."})
        if obserwacja and obserwacja.ocena.oceniany_id != pracownik.user_id:
            raise PermissionDenied("Osiągnięcie dotyczy innej osoby.")
        return cls.objects.create(pracownik=pracownik, autor=autor, data=zegar.dzis(), za_co=za_co.strip(),
                                  skutek=skutek.strip(), obserwacja=obserwacja)
