from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, ZegarDemo
from .pomoc_testow import sprawa_od_kryteriow


def zegar(d):
    ZegarDemo(data=d).save()


@override_settings(OKRES_DEMO=True)
class ZdarzeniaKadroweTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        sprawa_od_kryteriow(User.objects.get(username="oceniany"))  # seed ma sprawy w toku
        cls.kadry = User.objects.get(username="kadry")
        cls.anna = User.objects.get(username="oceniajaca")
        cls.jan = User.objects.get(username="oceniany")
        cls.dg = User.objects.get(username="dyrektor")

    def setUp(self):
        zegar(date(2025, 6, 2))
        self.o = Ocena.objects.get(oceniany=self.jan)  # pierwsza ocena, początek 16.03.2025
        self.o.ustaw_kryteria(["kreatywnosc"])
        self.o.zatwierdz_kryteria(date(2025, 4, 1))
        self.o.potwierdz_kryteria()

    def test_zmiana_oceniajacego_kryteria_bez_zmian_i_dostep(self):
        self.o.zmien_oceniajacego(self.kadry, self.dg, date(2025, 6, 2), "Zmiana podległości")
        self.o.refresh_from_db()
        self.assertEqual(self.o.oceniajacy, self.dg)
        self.assertEqual(self.o.kryteria_dodatkowe, ["kreatywnosc"])
        self.assertTrue(self.o.kryteria_zablokowane)
        self.client.force_login(self.anna)
        self.assertEqual(self.client.get(reverse("oceny:szczegoly", args=[self.o.pk])).status_code, 404)
        self.assertTrue(self.dg.przypomnienia.filter(ocena=self.o).exists())
        with self.assertRaises(PermissionDenied):
            self.o.zmien_oceniajacego(self.anna, self.anna, None)

    def test_zmiana_stanowiska_w_ciagu_szesciu_miesiecy(self):
        # ustalenie kryteriów 01.04.2025 + 6 mies. = 01.10.2025; zmiana 01.10.2025 to jeszcze „w okresie 6 miesięcy”
        self.o.zmiana_stanowiska(self.kadry, date(2025, 10, 1), "Główny specjalista")
        self.o.refresh_from_db()
        self.assertFalse(self.o.kryteria_zatwierdzone)
        self.assertEqual(self.o.rachunek_kryteriow().termin, date(2025, 10, 31))
        self.assertEqual(self.o.termin_oceny, date(2027, 4, 19))  # termin oceny bez zmian (§ 9 ust. 1)
        self.assertEqual(self.jan.pracownik.__class__.objects.get(pk=self.jan.pracownik.pk).stanowisko, "Główny specjalista")

    def test_zmiana_stanowiska_po_szesciu_miesiacach(self):
        zegar(date(2025, 10, 2))
        self.o.zmiana_stanowiska(self.kadry, date(2025, 10, 2))  # dzień po progu: art. 81 ust. 6
        self.o.refresh_from_db()
        self.assertEqual(self.o.termin_oceny, date(2025, 11, 3))  # 01.11 sobota (i święto) → 03.11
        self.assertEqual(self.o.najwczesniej_sporzadzenia, date(2025, 9, 25))
        self.assertIn("art. 81 ust. 6", self.o.rachunek_oceny().kroki[-1].podstawa)

    def test_zmiana_terminu_przez_oceniajacego(self):
        with self.assertRaises(ValidationError):  # wniosek ocenianego przed upływem 6 miesięcy
            self.o.zmien_termin(self.anna, date(2027, 6, 1), "4")
        z = self.o.zmien_termin(self.anna, date(2027, 6, 1), "2", "Planowany urlop rodzicielski")
        self.assertEqual(self.o.termin_oceny, date(2027, 6, 1))
        self.assertEqual(z.dane["stary"], "2027-04-19")
        with self.assertRaises(PermissionDenied):
            self.o.zmien_termin(self.kadry, date(2027, 7, 1), "1")
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:zawiadomienie", args=[self.o.pk, z.pk]))
        self.assertContains(r, "01.06.2027")
        self.assertContains(r, "19.04.2027")
        self.assertContains(r, "§ 8")

    def test_widok_formularzy(self):
        self.client.force_login(self.kadry)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertContains(r, "Zmiana stanowiska z istotną zmianą obowiązków")
        r = self.client.post(reverse("oceny:zdarzenie_kadrowe", args=[self.o.pk, "stanowisko"]), {"data_zmiany": "2025-06-02"})
        self.assertContains(r, "ponowne ustalenie kryteriów")
        self.client.force_login(self.anna)
        r = self.client.post(reverse("oceny:zdarzenie_kadrowe", args=[self.o.pk, "termin"]),
                             {"podstawa": "3", "nowy_termin": "2027-05-04"})
        self.assertContains(r, "zawiadomienie (§ 8)")

    def test_kandydaci_na_oceniajacego_tylko_przelozeni(self):
        """QA M1: lista „Nowy oceniający” bez współpracowników, kadrowej i samego ocenianego."""
        piotr, kadrowa = User.objects.get(username="piotr"), User.objects.get(username="kadry")
        kandydaci = self.o.kandydaci_na_oceniajacego()
        self.assertIn(self.dg, kandydaci)
        self.assertIn(User.objects.get(username="finanse"), kandydaci)
        for nie in (piotr, kadrowa, self.jan, self.anna):
            self.assertNotIn(nie, kandydaci)
        with self.assertRaises(ValidationError) as e:
            self.o.zmien_oceniajacego(self.kadry, piotr, date(2025, 6, 2))
        self.assertIn("stanowisku kierowniczym", str(e.exception))
        self.client.force_login(self.kadry)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertEqual(set(r.context["kandydaci"]), set(kandydaci))
