"""Pomoc w porządkowaniu obserwacji przed sporządzeniem oceny. Nie pisze oceny za przełożonego.

Tryby (OKRES_AI): „wylaczone” (domyślnie, deterministyczne zestawienie notatek), „ollama” (model lokalny w sieci urzędu).
Każde zdanie z modelu musi wskazywać istniejące notatki źródłowe; zdania bez źródła są odrzucane.
Przed wysłaniem do modelu imiona i nazwiska stron zastępujemy tokenami (pseudonimizacja).
"""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings

from . import rules


@dataclass
class Punkt:
    tekst: str
    zrodla: list[int]
    ai: bool = False


@dataclass
class Zestawienie:
    tryb: str  # "ai" | "bez_ai"
    komunikat: str
    kryteria: list[dict] = field(default_factory=list)


def _deterministyczne(ocena, user, komunikat) -> Zestawienie:
    grupy = []
    for kod, nazwa, obs in ocena.obserwacje_wg_kryteriow(user):
        punkty = [Punkt(f"{o.data:%d.%m.%Y}: {o.tresc}" + (f" Skutek: {o.skutek}" if o.skutek else ""), [o.pk]) for o in obs]
        grupy.append({"kod": kod, "nazwa": nazwa, "punkty": punkty})
    return Zestawienie("bez_ai", komunikat, grupy)


def _pseudonimizuj(tekst: str, mapa: dict[str, str]) -> str:
    for jawne, token in mapa.items():
        tekst = re.sub(re.escape(jawne), token, tekst, flags=re.IGNORECASE)
    return tekst


def _mapa_pseudonimow(ocena) -> dict[str, str]:
    mapa = {}
    for user, token in ((ocena.oceniany, "[OCENIANY]"), (ocena.oceniajacy, "[OCENIAJĄCY]")):
        for czesc in (user.get_full_name(), user.first_name, user.last_name):
            if czesc and len(czesc) > 2:
                mapa[czesc] = token
    return dict(sorted(mapa.items(), key=lambda x: -len(x[0])))


def _zapytaj_ollama(prompt: str) -> str:
    dane = json.dumps({"model": settings.OKRES_AI_MODEL, "stream": False, "format": "json",
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{settings.OKRES_OLLAMA_URL}/api/chat", data=dane,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=settings.OKRES_AI_TIMEOUT) as odp:  # noqa: S310 - adres z konfiguracji urzędu
        return json.loads(odp.read())["message"]["content"]


def zestaw(ocena, user) -> Zestawienie:
    widoczne = {o.pk: o for o in ocena.obserwacje_dla(user)}
    if settings.OKRES_AI != "ollama":
        return _deterministyczne(ocena, user, "Zestawienie notatek bez AI (asystent AI wyłączony w konfiguracji urzędu).")
    if not widoczne:
        return _deterministyczne(ocena, user, "Brak notatek do uporządkowania.")
    mapa = _mapa_pseudonimow(ocena)
    kryteria = ocena.wszystkie_kryteria()
    notatki = "\n".join(f"[N{o.pk}] ({kryteria.get(o.kryterium, 'bez kryterium')}, {o.data:%Y-%m-%d}) "
                        f"{_pseudonimizuj(o.tresc, mapa)} Skutek: {_pseudonimizuj(o.skutek, mapa) or '-'}"
                        for o in widoczne.values())
    prompt = (
        "Jesteś asystentem porządkującym notatki przełożonego przed oceną okresową w służbie cywilnej. "
        "Nie oceniasz, nie proponujesz punktów i nie piszesz uzasadnienia. Dla każdego kryterium z listy streść "
        "fakty z notatek w 1–3 krótkich zdaniach. Każde zdanie MUSI wskazywać identyfikatory notatek, z których "
        "wynika (np. [12]). Nie dodawaj faktów spoza notatek. Gdy brak notatek do kryterium, zwróć pustą listę.\n"
        f"Kryteria: {json.dumps(kryteria, ensure_ascii=False)}\nNotatki:\n{notatki}\n"
        'Odpowiedz JSON: {"kryteria": {"<kod>": [{"zdanie": "...", "zrodla": [12]}]}}'
    )
    try:
        wynik = json.loads(_zapytaj_ollama(prompt))
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError):
        return _deterministyczne(ocena, user, "Model lokalny niedostępny: pokazuję zestawienie notatek bez AI.")
    odwrotna = {}
    for jawne, token in mapa.items():
        odwrotna.setdefault(token, jawne)
    grupy, odrzucone = [], 0
    for kod, nazwa in kryteria.items():
        punkty = []
        for p in (wynik.get("kryteria") or {}).get(kod, []) if isinstance(wynik, dict) else []:
            zrodla = [int(z) for z in p.get("zrodla", []) if str(z).isdigit() and int(z) in widoczne]
            if not zrodla or not str(p.get("zdanie", "")).strip():
                odrzucone += 1
                continue
            tekst = str(p["zdanie"])
            for token, jawne in odwrotna.items():
                tekst = tekst.replace(token, jawne)
            punkty.append(Punkt(tekst, zrodla, ai=True))
        grupy.append({"kod": kod, "nazwa": nazwa, "punkty": punkty})
    komunikat = f"Uporządkowane przez model lokalny {settings.OKRES_AI_MODEL}. Każde zdanie odsyła do notatki."
    if odrzucone:
        komunikat += f" Odrzucono zdania bez źródła: {odrzucone}."
    return Zestawienie("ai", komunikat, grupy)


def wymagane_elementy(ocena, wynik) -> list[str]:
    """Co musi znaleźć się w treści oceny (z przepisów i przypisów do wzoru), bez gotowych sformułowań."""
    elementy = ["Wnioski do IPRZ: kierunki rozwoju zawodowego, obszary wiedzy i umiejętności do doskonalenia, "
                "proponowane formy i metody (przypis do wzoru; § 11 ust. 1 pkt 5)."]
    if wynik is not None and not wynik.pozytywna:
        elementy.insert(0, "Uzasadnienie jest obowiązkowe przy ocenie negatywnej (§ 11 ust. 3); może odnosić się "
                           "do wszystkich albo tylko niektórych ocen cząstkowych.")
    elif wynik is not None:
        elementy.insert(0, "Uzasadnienie przy ocenie pozytywnej jest fakultatywne (§ 11 ust. 4).")
    elementy.append("Uwzględnij wnioski z rozmowy oceniającej (§ 11 ust. 2).")
    return elementy
