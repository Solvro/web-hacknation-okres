from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from oceny import daty, zegar
from oceny.models import Obserwacja, Pracownik

from . import reguly, sygnaly
from .models import Docenienie, Uzgodnienie, ZdarzenieZadania


def _podwladny(request, pk) -> Pracownik:
    ja = getattr(request.user, "pracownik", None)
    if not ja:
        raise PermissionDenied("Brak danych kadrowych użytkownika.")
    return get_object_or_404(Pracownik.objects.select_related("user"), pk=pk, przelozony=ja)


def _karta(pracownik, bledy=None):
    lista = sygnaly.dla_pracownika(pracownik)
    return {
        "p": pracownik,
        "sygnaly": lista,
        # gdy sygnał ma własny formularz docenienia, drugi („bez sygnału”) tylko dubluje akcję
        "jest_sygnal_docenienia": any(s.rodzaj == "osiagniecie_bez_docenienia" for s in lista),
        "zdarzenia": pracownik.zdarzenia_zadan.all()[:8],
        "uzgodnienia": pracownik.uzgodnienia.all()[:5],
        "docenienia": pracownik.docenienia.all()[:3],
        "rodzaje": reguly.rodzaje_zdarzen(),
        "katalog": reguly.dzialania(),
        "bledy": bledy or {},
        "dzis": zegar.dzis(),
    }


@login_required
def zespol(request):
    ja = getattr(request.user, "pracownik", None)
    podwladni = ja.podwladni.select_related("user").order_by("user__last_name") if ja else []
    return render(request, "partner/zespol.html", {"karty": [_karta(p) for p in podwladni]})


def _odswiez(request, pracownik, bledy=None):
    return render(request, "partner/_karta.html", {"k": _karta(pracownik, bledy)})


def _bledy(e: ValidationError):
    return {k: v[0] for k, v in e.message_dict.items()} if hasattr(e, "message_dict") else {"__all__": e.messages[0]}


@login_required
@require_POST
def dodaj_zdarzenie(request, pk):
    p = _podwladny(request, pk)
    try:
        ZdarzenieZadania.dodaj(request.user, p, daty.z_formularza(request.POST.get("data")), request.POST.get("rodzaj", ""),
                               request.POST.get("opis", ""))
    except ValidationError as e:
        return _odswiez(request, p, _bledy(e))
    return _odswiez(request, p)


@login_required
@require_POST
def uzgodnij(request, pk):
    p = _podwladny(request, pk)
    try:
        Uzgodnienie.zapisz(request.user, p, request.POST.get("sygnal", ""), request.POST.get("dzialanie", ""),
                           request.POST.get("ustalenie", ""), daty.z_formularza(request.POST.get("data_sprawdzenia"), "data_sprawdzenia"))
    except ValidationError as e:
        return _odswiez(request, p, _bledy(e))
    return _odswiez(request, p)


@login_required
@require_POST
def wynik(request, pk):
    u = get_object_or_404(Uzgodnienie, pk=pk)
    try:
        u.zapisz_wynik(request.user, request.POST.get("wynik", ""), request.POST.get("notatka", ""))
    except ValidationError as e:
        return _odswiez(request, u.pracownik, _bledy(e))
    return _odswiez(request, u.pracownik)


@login_required
@require_POST
def docen(request, pk):
    p = _podwladny(request, pk)
    obs = None
    if request.POST.get("obserwacja"):
        obs = get_object_or_404(Obserwacja, pk=request.POST["obserwacja"], ocena__oceniany=p.user)
    try:
        Docenienie.dodaj(request.user, p, request.POST.get("za_co", ""), request.POST.get("skutek", ""), obs)
    except ValidationError as e:
        return _odswiez(request, p, _bledy(e))
    return _odswiez(request, p)


@login_required
def moje(request):
    """Widok pracownika: wszystkie dane o nim, które bierze pod uwagę HR partner (przejrzystość)."""
    p = getattr(request.user, "pracownik", None)
    if not p:
        raise PermissionDenied("Brak danych kadrowych użytkownika.")
    return render(request, "partner/moje.html", {
        "p": p, "sygnaly": sygnaly.dla_pracownika(p), "zdarzenia": p.zdarzenia_zadan.all(),
        "uzgodnienia": p.uzgodnienia.all(), "docenienia": p.docenienia.all(),
        "nieobecnosci": p.nieobecnosci.all(),
    })


@login_required
@require_POST
def perspektywa(request, pk):
    u = get_object_or_404(Uzgodnienie, pk=pk, pracownik__user=request.user)
    u.dopisz_perspektywe(request.user, request.POST.get("perspektywa", ""))
    return render(request, "partner/_uzgodnienie.html", {"u": u, "moje": True})
