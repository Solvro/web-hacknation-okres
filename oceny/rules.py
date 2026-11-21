from functools import cache
from pathlib import Path

import yaml

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
DOMYSLNA_WERSJA = "2016-04-04"


@cache
def load(version: str = DOMYSLNA_WERSJA) -> dict:
    return yaml.safe_load((RULES_DIR / f"{version}.yaml").read_text(encoding="utf-8"))


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
