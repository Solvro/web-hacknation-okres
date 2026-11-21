"""Progressive enhancement: formularze HTMX mają też method/action. Gdy przeglądarka wyśle je bez JavaScriptu,
widok zwraca sam fragment; middleware osadza go w pełnym układzie strony z odnośnikiem powrotu, żeby wynik
zapisu albo komunikat błędu był widoczny, a nie znikał."""

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe


def _powrot(request) -> str:
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(referer, {request.get_host()}, request.is_secure()):
        return referer
    dopasowanie = request.resolver_match
    if dopasowanie and dopasowanie.namespace == "oceny" and "pk" in dopasowanie.kwargs:
        return reverse("oceny:szczegoly", args=[dopasowanie.kwargs["pk"]])
    if dopasowanie and dopasowanie.namespace == "partner":
        p = getattr(request.user, "pracownik", None)
        return reverse("partner:zespol" if p and p.podwladni.exists() else "partner:moje")
    return reverse("oceny:moje_sprawy")


class FragmentBezJsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        odp = self.get_response(request)
        if (request.method != "POST" or request.headers.get("HX-Request") == "true" or odp.status_code != 200
                or odp.streaming or not odp.get("Content-Type", "").startswith("text/html")):
            return odp
        html = odp.content.decode(odp.charset or "utf-8")
        if html.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
            return odp
        strona = render_to_string("oceny/bez_js.html", {"fragment": mark_safe(html), "powrot": _powrot(request)}, request)
        return HttpResponse(strona)
