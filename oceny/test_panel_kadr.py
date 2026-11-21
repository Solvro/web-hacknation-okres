"""Panel kadr i lista spraw: polskie etykiety, imiona zamiast loginów, flaga „brak bieżącej sprawy” (QA L1, L4, M4)."""

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Pracownik


class PanelKadrTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kadry = User.objects.create_superuser("kadry_t", password="x", first_name="Krystyna", last_name="Kadrowa")
        szef = User.objects.create_user("szef_t", first_name="Dorota", last_name="Dyrektorska")
        cls.szef = Pracownik.objects.create(user=szef, stanowisko="Dyrektor", rodzaj_stanowiska="kierujacy")
        jan = User.objects.create_user("jan_t", first_name="Jan", last_name="Bezsprawy")
        Pracownik.objects.create(user=jan, stanowisko="Specjalista", rodzaj_stanowiska="pozostale", przelozony=cls.szef)

    def test_lista_pracownikow_po_polsku_z_flaga_braku_sprawy(self):
        self.client.force_login(self.kadry)
        html = self.client.get("/admin/oceny/pracownik/").content.decode()
        for tekst in ("Wybierz pracownika do zmiany", "Imię i nazwisko", "Przełożony", "Jan Bezsprawy",
                      "Dorota Dyrektorska", "brak bieżącej sprawy", "— wybierz —"):
            self.assertIn(tekst, html)
        for tekst in ("Imie nazwisko", "Przelozony", "Select an option", "szef_t"):
            self.assertNotIn(tekst, html)

    def test_filtr_brak_biezacej_sprawy(self):
        self.client.force_login(self.kadry)
        r = self.client.get("/admin/oceny/pracownik/", {"sprawa": "brak"})
        self.assertContains(r, "Jan Bezsprawy")

    def test_tytul_listy_spraw_zalezy_od_roli(self):
        self.client.force_login(self.kadry)
        self.assertContains(self.client.get("/oceny/"), "<h1>Sprawy w urzędzie</h1>", html=True)
        self.client.force_login(self.szef.user)
        self.assertContains(self.client.get("/oceny/"), "<h1>Moje sprawy</h1>", html=True)
