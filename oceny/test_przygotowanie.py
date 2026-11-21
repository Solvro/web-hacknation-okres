from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from . import scheduler
from .models import Ocena, ZegarDemo


@override_settings(OKRES_DEMO=True)
class PrzygotowanieIStopienTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=date(2026, 11, 21)).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        cls.jan = User.objects.get(username="oceniany")
        cls.anna = User.objects.get(username="oceniajaca")
        cls.dg = User.objects.get(username="dyrektor")

    def test_przygotowanie_do_rozmowy(self):
        o = Ocena.objects.get(oceniany=self.jan)
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:przygotowanie", args=[o.pk, "oceniajaca"]))
        self.assertContains(r, "Który etap sprawy udało się skrócić i co pomogło?")
        self.assertContains(r, "Raport kwartalny złożony 5 dni po terminie")  # prywatna notatka autorki
        self.assertContains(r, "Trudne sytuacje")
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:przygotowanie", args=[o.pk, "oceniajaca"]))
        self.assertNotContains(r, "Raport kwartalny złożony 5 dni po terminie")  # nie widzi prywatnej notatki
        self.assertNotContains(r, "Trudne sytuacje")
        self.client.force_login(self.dg)
        self.assertEqual(self.client.get(reverse("oceny:przygotowanie", args=[o.pk, "oceniajaca"])).status_code, 404)

    def _ocena(self, poprzednia, punkty, data):
        o = Ocena.objects.create(oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2022, 1, 3), poprzednia=poprzednia)
        o.zatwierdz_kryteria(date(2022, 1, 10))
        o.potwierdz_kryteria()
        komplet = {k: punkty for k in o.wszystkie_kryteria()}
        o.sporzadz(komplet, data, "", "Szkolenie", poprz_ocena="brak", wniosek_stopien="nie", okres_od=date(2022, 1, 10),
                   okres_do=data)
        o.potwierdz_zapoznanie()
        return o

    def test_obligatoryjny_stopien(self):
        p = self.jan.pracownik
        p.data_stopnia = date(2022, 1, 1)
        p.save()
        pierwsza = self._ocena(None, 7, date(2024, 1, 8))
        self.assertIsNone(pierwsza.obligatoryjny_stopien())
        druga = self._ocena(pierwsza, 9, date(2026, 11, 21))
        st = druga.obligatoryjny_stopien()
        self.assertEqual((st["stopien"], st["termin"]), (3, date(2026, 12, 21)))
        self.assertEqual(scheduler.przypomnienie_o_stopniu(druga), 1)
        self.assertTrue(self.dg.przypomnienia.filter(tresc__contains="art. 89 ust. 2").exists())

    def test_brak_obowiazku_przy_poziomie_oczekiwan(self):
        pierwsza = self._ocena(None, 5, date(2024, 1, 8))
        druga = self._ocena(pierwsza, 9, date(2026, 11, 21))
        self.assertIsNone(druga.obligatoryjny_stopien())
