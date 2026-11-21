"""Statystyki zbiorcze dla kierownictwa (UC-22). Tylko liczby z formalnego procesu: bez notatek i danych HR partnera."""

from collections import Counter
from datetime import timedelta

from . import zegar
from .models import Ocena, Sprzeciw


def zbierz() -> dict:
    dzis = zegar.dzis()
    sprawy = list(Ocena.objects.filter(anulowana_powod="").select_related("oceniany__pracownik"))
    etapy = Counter(o.etap_nazwa for o in sprawy)
    sporzadzone = [o for o in sprawy if o.sporzadzona]
    wymagaja = [o for o in sprawy if o.etap in ("kryteria", "ocena")]
    terminy = [(o, (o.nastepny_krok(o.oceniajacy) or {}).get("termin")) for o in wymagaja]
    komorki = Counter((getattr(o.oceniany, "pracownik", None) and o.oceniany.pracownik.komorka) or "—" for o in sprawy)
    sprzeciwy = Sprzeciw.objects.all()
    return {
        "dzis": dzis,
        "liczba_spraw": len(sprawy),
        "etapy": sorted(etapy.items(), key=lambda x: -x[1]),
        "arkusze": sorted(Counter(o.arkusz for o in sprawy).items()),
        "komorki": sorted(komorki.items()),
        "po_terminie": sum(1 for _, t in terminy if t and t < dzis),
        "w_30_dni": sum(1 for _, t in terminy if t and dzis <= t <= dzis + timedelta(days=30)),
        "pozytywne": sum(1 for o in sporzadzone if o.pozytywna),
        "negatywne": sum(1 for o in sporzadzone if o.pozytywna is False),
        "poziomy": sorted(Counter(o.poziom for o in sporzadzone).items(), key=lambda x: -x[1]),
        "wnioski_o_stopien": sum(1 for o in sporzadzone if o.wniosek_stopien == "tak"),
        "sprzeciwy": sprzeciwy.count(),
        "sprzeciwy_decyzje": sorted(Counter(s.get_decyzja_display() or "w rozpatrzeniu" for s in sprzeciwy).items()),
        "fikcje_zapoznania": sum(1 for o in sporzadzone if o.sposob_zapoznania == "fikcja"),
    }
