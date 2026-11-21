from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, ZegarDemo


@override_settings(OKRES_DEMO=True)
class ObserwacjeTest(TestCase):
    def setUp(self):
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.kadry = User.objects.create_user("kadry", is_staff=True)
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))
        ZegarDemo(data=date(2026, 11, 23)).save()

    def test_prywatnosc_notatek(self):
        prywatna = self.o.dodaj_obserwacje(self.anna, date(2026, 5, 4), "Spóźniony raport kwartalny", "rzetelnosc")
        wspolna = self.o.dodaj_obserwacje(self.anna, date(2026, 6, 1), "Skrócił obsługę wniosków", "organizacja_pracy",
                                          "Kolejka krótsza o 2 dni", udostepniona=True)
        osiagniecie = self.o.dodaj_obserwacje(self.jan, date(2026, 7, 1), "Przeszkoliłem dwie osoby", "wspolpraca")
        self.assertEqual(self.o.obserwacje_dla(self.anna), [prywatna, wspolna, osiagniecie])
        self.assertEqual(self.o.obserwacje_dla(self.jan), [wspolna, osiagniecie])
        self.assertEqual(self.o.obserwacje_dla(self.kadry), [])

    def test_grupowanie_wg_kryteriow_z_pustymi(self):
        self.o.dodaj_obserwacje(self.anna, date(2026, 5, 4), "Rzetelny audyt", "rzetelnosc")
        grupy = {kod: obs for kod, _, obs in self.o.obserwacje_wg_kryteriow(self.anna)}
        self.assertEqual(len(grupy["rzetelnosc"]), 1)
        self.assertEqual(grupy["komunikacja"], [])

    def test_walidacja(self):
        with self.assertRaises(ValidationError):
            self.o.dodaj_obserwacje(self.anna, date(2025, 1, 1), "Sprzed okresu")
        with self.assertRaises(ValidationError):
            self.o.dodaj_obserwacje(self.anna, date(2026, 11, 24), "Z przyszłości")
        with self.assertRaises(ValidationError):
            self.o.dodaj_obserwacje(self.anna, None, "x", "zarzadzanie_ludzmi")  # nie należy do arkusza C
        with self.assertRaises(PermissionDenied):
            self.o.dodaj_obserwacje(self.kadry, None, "Obca osoba")

    def test_widok_i_podpowiedz(self):
        self.client.force_login(self.anna)
        r = self.client.post(reverse("oceny:dodaj_obserwacje", args=[self.o.pk]),
                             {"data": "2026-06-01", "kryterium": "rzetelnosc", "tresc": "Terminowe rozliczenie", "skutek": ""})
        self.assertContains(r, "Terminowe rozliczenie")
        self.assertContains(r, "(prywatna)")
        self.assertContains(r, "Zapytaj w rozmowie o przykład")  # inne kryteria bez obserwacji
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertNotContains(r, "Terminowe rozliczenie")

    def test_widok_odrzuca_date_spoza_okresu_i_nieczytelna(self):
        """QA H3: data sprzed okresu, z przyszłości i nieczytelna dają komunikat, nic się nie zapisuje."""
        self.client.force_login(self.anna)
        url = reverse("oceny:dodaj_obserwacje", args=[self.o.pk])
        for data, komunikat in (("1999-01-01", "sprzed początku okresu"), ("2030-05-05", "z przyszłości"),
                                ("xyz", "Nie rozpoznano daty"), ("31.02.2026", "Nie rozpoznano daty")):
            r = self.client.post(url, {"data": data, "tresc": "Notatka testowa"})
            self.assertContains(r, komunikat)
        self.assertFalse(self.o.obserwacje.exists())

    def test_widok_przyjmuje_date_polska_i_pusta_jako_dzis(self):
        self.client.force_login(self.anna)
        url = reverse("oceny:dodaj_obserwacje", args=[self.o.pk])
        self.client.post(url, {"data": "04.05.2026", "tresc": "Format polski"})
        self.client.post(url, {"data": "", "tresc": "Bez daty"})
        self.assertEqual([o.data for o in self.o.obserwacje.all()], [date(2026, 5, 4), date(2026, 11, 23)])

    def test_formularz_ogranicza_zakres_daty(self):
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertContains(r, 'min="2025-03-17"')
        self.assertContains(r, 'max="2026-11-23"')
