from functools import cache

import yaml

from oceny.rules import RULES_DIR


@cache
def load() -> dict:
    return yaml.safe_load((RULES_DIR / "hr_partner.yaml").read_text(encoding="utf-8"))


def sygnaly() -> dict:
    return load()["sygnaly"]


def dzialania() -> dict:
    return load()["dzialania"]


def rodzaje_zdarzen() -> dict:
    return load()["rodzaje_zdarzen"]
