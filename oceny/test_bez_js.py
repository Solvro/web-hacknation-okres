"""QA M3: formularze działają też bez JavaScriptu (progressive enhancement)."""

import re
from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, ZegarDemo

FORM = re.compile(r"<form\b[^>]*>", re.DOTALL)


@override_settings(OKRES_DEMO=True)
class BezJavaScriptuTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=date(2026, 11, 21)).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())

    def strony(self):
        for login in ("oceniajaca", "oceniany", "kadry", "dyrektor", "piotr"):
            u = User.objects.get(username=login)
            self.client.force_login(u)
            for o in Ocena.objects.all():
                r = self.client.get(reverse("oceny:szczegoly", args=[o.pk]))
                if r.status_code == 200:
                    yield f"{login} /oceny/{o.pk}/", r.content.decode()
            for nazwa in ("partner:zespol", "partner:moje"):
                r = self.client.get(reverse(nazwa))
                if r.status_code == 200:
                    yield f"{login} {nazwa}", r.content.decode()

    def test_kazdy_formularz_htmx_ma_method_action_i_csrf(self):
        sprawdzone = 0
        for gdzie, html in self.strony():
            for m in FORM.finditer(html):
                tag = m.group(0)
                if "hx-post" not in tag:
                    continue
                sprawdzone += 1
                hx = re.search(r'hx-post="([^"]+)"', tag).group(1)
                self.assertIn('method="post"', tag, gdzie)
                self.assertIn(f'action="{hx}"', tag, gdzie)
                koniec = html.index("</form>", m.end())
                self.assertIn("csrfmiddlewaretoken", html[m.end():koniec], f"{gdzie}: {tag}")
            # Przycisk z hx-post poza formularzem bez JS nic nie robi.
            for b in re.finditer(r"<button\b[^>]*hx-post=[^>]*>", html):
                przed = html[:b.start()]
                self.assertGreater(przed.rfind("<form"), przed.rfind("</form>"), f"{gdzie}: {b.group(0)}")
        self.assertGreater(sprawdzone, 10)

    def test_post_bez_htmx_daje_pelna_strone_z_wynikiem_i_powrotem(self):
        anna = User.objects.get(username="oceniajaca")
        o = Ocena.objects.filter(oceniajacy=anna, sporzadzona_at__isnull=True).first()
        self.client.force_login(anna)
        url = reverse("oceny:dodaj_obserwacje", args=[o.pk])
        r = self.client.post(url, {"data": "2026-11-20", "tresc": "Zapis bez JavaScriptu"})
        self.assertContains(r, "<!doctype html>")
        self.assertContains(r, "Zapis bez JavaScriptu")
        self.assertContains(r, f'href="{reverse("oceny:szczegoly", args=[o.pk])}"')
        r = self.client.post(url, {"data": "xyz", "tresc": "Zła data"})
        self.assertContains(r, "<!doctype html>")
        self.assertContains(r, "Nie rozpoznano daty")

    def test_htmx_dalej_dostaje_fragment(self):
        anna = User.objects.get(username="oceniajaca")
        o = Ocena.objects.filter(oceniajacy=anna, sporzadzona_at__isnull=True).first()
        self.client.force_login(anna)
        r = self.client.post(reverse("oceny:dodaj_obserwacje", args=[o.pk]), {"data": "2026-11-20", "tresc": "Fragment"},
                             headers={"HX-Request": "true"})
        self.assertNotContains(r, "<!doctype html>")
