from functools import cache
from pathlib import Path

import yaml

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
DOMYSLNA_WERSJA = "2016-04-04"


@cache
def load(version: str = DOMYSLNA_WERSJA) -> dict:
    return yaml.safe_load((RULES_DIR / f"{version}.yaml").read_text(encoding="utf-8"))


def _slownik(lista: list[dict]) -> dict[str, str]:
    return {k: v for item in lista for k, v in item.items()}


def extra_criteria(version: str = DOMYSLNA_WERSJA) -> dict[str, str]:
    return _slownik(load(version)["kryteria_dodatkowe"]["wykaz"])


def mandatory_criteria(arkusz: str, version: str = DOMYSLNA_WERSJA) -> dict[str, str]:
    return _slownik(load(version)["arkusze"][arkusz])
