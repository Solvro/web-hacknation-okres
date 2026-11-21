from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from . import rozwoj, rules, zegar
from .models import Ocena, Urzad, ZegarDemo


def kontekst_globalny(request):
    u = request.user
    return {"okres_demo": settings.OKRES_DEMO, "urzad": Urzad.biezacy(), "demo_konta": demo_konta,
            "moze_statystyki": u.is_authenticated and _moze_statystyki(u)}


def _jest_dg(user) -> bool:
    return bool(getattr(user, "pracownik", None) and user.pracownik.dyrektor_generalny)


def _sprawy_widoczne(user):
    """Oceniany i oceniający widzą swoje sprawy, kadry wszystkie (akta osobowe), DG sprawy ze sprzeciwem,
    z wnioskiem o kolejny stopień służbowy (art. 89) i te, o których dostał powiadomienie."""
    if user.is_staff:
        return Ocena.objects.all()
    warunek = Q(oceniany=user) | Q(oceniajacy=user)
    if _jest_dg(user):
        warunek |= Q(sprzeciwy__isnull=False) | Q(wniosek_stopien="tak") | Q(przypomnienia__odbiorca=user)
    return Ocena.objects.filter(warunek).distinct()


def _ocena_dla(request, pk) -> Ocena:
    return get_object_or_404(_sprawy_widoczne(request.user), pk=pk)


@login_required
def moje_sprawy(request):
    sprawy = _sprawy_widoczne(request.user).select_related("oceniany__pracownik", "oceniajacy")
    wiersze = []
    for o in sprawy:
        krok = o.nastepny_krok(request.user)
        wiersze.append({"ocena": o, "krok": krok})
    if request.GET.get("filtr") == "moje":
        wiersze = [w for w in wiersze if w["krok"] and w["krok"]["moj"]]
    wiersze.sort(key=lambda w: (not (w["krok"] and w["krok"]["moj"]), (w["krok"] or {}).get("termin") or date.max))
    return render(request, "oceny/moje_sprawy.html", {
        "wiersze": wiersze, "filtr": request.GET.get("filtr", ""),
        "powiadomienia": request.user.przypomnienia.filter(przeczytane=False).select_related("ocena")[:20],
        "wynik_schedulera": request.session.pop("wynik_schedulera", None),
    })


@login_required
@require_POST
def przeczytane(request, pk):
    request.user.przypomnienia.filter(pk=pk).update(przeczytane=True)
    return HttpResponse("")


@login_required
@require_POST
def uruchom_scheduler(request):
    """Na pokaz: kadry uruchamiają scheduler ręcznie (w urzędzie robi to cron raz dziennie)."""
    if not (settings.OKRES_DEMO and request.user.is_staff):
        raise PermissionDenied("Ręczne uruchomienie schedulera jest dostępne tylko w trybie demo dla kadr.")
    from . import scheduler

    request.session["wynik_schedulera"] = scheduler.uruchom()
    return redirect("oceny:moje_sprawy")


@login_required
def zaproszenie_ics(request, pk):
    """UC-03/UC-07: zaproszenie na rozmowę do kalendarza poczty. Tytuł bez informacji kadrowych."""
    ocena = _ocena_dla(request, pk)
    if ocena.oceniajacy_id != request.user.id:
        raise PermissionDenied("Zaproszenie wysyła oceniający.")
    try:
        start = datetime.fromisoformat(f"{request.GET['data']}T{request.GET.get('godzina', '10:00')}")
    except (KeyError, ValueError):
        return HttpResponse("Podaj datę i godzinę spotkania.", status=400)
    try:
        minuty = max(15, min(240, int(request.GET.get("minuty", 60))))
    except ValueError:
        minuty = 60
    koniec = start + timedelta(minutes=minuty)
    fmt = "%Y%m%dT%H%M%S"
    rodzaj = request.GET.get("rodzaj") if request.GET.get("rodzaj") in ("kryteria", "oceniajaca") else "rozmowa"
    uid = f"okres-{ocena.pk}-{rodzaj}-{start:{fmt}}@okres.local"
    adresy = [u.email for u in (ocena.oceniany, ocena.oceniajacy) if u.email]
    linie = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//OKRES//PL", "METHOD:REQUEST", "BEGIN:VEVENT",
        f"UID:{uid}", f"DTSTAMP:{datetime.now():{fmt}}", f"DTSTART;TZID=Europe/Warsaw:{start:{fmt}}",
        f"DTEND;TZID=Europe/Warsaw:{koniec:{fmt}}", "SUMMARY:Spotkanie z przełożonym",
        "DESCRIPTION:Szczegóły w systemie OKRES po zalogowaniu.",
        *[f"ATTENDEE;RSVP=TRUE:mailto:{a}" for a in adresy], "END:VEVENT", "END:VCALENDAR",
    ]
    odp = HttpResponse("\r\n".join(linie) + "\r\n", content_type="text/calendar; charset=utf-8")
    odp["Content-Disposition"] = 'attachment; filename="spotkanie.ics"'
    return odp


@login_required
def jak_obliczono(request, pk, rodzaj):
    ocena = _ocena_dla(request, pk)
    rachunek = ocena.rachunek_kryteriow() if rodzaj == "kryteria" else ocena.rachunek_oceny()
    return render(request, "oceny/_rachunek.html", {"rachunek": rachunek})


def _miejscowosc(user) -> str:
    """Miejscowość pracy osoby, a gdy jej brak, siedziba urzędu (schemat pól KPRM)."""
    p = getattr(user, "pracownik", None)
    if p and p.miejscowosc_pracy:
        return p.miejscowosc_pracy
    urzad = Urzad.biezacy()
    return urzad.miejscowosc if urzad else ""


def _kontekst(request, ocena, bledy=()):
    maks = rules.load(ocena.wersja_regul)["kryteria_dodatkowe"]["max"]
    return {
        "ocena": ocena,
        "wykaz": rules.extra_criteria(ocena.arkusz, ocena.wersja_regul),
        "obowiazkowe": rules.mandatory_criteria(ocena.arkusz, ocena.wersja_regul),
        "maks": maks,
        "sloty": (ocena.kryteria_dodatkowe + [""] * maks)[:maks],
        "miejscowosc_domyslna": _miejscowosc(ocena.oceniajacy),
        "jest_oceniajacym": ocena.oceniajacy_id == request.user.id,
        "jest_ocenianym": ocena.oceniany_id == request.user.id,
        "jest_dg": _jest_dg(request.user) and request.user.id not in (ocena.oceniany_id, ocena.oceniajacy_id),
        "jest_kadrami": request.user.is_staff,
        "bledy": bledy,
    }


@login_required
def szczegoly(request, pk):
    ocena = _ocena_dla(request, pk)
    return render(request, "oceny/szczegoly.html", _kontekst_oceny(request, ocena) | _kontekst_kadrowe(request, ocena))


@login_required
@require_POST
def ustaw_kryteria(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniajacy_id != request.user.id:
        raise PermissionDenied("Kryteria wyznacza oceniający.")
    bledy = ()
    try:
        ocena.ustaw_kryteria([k for k in request.POST.getlist("kryteria") if k])
    except ValidationError as e:
        bledy = e.messages
        ocena.refresh_from_db()
    return render(request, "oceny/_kryteria.html", _kontekst(request, ocena, bledy))


@login_required
@require_POST
def zatwierdz_kryteria(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniajacy_id != request.user.id:
        raise PermissionDenied("Rozmowę i kryteria zatwierdza oceniający.")
    try:
        data_rozmowy = date.fromisoformat(request.POST.get("data_rozmowy", ""))
    except ValueError:
        data_rozmowy = None
    bledy = ()
    try:
        ocena.zatwierdz_kryteria(data_rozmowy, request.POST.get("miejscowosc", ""), request.POST.get("cele_i_oczekiwania", ""))
    except ValidationError as e:
        bledy = e.messages
    return render(request, "oceny/_kryteria.html", _kontekst(request, ocena, bledy))


@login_required
@require_POST
def potwierdz_kryteria(request, pk):
    ocena = _ocena_dla(request, pk)
    if ocena.oceniany_id != request.user.id:
        raise PermissionDenied("Kryteria potwierdza oceniany.")
    ocena.potwierdz_kryteria()
    return render(request, "oceny/_kryteria.html", _kontekst_oceny(request, ocena) | {"odswiez_ocene": True})


def _data(wartosc):
    try:
        return date.fromisoformat(wartosc or "")
    except ValueError:
        return None


def _liczba(wartosc):
    try:
        return int(wartosc)
    except (TypeError, ValueError):
        return None


POLA_DATY = ("okres_od", "okres_do", "poprz_data", "data_stopnia")
POLA_LICZBY = ("rok_mianowania", "stopien_sluzbowy")
POLA_TEKSTU = ("miejscowosc", "poprz_ocena", "poprz_poziom", "wniosek_stopien", "umotywowanie_wniosku")


def _dane_formularza(request, ocena):
    czastkowe = {}
    for kod in ocena.wszystkie_kryteria():
        if (pkt := _liczba(request.POST.get(f"kryterium_{kod}"))) is not None:
            czastkowe[kod] = pkt
    pola = {k: _data(request.POST.get(k)) for k in POLA_DATY}
    pola |= {k: _liczba(request.POST.get(k)) for k in POLA_LICZBY}
    pola |= {k: request.POST.get(k, "") for k in POLA_TEKSTU}
    return (czastkowe, _data(request.POST.get("data_rozmowy")), request.POST.get("uzasadnienie", ""),
            request.POST.get("wnioski_iprz", ""), pola)


def _podpowiedz_pytania(ocena, kod) -> str:
    """Pytanie do rozmowy z pierwszego wskaźnika kryterium w Załączniku nr 1."""
    opis = rules.criteria(ocena.wersja_regul)[kod]["opis"]
    return f"Brak obserwacji. Zapytaj w rozmowie o przykład z okresu oceny: „{opis[0]}”"


def _kontekst_oceny(request, ocena, czastkowe=None, bledy=None, **pola):
    czastkowe = ocena.oceny_czastkowe if czastkowe is None else czastkowe
    grupy = {kod: obs for kod, _, obs in ocena.obserwacje_wg_kryteriow(request.user)}
    return _kontekst(request, ocena) | {
        "kryteria_oceny": [(kod, nazwa, czastkowe.get(kod)) for kod, nazwa in ocena.wszystkie_kryteria().items()],
        "obserwacje_kryteriow": [
            {"kod": kod, "nazwa": nazwa, "wybrane": czastkowe.get(kod), "obserwacje": grupy.get(kod, []),
             "podpowiedz": "" if grupy.get(kod) else _podpowiedz_pytania(ocena, kod)}
            for kod, nazwa in ocena.wszystkie_kryteria().items()
        ],
        "obserwacje_bez_kryterium": grupy.get("", []),
        "skala": rules.load(ocena.wersja_regul)["punktacja"]["skala_czastkowa"],
        "wynik": ocena.podglad_wyniku(czastkowe),
        "podpowiedzi_rozwoju": rozwoj.podpowiedzi(ocena.wszystkie_kryteria(), czastkowe),
        "bledy_pol": bledy or {},
        "pola": ocena.domyslne_pola() | {"miejscowosc": _miejscowosc(ocena.oceniajacy)}
                | {k: v for k, v in pola.items() if v not in (None, "")},
        "z_historii": ocena.poprzednia_z_historii(),
        "poziomy": [p["nazwa"] for p in reversed(rules.load(ocena.wersja_regul)["punktacja"]["poziomy"])],
        "stopnie": range(1, 10),
        "miejscowosc_ocenianego": _miejscowosc(ocena.oceniany),
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
    ctx = _kontekst_oceny(request, ocena, czastkowe)
    # Wynik w miejscu tabeli, podpowiedzi rozwojowe obok (out-of-band), bez przeładowania formularza.
    html = render_to_string("oceny/_wynik.html", ctx, request) + render_to_string("oceny/_rozwoj.html", ctx | {"rozwoj_oob": True}, request)
    return HttpResponse(html)


@login_required
@require_POST
def sporzadz(request, pk):
    ocena = _tylko_oceniajacy(request, pk)
    czastkowe, data_rozmowy, uzasadnienie, wnioski, pola = _dane_formularza(request, ocena)
    try:
        ocena.sporzadz(czastkowe, data_rozmowy, uzasadnienie, wnioski, **pola)
    except ValidationError as e:
        ctx = _kontekst_oceny(request, ocena, czastkowe, **(pola | {
            "data_rozmowy": data_rozmowy, "uzasadnienie": uzasadnienie, "wnioski_iprz": wnioski}))
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
    ocena.potwierdz_zapoznanie(request.POST.get("miejscowosc") or _miejscowosc(ocena.oceniany))
    return _zapoznanie(request, ocena)


@login_required
@require_POST
def fikcja_zapoznania(request, pk):
    ocena = _ocena_dla(request, pk)
    if not request.user.is_staff:
        raise PermissionDenied("Fikcję zapoznania dokumentuje komórka kadrowa.")
    try:
        ocena.odnotuj_fikcje_zapoznania(request.user, request.POST.get("uwagi", ""), _data(request.POST.get("data_doreczenia")))
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


@require_POST
def demo_zaloguj(request):
    """Przełącznik ról na pokaz: tylko w trybie demo i tylko na konta utworzone przez seed_demo."""
    from django.contrib.auth import login
    from django.contrib.auth.models import User
    from django.shortcuts import redirect

    from .management.commands.seed_demo import LOGINY_DEMO

    login_demo = request.POST.get("login", "")
    if not settings.OKRES_DEMO or login_demo not in LOGINY_DEMO:
        raise PermissionDenied("Szybkie logowanie działa tylko w trybie demo.")
    login(request, get_object_or_404(User, username=login_demo), backend="django.contrib.auth.backends.ModelBackend")
    return redirect("oceny:moje_sprawy")


def demo_konta():
    from django.contrib.auth.models import User

    from .management.commands.seed_demo import LOGINY_DEMO

    if not settings.OKRES_DEMO:
        return []
    return list(User.objects.filter(username__in=LOGINY_DEMO).select_related("pracownik").order_by("pk"))


@login_required
@require_POST
def dodaj_obserwacje(request, pk):
    ocena = _ocena_dla(request, pk)
    try:
        data = date.fromisoformat(request.POST.get("data", ""))
    except ValueError:
        data = None
    bledy = {}
    try:
        ocena.dodaj_obserwacje(request.user, data, request.POST.get("tresc", ""), request.POST.get("kryterium", ""),
                               request.POST.get("skutek", ""), request.POST.get("udostepniona") == "1")
    except ValidationError as e:
        bledy = {k: v[0] for k, v in e.message_dict.items()}
    return render(request, "oceny/_obserwacje.html", _kontekst_oceny(request, ocena) | {"bledy_obserwacji": bledy})


STOPNIE_SLOWNIE = ["", "pierwszego", "drugiego", "trzeciego", "czwartego", "piątego", "szóstego", "siódmego", "ósmego",
                   "dziewiątego"]


def _przedzialy(ocena):
    """Wiersze tabeli „Przyznanie oceny” ze wzoru, z zaznaczeniem przedziału średniej."""
    poziomy = rules.load(ocena.wersja_regul)["punktacja"]["poziomy"]
    wiersze, dolna = [], None
    minimum = min(rules.load(ocena.wersja_regul)["punktacja"]["skala_czastkowa"])
    for p in poziomy:
        zakres = (f"od {minimum} punktu do {p['do']} punktów" if dolna is None
                  else f"powyżej {dolna} punktów do {p['do']} punktów")
        wiersze.append((zakres, p["nazwa"], ocena.sporzadzona and ocena.poziom == p["nazwa"]))
        dolna = p["do"]
    return wiersze


@login_required
def wydruk(request, pk):
    """Arkusz A/B/C do druku lub zapisu PDF z przeglądarki. ?czesc=I: kopia części I dla ocenianego."""
    ocena = _ocena_dla(request, pk)
    cfg = rules.load(ocena.wersja_regul)["arkusze"][ocena.arkusz]
    maks = rules.load(ocena.wersja_regul)["kryteria_dodatkowe"]["max"]
    obowiazkowe = rules.mandatory_criteria(ocena.arkusz, ocena.wersja_regul)
    dodatkowe_nazwy = [nazwa for kod, nazwa in ocena.wszystkie_kryteria().items() if kod not in obowiazkowe]
    dodatkowe_kolumna = (dodatkowe_nazwy + [""] * maks)[:maks]
    # Układ wzoru: obok obowiązkowych najpierw pola kryteriów dodatkowych, niżej scalone pole terminu.
    wiersze = []
    for i, nazwa in enumerate(obowiazkowe.values()):
        wiersze.append((nazwa, dodatkowe_kolumna[i] if i < maks else None, i == maks))
    czastkowe = ocena.oceny_czastkowe
    dodatkowe_kody = [k for k in ocena.kryteria_dodatkowe]
    wszystkie = ocena.wszystkie_kryteria()
    czastkowe_dodatkowe = [(wszystkie[k], czastkowe.get(k)) for k in dodatkowe_kody]
    czastkowe_dodatkowe += [("brak", None)] * (maks - len(czastkowe_dodatkowe))
    return render(request, "oceny/wydruk.html", {
        "ocena": ocena, "cfg": cfg, "wiersze_czesci_i": wiersze, "rowspan_terminu": len(obowiazkowe) - maks,
        "tylko_czesc_i": request.GET.get("czesc") == "I" or not ocena.sporzadzona,
        "skala": rules.load(ocena.wersja_regul)["punktacja"]["skala_czastkowa"],
        "czastkowe_obowiazkowe": [(nazwa, czastkowe.get(kod)) for kod, nazwa in obowiazkowe.items()],
        "czastkowe_dodatkowe": czastkowe_dodatkowe,
        "srednia_wydruk": f"{ocena.srednia}".replace(".", ",") if ocena.srednia is not None else "",
        "przedzialy": _przedzialy(ocena),
        "stopien_slownie": STOPNIE_SLOWNIE[ocena.stopien_sluzbowy + 1] if ocena.stopien_sluzbowy and ocena.stopien_sluzbowy < 9 else "",
    })


@login_required
@require_POST
def rozpatrz_sprzeciw(request, pk):
    ocena = _ocena_dla(request, pk)
    if not _jest_dg(request.user):
        raise PermissionDenied("Sprzeciw rozpatruje dyrektor generalny.")
    czastkowe, *_ = _dane_formularza(request, ocena)
    bledy = {}
    try:
        ocena.rozpatrz_sprzeciw(request.user, request.POST.get("decyzja", ""), request.POST.get("uzasadnienie_decyzji", ""),
                                czastkowe)
    except ValidationError as e:
        bledy = {k: v[0] for k, v in e.message_dict.items()}
    ocena.refresh_from_db()
    return render(request, "oceny/_ocena.html", _kontekst_oceny(request, ocena) | {"bledy_zapoznania": bledy})


@login_required
@require_POST
def zdarzenie_kadrowe(request, pk, rodzaj):
    ocena = _ocena_dla(request, pk)
    bledy = {}
    try:
        if rodzaj == "oceniajacy":
            from django.contrib.auth.models import User
            nowy = get_object_or_404(User, pk=_liczba(request.POST.get("nowy")) or 0)
            ocena.zmien_oceniajacego(request.user, nowy, _data(request.POST.get("data")), request.POST.get("powod", ""))
        elif rodzaj == "stanowisko":
            ocena.zmiana_stanowiska(request.user, _data(request.POST.get("data_zmiany")), request.POST.get("stanowisko", ""),
                                    request.POST.get("rodzaj_stanowiska", ""))
        elif rodzaj == "termin":
            ocena.zmien_termin(request.user, _data(request.POST.get("nowy_termin")), request.POST.get("podstawa", ""),
                               request.POST.get("uzasadnienie", ""))
        else:
            raise PermissionDenied("Nieznane zdarzenie.")
    except ValidationError as e:
        bledy = {k: v[0] for k, v in e.message_dict.items()}
    ocena.refresh_from_db()
    if ocena.oceniajacy_id != request.user.id and not request.user.is_staff:
        return redirect("oceny:moje_sprawy")
    return render(request, "oceny/_kadrowe.html", _kontekst_kadrowe(request, ocena, bledy))


def _kontekst_kadrowe(request, ocena, bledy=None):
    from .models import Pracownik
    baza, opis_bazy = ocena.data_bazowa_szesciu_miesiecy()
    return _kontekst(request, ocena) | {
        "bledy_kadrowe": bledy or {},
        "kandydaci": [p.user for p in Pracownik.objects.select_related("user").exclude(user__in=[ocena.oceniany, ocena.oceniajacy])],
        "rodzaje_stanowisk": Pracownik.RODZAJE,
        "podstawy_terminu": ocena.PODSTAWY_ZMIANY_TERMINU,
        "baza_6m": baza, "opis_bazy_6m": opis_bazy,
        "jest_kadrami": request.user.is_staff,
    }


@login_required
def zawiadomienie(request, pk, zdarzenie_pk):
    """§ 8: pisemne zawiadomienie ocenianego o nowym terminie; kopia do arkusza."""
    ocena = _ocena_dla(request, pk)
    z = get_object_or_404(ocena.zdarzenia_kadrowe, pk=zdarzenie_pk, rodzaj="zmiana_terminu")
    return render(request, "oceny/zawiadomienie.html", {"ocena": ocena, "z": z, "urzad": Urzad.biezacy(),
                                                         "stary": _data(z.dane.get("stary")), "nowy": _data(z.dane.get("nowy"))})


@login_required
def przygotowanie(request, pk, rodzaj):
    """Przygotowanie do rozmowy: agenda z przepisów, wskaźniki kryteriów, obserwacje, trudne sytuacje."""
    ocena = _ocena_dla(request, pk)
    if rodzaj not in ("rozpoczynajaca", "oceniajaca") or request.user.id not in (ocena.oceniany_id, ocena.oceniajacy_id):
        raise PermissionDenied("Przygotowanie do rozmowy jest dla stron oceny.")
    wykaz = rules.criteria(ocena.wersja_regul)
    grupy = {kod: obs for kod, _, obs in ocena.obserwacje_wg_kryteriow(request.user)}
    kryteria = [{"nazwa": nazwa, "wskazniki": wykaz[kod]["opis"], "obserwacje": grupy.get(kod, [])}
                for kod, nazwa in (ocena.wszystkie_kryteria() if rodzaj == "oceniajaca"
                                   else rules.mandatory_criteria(ocena.arkusz, ocena.wersja_regul)).items()]
    cfg = rules.rozmowy()
    return render(request, "oceny/przygotowanie.html", {
        "ocena": ocena, "r": cfg[rodzaj], "rodzaj": rodzaj, "kryteria": kryteria,
        "trudne": cfg["trudne_sytuacje"], "feedback": cfg["biezacy_feedback"],
        "jest_oceniajacym": request.user.id == ocena.oceniajacy_id,
        "dodatkowe_do_wyboru": rules.extra_criteria(ocena.arkusz, ocena.wersja_regul) if rodzaj == "rozpoczynajaca" else {},
    })


@login_required
def porownanie_regul(request, pk):
    """Wpływ wersji przepisów na terminy tej sprawy (pokaz aktualizacji reguł bez przebudowy systemu)."""
    import copy

    ocena = _ocena_dla(request, pk)
    wiersze = []
    for w in rules.dostepne_wersje():
        kopia = copy.copy(ocena)
        kopia.wersja_regul = w["kod"]
        wiersze.append({"wersja": w, "kryteria": kopia.rachunek_kryteriow(), "ocena": kopia.rachunek_oceny(),
                        "biezaca": w["kod"] == ocena.wersja_regul, "bledy": rules.sprawdz(w["kod"])})
    return render(request, "oceny/porownanie_regul.html", {"ocena": ocena, "wiersze": wiersze, "aktywna": rules.aktywna()})


def _moze_statystyki(user) -> bool:
    return user.is_staff or _jest_dg(user)


@login_required
def statystyki(request):
    if not _moze_statystyki(request.user):
        raise PermissionDenied("Statystyki są dostępne dla kierownictwa i kadr.")
    from . import statystyki as st

    dane = st.zbierz()
    if request.GET.get("format") == "csv":
        import csv

        odp = HttpResponse(content_type="text/csv; charset=utf-8")
        odp["Content-Disposition"] = 'attachment; filename="okres-statystyki.csv"'
        w = csv.writer(odp, delimiter=";")
        w.writerow(["wskaźnik", "wartość"])
        for k in ("liczba_spraw", "po_terminie", "w_30_dni", "pozytywne", "negatywne", "wnioski_o_stopien", "sprzeciwy",
                  "fikcje_zapoznania"):
            w.writerow([k, dane[k]])
        for grupa in ("etapy", "arkusze", "komorki", "poziomy", "sprzeciwy_decyzje"):
            for nazwa, liczba in dane[grupa]:
                w.writerow([f"{grupa}: {nazwa}", liczba])
        return odp
    return render(request, "oceny/statystyki.html", dane)


@login_required
def eksport_sprawy(request, pk):
    """UC-21: paczka do akt osobowych / ręcznego przekazania do EZD: arkusz HTML, dane JSON, historia."""
    import io
    import json
    import zipfile

    from django.contrib.staticfiles import finders
    from django.core.serializers.json import DjangoJSONEncoder

    ocena = _ocena_dla(request, pk)
    if not (request.user.is_staff or request.user.id == ocena.oceniany_id):
        raise PermissionDenied("Eksport do akt wykonuje komórka kadrowa (oceniany może pobrać własną sprawę).")
    arkusz = wydruk(request, pk).content.decode()
    css = open(finders.find("oceny/wydruk.css"), encoding="utf-8").read()
    arkusz = arkusz.replace('<link rel="stylesheet" href="/static/oceny/wydruk.css">', f"<style>{css}</style>")
    pola = {f.name: getattr(ocena, f.attname) for f in ocena._meta.fields}
    r_oceny, r_kryt = ocena.rachunek_oceny(), ocena.rachunek_kryteriow()
    dane = {
        "format": "okres-sprawa/1", "wygenerowano": zegar.dzis(), "pakiet_regul": ocena.wersja_regul,
        "ocena": pola, "kryteria": ocena.wszystkie_kryteria(),
        "terminy": {"kryteria": r_kryt and r_kryt.termin, "ocena": r_oceny and r_oceny.termin,
                    "rachunek_oceny": [k.__dict__ for k in r_oceny.kroki] if r_oceny else []},
        "zdarzenia_kadrowe": list(ocena.zdarzenia_kadrowe.values("data", "rodzaj", "opis", "podstawa", "dane")),
        "sprzeciwy": list(ocena.sprzeciwy.values("wersja", "data_zlozenia", "tresc", "decyzja", "data_decyzji",
                                                  "uzasadnienie_decyzji")),
        "wersje": list(ocena.wersje.values("wersja", "utworzona", "powod", "dane")),
        "korekty": list(ocena.korekty.values("kiedy", "kto__username", "pole", "przed", "po", "powod")),
    }
    bufor = io.BytesIO()
    with zipfile.ZipFile(bufor, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("arkusz.html", arkusz)
        z.writestr("dane.json", json.dumps(dane, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2))
        z.writestr("CZYTAJ.txt", "Paczka sprawy oceny okresowej z systemu OKRES.\n"
                                 "arkusz.html: arkusz do druku lub zapisu PDF (wzór z rozporządzenia).\n"
                                 "dane.json: komplet danych sprawy, terminy z rachunkiem, zdarzenia, sprzeciwy, wersje i korekty.\n"
                                 "Notatki przełożonego i dane HR partnera nie są częścią akt.\n")
    odp = HttpResponse(bufor.getvalue(), content_type="application/zip")
    odp["Content-Disposition"] = f'attachment; filename="ocena-{ocena.pk}.zip"'
    return odp


@login_required
@require_POST
def asystent(request, pk):
    """Porządkowanie własnych obserwacji przełożonego przed sporządzeniem oceny (z odnośnikami do notatek)."""
    from . import asystent as a

    ocena = _tylko_oceniajacy(request, pk)
    if ocena.sporzadzona:
        raise PermissionDenied("Ocena została już sporządzona.")
    czastkowe, *_ = _dane_formularza(request, ocena)
    return render(request, "oceny/_asystent.html", {
        "z": a.zestaw(ocena, request.user), "elementy": a.wymagane_elementy(ocena, ocena.podglad_wyniku(czastkowe)),
    })
