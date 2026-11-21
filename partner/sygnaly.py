"""Sygnały HR partnera: deterministyczne reguły z rules/hr_partner.yaml.

Każdy sygnał zawiera zdarzenia źródłowe, pytanie do rozmowy i proponowane działania. Nie ma punktacji ludzi,
predykcji ani automatycznych decyzji. Do formalnej oceny i raportów kadr sygnały nie trafiają.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from oceny import terminy, zegar
from oceny.models import Obserwacja

from . import reguly


@dataclass
class Sygnal:
    klucz: str
    rodzaj: str
    tytul: str
    pytanie: str
    obszar: str
    dzialania: list[tuple[str, str]]
    zrodla: list[str] = field(default_factory=list)
    obserwacja_id: int | None = None


def _dzialania(kody):
    katalog = reguly.dzialania()
    return [(k, katalog[k]["nazwa"]) for k in kody if k in katalog]


def _z_dziennika(pracownik, nazwa, cfg, dzis):
    od = dzis - timedelta(days=cfg["okno_dni"])
    zdarzenia = list(pracownik.zdarzenia_zadan.filter(rodzaj=cfg["zdarzenie"], data__gt=od, data__lte=dzis).order_by("data"))
    if len(zdarzenia) < cfg["prog"]:
        return None
    tytul = cfg["tytul"].format(n=len(zdarzenia), dni=cfg["okno_dni"], tygodnie=cfg["okno_dni"] // 7)
    # Klucz zależy od ostatniego zdarzenia, więc nowa seria zdarzeń to nowy sygnał.
    return Sygnal(f"{nazwa}:{zdarzenia[-1].pk}", nazwa, tytul, cfg["pytanie"], cfg["obszar"], _dzialania(cfg["dzialania"]),
                  [f"{z.data:%d.%m.%Y}: {z.opis}" for z in zdarzenia])


def _powrot(pracownik, cfg, dzis):
    okresy = terminy.scal_nieobecnosci([terminy.Okres(n.od, n.do) for n in pracownik.nieobecnosci.all()])
    for o in reversed(okresy):
        if o.do < dzis and (dzis - o.do).days <= cfg["okno_dni"] and o.dni >= cfg["min_dni_nieobecnosci"]:
            return Sygnal(f"powrot:{o.od:%Y%m%d}", "powrot_po_nieobecnosci", cfg["tytul"].format(dni_nieobecnosci=o.dni),
                          cfg["pytanie"], cfg["obszar"], _dzialania(cfg["dzialania"]),
                          [f"Nieobecność usprawiedliwiona {o.od:%d.%m.%Y}–{o.do:%d.%m.%Y} (bez przyczyny)"])
    return None


def _osiagniecia(pracownik, cfg, dzis):
    wynik = []
    graniczna = dzis - timedelta(days=cfg["dni_bez_reakcji"])
    zgloszone = Obserwacja.objects.filter(ocena__oceniany=pracownik.user, autor=pracownik.user, data__lte=dzis,
                                          docenienia__isnull=True).order_by("data")
    for o in zgloszone:
        if o.data <= graniczna:
            wynik.append(Sygnal(f"docenienie:{o.pk}", "osiagniecie_bez_docenienia", cfg["tytul"].format(data=f"{o.data:%d.%m.%Y}"),
                                cfg["pytanie"], cfg["obszar"], _dzialania(cfg["dzialania"]), [o.tresc], obserwacja_id=o.pk))
    return wynik


def dla_pracownika(pracownik) -> list[Sygnal]:
    dzis = zegar.dzis()
    cfg = reguly.sygnaly()
    wynik = [s for s in (
        _z_dziennika(pracownik, "zmiany_priorytetu", cfg["zmiany_priorytetu"], dzis),
        _z_dziennika(pracownik, "przyrost_zadan", cfg["przyrost_zadan"], dzis),
        _powrot(pracownik, cfg["powrot_po_nieobecnosci"], dzis),
    ) if s]
    wynik += _osiagniecia(pracownik, cfg["osiagniecie_bez_docenienia"], dzis)
    obsluzone = set(pracownik.uzgodnienia.values_list("sygnal", flat=True))
    return [s for s in wynik if s.klucz not in obsluzone]
