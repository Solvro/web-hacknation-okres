from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, ZegarDemo
from .pomoc_testow import sprawa_od_kryteriow


@override_settings(OKRES_DEMO=True)
class WydrukTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        sprawa_od_kryteriow(User.objects.get(username="oceniany"))  # seed ma sprawy w toku
        sprawa_od_kryteriow(User.objects.get(username="piotr"))  # seed ma sprawy w toku
        ZegarDemo(data=date(2026, 11, 23)).save()
        cls.jan = User.objects.get(username="oceniany")
        cls.anna = User.objects.get(username="oceniajaca")
        cls.piotr = User.objects.get(username="piotr")

    def przygotuj(self, oceniany, czastkowe=7, **pola):
        o = Ocena.objects.get(oceniany=oceniany)
        o.ustaw_kryteria(["kreatywnosc", "negocjowanie"])
        o.zatwierdz_kryteria(date(2025, 4, 1), "Bydgoszcz")
        o.potwierdz_kryteria()
        komplet = {k: czastkowe for k in o.wszystkie_kryteria()}
        o.sporzadz(komplet, date(2026, 11, 23), "", "Szkolenie z mediacji", miejscowosc="Bydgoszcz", **pola)
        return o

    def test_arkusz_c_po_sporzadzeniu(self):
        o = self.przygotuj(self.jan, poprz_ocena="brak", wniosek_stopien="tak", umotywowanie_wniosku="Wyróżniające wyniki")
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:wydruk", args=[o.pk]))
        self.assertContains(r, "Załącznik nr 4")
        self.assertContains(r, "ARKUSZ C")
        self.assertContains(r, "Komórka organizacyjna")
        self.assertContains(r, "Organizacja pracy i orientacja na osiąganie celów")
        self.assertContains(r, "7,00")
        self.assertContains(r, "powyżej 6 punktów do 8 punktów")
        self.assertContains(r, "CZĘŚĆ III")
        self.assertContains(r, "trzeciego")  # posiadany stopień 2 → wniosek o trzeci
        self.assertContains(r, "brak")  # trzecie pole kryterium dodatkowego
        self.assertContains(r, "Kreatywność")

    def test_bez_czesci_iii_dla_pracownika(self):
        o = self.przygotuj(self.piotr)
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:wydruk", args=[o.pk]))
        self.assertNotContains(r, "CZĘŚĆ III")
        self.assertContains(r, "NIE DOTYCZY")

    def test_kopia_czesci_i_i_arkusz_b(self):
        o = Ocena.objects.get(oceniany=self.anna)
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:wydruk", args=[o.pk]) + "?czesc=I")
        self.assertContains(r, "Załącznik nr 3")
        self.assertContains(r, "Zarządzanie ludźmi")
        self.assertNotContains(r, "CZĘŚĆ II")

    def test_cudzy_wydruk_niedostepny(self):
        o = Ocena.objects.get(oceniany=self.piotr)
        self.client.force_login(self.jan)
        self.assertEqual(self.client.get(reverse("oceny:wydruk", args=[o.pk])).status_code, 404)
