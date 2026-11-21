"""Wyliczenie poziomu i wyniku oceny (§ 11 ust. 1). Deterministyczne, sterowane pakietem reguł."""

from dataclasses import dataclass
from fractions import Fraction

from . import rules


@dataclass(frozen=True)
class Wynik:
    srednia: Fraction
    poziom_kod: str
    poziom_nazwa: str
    pozytywna: bool

    @property
    def srednia_wyswietlana(self) -> str:
        return f"{float(self.srednia):.2f}".replace(".", ",")


def oblicz(czastkowe: list[int], version: str = rules.DOMYSLNA_WERSJA) -> Wynik:
    cfg = rules.load(version)["punktacja"]
    if not czastkowe:
        raise ValueError("Brak ocen cząstkowych.")
    niedozwolone = set(czastkowe) - set(cfg["skala_czastkowa"])
    if niedozwolone:
        raise ValueError(f"Niedozwolone oceny cząstkowe: {sorted(niedozwolone)}.")
    # Ułamek zamiast float: progi porównujemy dokładnie, przed zaokrągleniem do wyświetlenia.
    srednia = Fraction(sum(czastkowe), len(czastkowe))
    poziom = next(p for p in cfg["poziomy"] if srednia <= p["do"])
    pozytywna = poziom["kod"] in cfg["poziomy_pozytywne"] and cfg["czastkowa_wykluczajaca"] not in czastkowe
    return Wynik(srednia, poziom["kod"], poziom["nazwa"], pozytywna)
