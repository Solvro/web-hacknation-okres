"""Pomoc dla testów opartych na seedzie demo.

Seed pokazuje urząd w dniu 21.11.2026: sprawy Jana i Piotra są w toku (część I za nimi). Testy obiegu
i terminów sprawdzają przebieg od etapu kryteriów na tych samych osobach, więc cofają ich sprawy do punktu wyjścia:
Jan od 16.03.2025 (przykład nieobecności z materiałów KPRM), Piotr od 02.12.2024.
"""

from datetime import date

from .models import Ocena

PUNKT_WYJSCIA = {
    "oceniany": (date(2025, 3, 16), "zatrudnienie"),
    "piotr": (date(2024, 12, 2), "poprzednia_ocena"),
}


def sprawa_od_kryteriow(user) -> Ocena:
    """Jedna sprawa osoby na etapie kryteriów. Sprawa Jana zostaje (z obserwacjami), czyścimy tylko część I;
    sprawy Piotra (zakończona i kolejna) zastępuje nowa sprawa z punktu wyjścia."""
    poczatek, podstawa = PUNKT_WYJSCIA[user.username]
    sprawy = Ocena.objects.filter(oceniany=user)
    istniejaca = sprawy.filter(poczatek_okresu=poczatek, data_sporzadzenia__isnull=True).first()
    if istniejaca:
        sprawy.exclude(pk=istniejaca.pk).delete()
        sprawy.filter(pk=istniejaca.pk).update(
            kryteria_dodatkowe=[], data_rozmowy_rozpoczynajacej=None, kryteria_zatwierdzone_at=None,
            data_zatwierdzenia_kryteriow=None, miejscowosc_czesc_i="", cele_i_oczekiwania="",
            kryteria_potwierdzone_at=None, data_potwierdzenia_kryteriow=None)
        return Ocena.objects.get(pk=istniejaca.pk)
    for o in sprawy.order_by("-pk"):  # kolejna sprawa wskazuje poprzednią (PROTECT), więc od najnowszej
        o.delete()
    p = user.pracownik
    return Ocena.objects.create(oceniany=user, oceniajacy=p.przelozony.user, poczatek_okresu=poczatek,
                                podstawa_poczatku=podstawa, arkusz=p.arkusz)
