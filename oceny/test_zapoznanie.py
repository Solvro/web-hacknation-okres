from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, ZegarDemo


def ustaw_zegar(d):
    ZegarDemo(data=d).save()


@override_settings(OKRES_DEMO=True)
class ZapoznanieSprzeciwTest(TestCase):
    def setUp(self):
        self.oceniany = User.objects.create_user("jan.testowy")
        self.oceniajacy = User.objects.create_user("anna.syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.oceniany, oceniajacy=self.oceniajacy, poczatek_okresu=date(2025, 3, 17))
        ustaw_zegar(date(2026, 11, 2))  # poniedziałek
        self.o.zatwierdz_kryteria(date(2025, 4, 1))
        self.o.potwierdz_kryteria()
        self.komplet = {k: 5 for k in self.o.wszystkie_kryteria()}

    def sporzadz(self, czastkowe=None, uzasadnienie=""):
        self.o.sporzadz(czastkowe or self.komplet, date(2026, 11, 2), uzasadnienie, "Szkolenie")

    def test_zapoznanie_przed_sporzadzeniem_niemozliwe(self):
        with self.assertRaises(PermissionDenied):
            self.o.potwierdz_zapoznanie()

    def test_termin_sprzeciwu_z_przesunieciem_na_roboczy(self):
        self.sporzadz()
        ustaw_zegar(date(2026, 11, 4))
        self.o.potwierdz_zapoznanie()
        self.assertEqual(self.o.data_zapoznania, date(2026, 11, 4))
        self.assertEqual(self.o.termin_sprzeciwu, date(2026, 11, 12))  # 11.11 święto

    def test_sprzeciw_w_terminie_i_po_terminie(self):
        self.sporzadz()
        self.o.potwierdz_zapoznanie()  # 2.11 → termin 9.11
        ustaw_zegar(date(2026, 11, 10))
        with self.assertRaises(PermissionDenied):
            self.o.zloz_sprzeciw("Nie zgadzam się z oceną kryterium rzetelność.")
        ustaw_zegar(date(2026, 11, 9))
        s = self.o.zloz_sprzeciw("Nie zgadzam się z oceną kryterium rzetelność.")
        self.assertEqual(s.data_zlozenia, date(2026, 11, 9))
        with self.assertRaises(PermissionDenied):
            self.o.zloz_sprzeciw("drugi")

    def test_fikcja_wymaga_opisu(self):
        self.sporzadz()
        with self.assertRaises(ValidationError):
            self.o.odnotuj_fikcje_zapoznania("  ")
        self.o.odnotuj_fikcje_zapoznania("Przekazano osobiście, odmowa podpisu")
        self.assertEqual(self.o.sposob_zapoznania, "fikcja")
        with self.assertRaises(PermissionDenied):
            self.o.potwierdz_zapoznanie()

    def test_terminy_po_negatywnej(self):
        self.sporzadz(self.komplet | {"rzetelnosc": 1}, "Uzasadnienie testowe")
        self.assertEqual(self.o.terminy_po_negatywnej(), {"kryteria_nowego_okresu": date(2026, 11, 9)})
        ustaw_zegar(date(2026, 11, 5))
        self.o.potwierdz_zapoznanie()
        self.assertEqual(self.o.terminy_po_negatywnej()["ponowna_ocena"], date(2027, 5, 5))

    def test_widoki_i_role(self):
        self.sporzadz()
        url = reverse("oceny:potwierdz_zapoznanie", args=[self.o.pk])
        self.client.force_login(self.oceniajacy)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.oceniany)
        r = self.client.post(url)
        self.assertContains(r, "09.11.2026")
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertContains(r, "DEMO: zegar systemowy przesunięty")

    @override_settings(OKRES_DEMO=False)
    def test_zegar_ignorowany_poza_trybem_demo(self):
        from . import zegar
        self.assertIsNone(zegar.przesunieta())
