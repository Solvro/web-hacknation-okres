"""Liczenie terminów według zasad KPRM (materiały: „liczenie terminów”). Deterministyczne, bez AI."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache

import holidays

from . import rules


@cache
def _swieta(rok: int) -> holidays.HolidayBase:
    return holidays.Poland(years=rok)


def dzien_wolny(d: date) -> bool:
    """Sobota, niedziela albo święto ustawowe."""
    return d.weekday() >= 5 or d in _swieta(d.year)


def dodaj_miesiace(d: date, n: int) -> date:
    """Dzień odpowiadający początkowemu; gdy go brak, ostatni dzień miesiąca."""
    m = d.month - 1 + n
    rok, miesiac = d.year + m // 12, m % 12 + 1
    return date(rok, miesiac, min(d.day, calendar.monthrange(rok, miesiac)[1]))


def przesun_na_roboczy(d: date) -> date:
    while dzien_wolny(d):
        d += timedelta(days=1)
    return d


def termin_miesieczny(poczatek: date, miesiace: int) -> date:
    return przesun_na_roboczy(dodaj_miesiace(poczatek, miesiace))


def termin_dniowy(zdarzenie: date, dni: int) -> date:
    """Dnia zdarzenia nie liczy się; koniec w dzień wolny przesuwa się na roboczy."""
    return przesun_na_roboczy(zdarzenie + timedelta(days=dni))


@dataclass(frozen=True)
class Okres:
    od: date
    do: date  # włącznie

    @property
    def dni(self) -> int:
        return (self.do - self.od).days + 1


def scal_nieobecnosci(okresy: list[Okres]) -> list[Okres]:
    """Okresy następujące po sobie łączą się, jeśli dzielą je wyłącznie dni wolne od pracy."""
    scalone: list[Okres] = []
    for o in sorted(okresy, key=lambda o: o.od):
        if scalone:
            ost = scalone[-1]
            przerwa = (ost.do + timedelta(days=n) for n in range(1, (o.od - ost.do).days))
            if o.od <= ost.do + timedelta(days=1) or all(dzien_wolny(d) for d in przerwa):
                scalone[-1] = Okres(ost.od, max(ost.do, o.do))
                continue
        scalone.append(o)
    return scalone


def dluzsza_niz(okres: Okres, miesiace: int) -> bool:
    # Okres od 5.10 do 4.11 trwa dokładnie miesiąc; dłuższy zaczyna się od 5.11.
    return okres.do >= dodaj_miesiace(okres.od, miesiace)


@dataclass(frozen=True)
class Krok:
    opis: str
    data: date
    podstawa: str = ""


@dataclass(frozen=True)
class Rachunek:
    """Termin razem z krokami obliczenia, do pokazania kadrom („Jak obliczono termin?”)."""

    termin: date
    kroki: tuple[Krok, ...]


def _z_przesunieciem(kroki: list[Krok], koniec: date) -> Rachunek:
    roboczy = przesun_na_roboczy(koniec)
    if roboczy != koniec:
        kroki.append(Krok(f"{koniec:%d.%m.%Y} to dzień wolny od pracy, termin przesuwa się na najbliższy dzień roboczy", roboczy,
                          "zasady liczenia terminów KPRM"))
    return Rachunek(roboczy, tuple(kroki))


def rachunek_terminu_oceny(poczatek: date, nieobecnosci: list[Okres] = (), version: str = rules.DOMYSLNA_WERSJA,
                           opis_poczatku: str = "Początek okresu oceny") -> Rachunek:
    """Termin oceny okresowej z przedłużeniem o długotrwałe nieobecności (art. 81 ust. 1 i 7)."""
    cfg = rules.load(version)["terminy"]
    miesiace = cfg["okres_oceny_miesiace"]
    koniec = dodaj_miesiace(poczatek, miesiace)
    kroki = [Krok(opis_poczatku, poczatek), Krok(f"+ {miesiace} miesięcy", koniec, "art. 81 ust. 1 ustawy")]
    prog = cfg["nieobecnosc_przedluza_powyzej_miesiecy"]
    # Liczy się tylko część nieobecności przypadająca w okresie oceny.
    przyciete = [Okres(max(o.od, poczatek), o.do) for o in nieobecnosci if o.do >= poczatek]
    for o in scal_nieobecnosci(przyciete):
        if o.od > koniec:
            continue
        if dluzsza_niz(o, prog):
            koniec += timedelta(days=o.dni)
            kroki.append(Krok(f"+ {o.dni} dni ciągłej nieobecności usprawiedliwionej {o.od:%d.%m.%Y}–{o.do:%d.%m.%Y} "
                              f"(dłuższej niż {prog} mies.)", koniec, "art. 81 ust. 7 ustawy"))
        else:
            kroki.append(Krok(f"Nieobecność {o.od:%d.%m.%Y}–{o.do:%d.%m.%Y} ({o.dni} dni) nie przekracza {prog} mies., "
                              "termin bez zmian", koniec, "art. 81 ust. 7 ustawy"))
    return _z_przesunieciem(kroki, koniec)


def rachunek_dniowy(zdarzenie: date, dni: int, opis_zdarzenia: str, podstawa: str) -> Rachunek:
    koniec = zdarzenie + timedelta(days=dni)
    return _z_przesunieciem([Krok(opis_zdarzenia, zdarzenie), Krok(f"+ {dni} dni (bez dnia zdarzenia)", koniec, podstawa)], koniec)


def rachunek_miesieczny(poczatek: date, miesiace: int, opis_poczatku: str, podstawa: str) -> Rachunek:
    koniec = dodaj_miesiace(poczatek, miesiace)
    return _z_przesunieciem([Krok(opis_poczatku, poczatek), Krok(f"+ {miesiace} miesięcy", koniec, podstawa)], koniec)


def termin_oceny(poczatek: date, nieobecnosci: list[Okres] = (), version: str = rules.DOMYSLNA_WERSJA) -> date:
    return rachunek_terminu_oceny(poczatek, nieobecnosci, version).termin
