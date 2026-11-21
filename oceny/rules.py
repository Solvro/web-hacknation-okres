"""Pakiety reguł prawnych (YAML, wersjonowane). Kod czyta reguły, nie zawiera ich na sztywno.

Pakiet może dziedziczyć po innym (`dziedziczy:`) i nadpisywać wybrane klucze; przykłady wejście → wynik
w sekcji `przyklady` sprawdza `manage.py sprawdz_reguly` przed aktywacją.
"""

from functools import cache
from pathlib import Path

import yaml

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
DOMYSLNA_WERSJA = "2016-04-04"
PLIKI_POMOCNICZE = {"hr_partner", "rozmowy", "rozwoj"}
WYMAGANE_KLUCZE = ("wersja", "obowiazuje_od", "kryteria", "arkusze", "kryteria_dodatkowe", "punktacja", "terminy", "przypomnienia")


def _scal(baza: dict, zmiany: dict) -> dict:
    wynik = dict(baza)
    for k, v in zmiany.items():
        wynik[k] = _scal(baza[k], v) if isinstance(v, dict) and isinstance(baza.get(k), dict) else v
    return wynik


@cache
def load(version: str = DOMYSLNA_WERSJA) -> dict:
    dane = yaml.safe_load((RULES_DIR / f"{version}.yaml").read_text(encoding="utf-8"))
    if rodzic := dane.get("dziedziczy"):
        dane = _scal(load(rodzic), {k: v for k, v in dane.items() if k != "dziedziczy"})
    return dane


def dostepne_wersje() -> list[dict]:
    wersje = []
    for plik in sorted(RULES_DIR.glob("*.yaml")):
        if plik.stem in PLIKI_POMOCNICZE:
            continue
        d = load(plik.stem)
        wersje.append({"kod": plik.stem, "nazwa": d.get("nazwa", plik.stem), "obowiazuje_od": d.get("obowiazuje_od"),
                       "symulacja": bool(d.get("symulacja"))})
    return wersje


def aktywna() -> str:
    from .models import Urzad

    urzad = Urzad.biezacy()
    return urzad.wersja_regul if urzad and urzad.wersja_regul else DOMYSLNA_WERSJA


def criteria(version: str = DOMYSLNA_WERSJA) -> dict[str, dict]:
    """Pełny wykaz kryteriów z Załącznika nr 1: {kod: {nazwa, opis}}."""
    return load(version)["kryteria"]


def mandatory_criteria(arkusz: str, version: str = DOMYSLNA_WERSJA) -> dict[str, str]:
    wykaz = criteria(version)
    return {k: wykaz[k]["nazwa"] for k in load(version)["arkusze"][arkusz]["obowiazkowe"]}


def extra_criteria(arkusz: str, version: str = DOMYSLNA_WERSJA) -> dict[str, str]:
    """Kryteria, które można wybrać jako dodatkowe: wykaz bez obowiązkowych danego arkusza."""
    obowiazkowe = load(version)["arkusze"][arkusz]["obowiazkowe"]
    return {k: v["nazwa"] for k, v in criteria(version).items() if k not in obowiazkowe}


@cache
def rozmowy() -> dict:
    return yaml.safe_load((RULES_DIR / "rozmowy.yaml").read_text(encoding="utf-8"))


def sprawdz(version: str) -> list[str]:
    """Walidacja pakietu: wymagane klucze, spójność kryteriów, przykłady wejście → wynik. Zwraca listę błędów."""
    from datetime import date

    from . import punktacja, terminy

    try:
        d = load(version)
    except (OSError, yaml.YAMLError) as e:
        return [f"Nie można wczytać pakietu: {e}"]
    bledy = [f"Brak klucza „{k}”." for k in WYMAGANE_KLUCZE if k not in d]
    if bledy:
        return bledy
    for arkusz, cfg in d["arkusze"].items():
        for kod in cfg["obowiazkowe"]:
            if kod not in d["kryteria"]:
                bledy.append(f"Arkusz {arkusz}: kryterium „{kod}” spoza wykazu.")
    poziomy = [p["do"] for p in d["punktacja"]["poziomy"]]
    if poziomy != sorted(poziomy) or poziomy[-1] < max(d["punktacja"]["skala_czastkowa"]):
        bledy.append("Progi poziomów muszą rosnąć i obejmować najwyższą ocenę cząstkową.")
    for i, p in enumerate(d.get("przyklady", [])):
        try:
            if "termin_oceny" in p:
                okresy = [terminy.Okres(date.fromisoformat(a), date.fromisoformat(b)) for a, b in p.get("nieobecnosci", [])]
                wynik = terminy.termin_oceny(date.fromisoformat(p["poczatek"]), okresy, version).isoformat()
                oczekiwane = p["termin_oceny"]
            elif "punkty" in p:
                w = punktacja.oblicz(p["punkty"], version)
                wynik, oczekiwane = [w.poziom_kod, w.pozytywna], [p["poziom"], p["pozytywna"]]
            else:
                bledy.append(f"Przykład {i + 1}: nieznany rodzaj.")
                continue
        except Exception as e:  # noqa: BLE001 - każdy błąd przykładu blokuje aktywację
            bledy.append(f"Przykład {i + 1}: błąd obliczenia ({e}).")
            continue
        if wynik != oczekiwane:
            bledy.append(f"Przykład {i + 1}: oczekiwano {oczekiwane}, wyszło {wynik}.")
    return bledy
