"""Scheduler procesu oceny: przypomnienia o terminach i zakładanie kolejnych spraw.

Uruchamiany cyklicznie (`manage.py scheduler`) albo z panelu w trybie demo. Funkcje są idempotentne:
ponowne uruchomienie tego samego dnia nie tworzy duplikatów ani nie dolicza nieobecności drugi raz,
bo terminy są zawsze liczone od nowa z danych źródłowych.
"""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction

from . import rules, zegar
from .models import Ocena, Przypomnienie


def _przypomnij(ocena, odbiorca, rodzaj: str, termin, tresc: str, dni_przed: int) -> bool:
    klucz = f"{ocena.pk}:{rodzaj}:{termin:%Y%m%d}:{dni_przed}:{odbiorca.pk}"
    try:
        with transaction.atomic():
            Przypomnienie.objects.create(ocena=ocena, odbiorca=odbiorca, klucz=klucz, tresc=tresc, termin=termin,
                                         utworzone=zegar.dzis())
    except IntegrityError:
        return False
    if getattr(settings, "OKRES_POWIADOMIENIA_EMAIL", False) and odbiorca.email:
        # Bez danych kadrowych w temacie; szczegóły po zalogowaniu.
        send_mail("OKRES: przypomnienie o terminie", f"{tresc}\nTermin: {termin:%d.%m.%Y}", None, [odbiorca.email],
                  fail_silently=True)
    return True


def _progi(ocena, rodzaj):
    return rules.load(ocena.wersja_regul)["przypomnienia"][rodzaj]


def przypomnienia_dla(ocena) -> int:
    dzis = zegar.dzis()
    utworzone = 0
    etap = ocena.etap
    if etap == "kryteria":
        r = ocena.rachunek_kryteriow()
        kto = ocena.oceniany if ocena.kryteria_zatwierdzone else ocena.oceniajacy
        rodzaj, termin, opis = "kryteria", r and r.termin, "Wyznaczenie kryteriów i rozmowa (§ 7)"
    elif etap == "ocena":
        kto, rodzaj, termin, opis = ocena.oceniajacy, "ocena", ocena.termin_oceny, "Sporządzenie oceny okresowej"
    elif etap == "termin_sprzeciwu":
        kto, rodzaj, termin, opis = ocena.oceniany, "sprzeciw", ocena.termin_sprzeciwu, "Upływ terminu na sprzeciw (art. 83 ust. 1)"
    else:
        return 0
    if not termin:
        return 0
    for dni in _progi(ocena, rodzaj):
        if dzis >= termin - timedelta(days=dni):
            napis = f"{opis}: {ocena.oceniany.get_full_name()} — termin {termin:%d.%m.%Y}"
            if dzis > termin:
                napis += " (PO TERMINIE)"
            utworzone += _przypomnij(ocena, kto, rodzaj, termin, napis, dni)
    return utworzone


def zaloz_kolejna(ocena) -> Ocena | None:
    """UC-01 / UC-27: po sporządzeniu oceny zakłada kolejny okres oceny. Od razu, bo po ocenie negatywnej
    kryteria wyznacza się w 7 dni od sporządzenia (§ 7 ust. 2), a więc jeszcze w trakcie terminu na sprzeciw."""
    if not ocena.sporzadzona or Ocena.objects.filter(poprzednia=ocena).exists():
        return None
    pracownik = getattr(ocena.oceniany, "pracownik", None)
    oceniajacy = pracownik.przelozony.user if pracownik and pracownik.przelozony else ocena.oceniajacy
    return Ocena.objects.create(oceniany=ocena.oceniany, oceniajacy=oceniajacy, poprzednia=ocena,
                                poczatek_okresu=ocena.data_sporzadzenia, podstawa_poczatku="poprzednia_ocena",
                                arkusz=pracownik.arkusz if pracownik else ocena.arkusz)


def uruchom() -> dict:
    wynik = {"przypomnienia": 0, "nowe_sprawy": 0}
    for ocena in Ocena.objects.select_related("oceniany", "oceniajacy"):
        wynik["przypomnienia"] += przypomnienia_dla(ocena)
        if zaloz_kolejna(ocena):
            wynik["nowe_sprawy"] += 1
    return wynik
