from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from . import rules
from .models import Ocena


def _ocena_dla(request, pk) -> Ocena:
    # Wgląd mają tylko strony oceny; kadry korzystają z panelu admina.
    return get_object_or_404(Ocena, Q(oceniany=request.user) | Q(oceniajacy=request.user), pk=pk)


def _kontekst(request, ocena, bledy=()):
    return {
        "ocena": ocena,
        "wykaz": rules.extra_criteria(ocena.wersja_regul),
        "maks": rules.load(ocena.wersja_regul)["kryteria_dodatkowe"]["max"],
        "jest_oceniajacym": ocena.oceniajacy_id == request.user.id,
        "jest_ocenianym": ocena.oceniany_id == request.user.id,
        "bledy": bledy,
    }


@login_required
def szczegoly(request, pk):
    ocena = _ocena_dla(request, pk)
    return render(request, "oceny/szczegoly.html", _kontekst_oceny(request, ocena))


@login_required
@require_POST
def ustaw_kryteria(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniajacy_id != request.user.id:
        raise PermissionDenied("Kryteria wyznacza oceniający.")
    bledy = ()
    try:
        ocena.ustaw_kryteria(request.POST.getlist("kryteria"))
    except ValidationError as e:
        bledy = e.messages
        ocena.refresh_from_db()
    return render(request, "oceny/_kryteria.html", _kontekst(request, ocena, bledy))


@login_required
@require_POST
def potwierdz_kryteria(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniany_id != request.user.id:
        raise PermissionDenied("Kryteria potwierdza oceniany.")
    ocena.potwierdz_kryteria()
    return render(request, "oceny/_kryteria.html", _kontekst_oceny(request, ocena) | {"odswiez_ocene": True})


def _dane_formularza(request, ocena):
    czastkowe = {}
    for kod in ocena.wszystkie_kryteria():
        try:
            czastkowe[kod] = int(request.POST.get(f"kryterium_{kod}", ""))
        except ValueError:
            pass
    try:
        data_rozmowy = date.fromisoformat(request.POST.get("data_rozmowy", ""))
    except ValueError:
        data_rozmowy = None
    return czastkowe, data_rozmowy, request.POST.get("uzasadnienie", ""), request.POST.get("wnioski_iprz", "")


def _kontekst_oceny(request, ocena, czastkowe=None, bledy=None, **pola):
    czastkowe = ocena.oceny_czastkowe if czastkowe is None else czastkowe
    return _kontekst(request, ocena) | {
        "kryteria_oceny": [(kod, nazwa, czastkowe.get(kod)) for kod, nazwa in ocena.wszystkie_kryteria().items()],
        "skala": rules.load(ocena.wersja_regul)["punktacja"]["skala_czastkowa"],
        "wynik": ocena.podglad_wyniku(czastkowe),
        "bledy_pol": bledy or {},
        "pola": pola,
    }


def _tylko_oceniajacy(request, pk) -> Ocena:
    ocena = _ocena_dla(request, pk)
    if ocena.oceniajacy_id != request.user.id:
        raise PermissionDenied("Ocenę sporządza oceniający.")
    return ocena


@login_required
@require_POST
def podglad_wyniku(request, pk):
    """Podgląd średniej, poziomu i wyniku w trakcie wypełniania (bez zapisu)."""
    ocena = _tylko_oceniajacy(request, pk)
    czastkowe, *_ = _dane_formularza(request, ocena)
    return render(request, "oceny/_wynik.html", _kontekst_oceny(request, ocena, czastkowe))


@login_required
@require_POST
def sporzadz(request, pk):
    ocena = _tylko_oceniajacy(request, pk)
    czastkowe, data_rozmowy, uzasadnienie, wnioski = _dane_formularza(request, ocena)
    try:
        ocena.sporzadz(czastkowe, data_rozmowy, uzasadnienie, wnioski)
    except ValidationError as e:
        ctx = _kontekst_oceny(request, ocena, czastkowe, data_rozmowy=request.POST.get("data_rozmowy", ""),
                              uzasadnienie=uzasadnienie, wnioski_iprz=wnioski)
        ctx["bledy_pol"] = {k: v[0] for k, v in e.message_dict.items()}
        return render(request, "oceny/_ocena.html", ctx)
    return render(request, "oceny/_ocena.html", _kontekst_oceny(request, ocena))


def _zapoznanie(request, ocena, bledy=None):
    return render(request, "oceny/_zapoznanie.html", _kontekst_oceny(request, ocena) | {"bledy_zapoznania": bledy or {}})


@login_required
@require_POST
def potwierdz_zapoznanie(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniany_id != request.user.id:
        raise PermissionDenied("Zapoznanie potwierdza oceniany.")
    ocena.potwierdz_zapoznanie()
    return _zapoznanie(request, ocena)


@login_required
@require_POST
def fikcja_zapoznania(request, pk):
    ocena = _tylko_oceniajacy(request, pk)
    try:
        ocena.odnotuj_fikcje_zapoznania(request.POST.get("uwagi", ""))
    except ValidationError as e:
        return _zapoznanie(request, ocena, {k: v[0] for k, v in e.message_dict.items()})
    return _zapoznanie(request, ocena)


@login_required
@require_POST
def zloz_sprzeciw(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniany_id != request.user.id:
        raise PermissionDenied("Sprzeciw składa oceniany.")
    try:
        ocena.zloz_sprzeciw(request.POST.get("tresc", ""))
    except ValidationError as e:
        return _zapoznanie(request, ocena, {k: v[0] for k, v in e.message_dict.items()})
    return _zapoznanie(request, ocena)
