from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from . import rules
from .models import Ocena, Urzad, ZegarDemo


class PakietyRegulTest(SimpleTestCase):
    def test_wszystkie_pakiety_poprawne(self):
        for w in rules.dostepne_wersje():
            with self.subTest(w["kod"]):
                self.assertEqual(rules.sprawdz(w["kod"]), [])

    def test_dziedziczenie(self):
        sym = rules.load("symulacja-12m")
        self.assertEqual(sym["terminy"]["okres_oceny_miesiace"], 12)
        self.assertEqual(sym["terminy"]["sprzeciw_dni"], 7)  # odziedziczone
        self.assertEqual(len(sym["kryteria"]), 14)

    def test_bledny_przyklad_wykryty(self):
        self.assertTrue(rules.sprawdz("nieistniejacy"))

    def test_komenda(self):
        out = StringIO()
        call_command("sprawdz_reguly", stdout=out)
        self.assertIn("✓ 2016-04-04", out.getvalue())
        self.assertIn("✓ symulacja-12m", out.getvalue())


@override_settings(OKRES_DEMO=True)
class AktywnaWersjaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=date(2026, 11, 21)).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())

    def test_nowe_sprawy_dostaja_aktywna_wersje_a_stare_zachowuja(self):
        jan = User.objects.get(username="oceniany")
        stara = Ocena.objects.get(oceniany=jan)
        u = Urzad.biezacy()
        u.wersja_regul = "symulacja-12m"
        u.full_clean()
        u.save()
        nowa = Ocena.objects.create(oceniany=jan, oceniajacy=stara.oceniajacy, poczatek_okresu=date(2025, 3, 16))
        self.assertEqual(nowa.wersja_regul, "symulacja-12m")
        stara.refresh_from_db()
        self.assertEqual(stara.wersja_regul, "2016-04-04")
        self.assertEqual(stara.termin_oceny, date(2027, 4, 19))
        # cykl 12 mies.: 16.03.2026 (poniedziałek); nieobecność z października 2026 wypada po terminie
        self.assertEqual(nowa.termin_oceny, date(2026, 3, 16))

    def test_nieznany_pakiet_odrzucony(self):
        u = Urzad.biezacy()
        u.wersja_regul = "2030-01-01"
        with self.assertRaises(ValidationError):
            u.full_clean()

    def test_porownanie(self):
        jan = User.objects.get(username="oceniany")
        o = Ocena.objects.get(oceniany=jan)
        self.client.force_login(jan)
        r = self.client.get(reverse("oceny:porownanie_regul", args=[o.pk]))
        self.assertContains(r, "19.04.2027")
        self.assertContains(r, "16.03.2026")
        self.assertContains(r, "symulacja")
