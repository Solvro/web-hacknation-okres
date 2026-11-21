"""Część rozwojowa oceny: podpowiedzi do wniosków IPRZ i wskazówki dotyczące mocnych stron (rules/rozwoj.yaml).

Deterministyczne, bez AI. System niczego nie wpisuje do arkusza: oceniający może jednym kliknięciem wstawić
propozycję do pola wniosków jako punkt wyjścia, a potem sam ją przeredagowuje.
"""

from functools import cache

import yaml

from .rules import RULES_DIR


@cache
def katalog() -> dict:
    return yaml.safe_load((RULES_DIR / "rozwoj.yaml").read_text(encoding="utf-8"))


def sprawdz(dane: dict | None = None, kryteria: dict | None = None) -> list[str]:
    """Walidacja katalogu: każde kryterium z wykazu ma 2–3 działania o dozwolonej formie i wskazówkę „mocna strona”."""
    from . import rules

    dane = katalog() if dane is None else dane
    bledy = [f"Brak klucza „{k}”." for k in ("wersja", "pakiet_kryteriow", "formy", "kryteria",
                                              "obszar_do_rozwoju_przy", "mocna_strona_przy") if k not in dane]
    if bledy:
        return bledy
    if kryteria is None:
        kryteria = rules.criteria(dane["pakiet_kryteriow"])
    skala = set(rules.load(dane["pakiet_kryteriow"])["punktacja"]["skala_czastkowa"])
    for klucz in ("obszar_do_rozwoju_przy", "mocna_strona_przy"):
        if not set(dane[klucz]) <= skala:
            bledy.append(f"„{klucz}”: wartości spoza skali ocen cząstkowych {sorted(skala)}.")
    for kod in kryteria:
        if kod not in dane["kryteria"]:
            bledy.append(f"Brak podpowiedzi dla kryterium „{kod}”.")
    for kod, cfg in dane["kryteria"].items():
        if kod not in kryteria:
            bledy.append(f"Kryterium „{kod}” spoza wykazu.")
            continue
        dzialania = (cfg or {}).get("dzialania") or []
        if not 2 <= len(dzialania) <= 3:
            bledy.append(f"„{kod}”: wymagane 2–3 działania rozwojowe, jest {len(dzialania)}.")
        for d in dzialania:
            if not isinstance(d, dict) or d.get("forma") not in dane["formy"] or not str(d.get("opis", "")).strip():
                bledy.append(f"„{kod}”: działanie bez opisu albo z formą spoza listy {sorted(dane['formy'])}.")
        if not str((cfg or {}).get("mocna_strona", "")).strip():
            bledy.append(f"„{kod}”: brak wskazówki „mocna_strona”.")
    return bledy


def podpowiedzi(kryteria: dict[str, str], czastkowe: dict[str, int]) -> list[dict]:
    """Dla kryteriów z oceną 1/3: propozycje do IPRZ; dla 7/9: jak wykorzystać mocną stronę. Kolejność jak w arkuszu."""
    dane = katalog()
    formy = dane["formy"]
    wynik = []
    for kod, nazwa in kryteria.items():
        pkt, cfg = czastkowe.get(kod), dane["kryteria"].get(kod)
        if pkt is None or not cfg:
            continue
        if pkt in dane["obszar_do_rozwoju_przy"]:
            wynik.append({"kod": kod, "nazwa": nazwa, "punkty": pkt, "rodzaj": "rozwoj", "dzialania": [
                {"forma": formy[d["forma"]], "opis": d["opis"], "do_iprz": f"{nazwa}: {formy[d['forma']]}. {d['opis']}"}
                for d in cfg["dzialania"]]})
        elif pkt in dane["mocna_strona_przy"]:
            wynik.append({"kod": kod, "nazwa": nazwa, "punkty": pkt, "rodzaj": "mocna", "wskazowka": cfg["mocna_strona"]})
    return wynik
