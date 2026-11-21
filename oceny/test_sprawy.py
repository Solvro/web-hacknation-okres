from io import StringIO
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Nieobecnosc, Ocena, Pracownik, ZegarDemo


@override_settings(OKRES_DEMO=True)
class SprawyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        ZegarDemo(data=date(2026, 11, 23)).save()
        cls.jan = User.objects.get(username="oceniany")
        cls.anna = User.objects.get(username="oceniajaca")
        cls.o = Ocena.objects.get(oceniany=cls.jan)

    def test_arkusz_ze_stanowiska(self):
        self.assertEqual(self.o.arkusz, "C")
        self.assertEqual(Ocena.objects.get(oceniany=self.anna).arkusz, "B")
        self.assertEqual(Pracownik(rodzaj_stanowiska="kierownik_urzedu").arkusz, "A")

    def test_termin_oceny_ze_scenariusza_demo(self):
        # 16.03.2025 + 24 mies. = 16.03.2027; + 33 dni nieobecności = 18.04.2027 (niedziela) → 19.04.2027
        r = self.o.rachunek_oceny()
        self.assertEqual(r.termin, date(2027, 4, 19))
        self.assertIn("33 dni", " ".join(k.opis for k in r.kroki))
        self.assertIn("dzień wolny", r.kroki[-1].opis)

    def test_termin_kryteriow(self):
        self.assertEqual(self.o.rachunek_kryteriow().termin, date(2025, 4, 15))

    def test_nieobecnosc_od_konca_przed_poczatkiem(self):
        with self.assertRaises(ValidationError):
            Nieobecnosc(pracownik=self.jan.pracownik, od=date(2026, 1, 10), do=date(2026, 1, 5)).full_clean()

    def test_nastepne_kroki(self):
        self.assertEqual(self.o.nastepny_krok(self.anna)["opis"], "Przeprowadź rozmowę i wyznacz kryteria")
        self.assertTrue(self.o.nastepny_krok(self.anna)["moj"])
        self.assertFalse(self.o.nastepny_krok(self.jan)["moj"])
        self.o.zatwierdz_kryteria(date(2026, 11, 20), "Bydgoszcz")
        self.assertTrue(self.o.nastepny_krok(self.jan)["moj"])
        self.o.potwierdz_kryteria()
        self.assertEqual(self.o.etap, "ocena")
        self.assertEqual(self.o.nastepny_krok(self.anna)["termin"], date(2027, 4, 19))

    def test_rozmowa_z_przyszlosci_odrzucona(self):
        with self.assertRaises(ValidationError):
            self.o.zatwierdz_kryteria(date(2026, 11, 24))

    def test_moje_sprawy_widocznosc(self):
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:moje_sprawy"))
        self.assertContains(r, "Jan Testowy")
        self.assertNotContains(r, "Piotr Przykładowy")
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:moje_sprawy") + "?filtr=moje")
        self.assertContains(r, "Piotr Przykładowy")
        self.assertNotContains(r, "Anna Syntetyczna</a>")  # jej własna sprawa nie wymaga jej działania
        self.client.force_login(User.objects.get(username="kadry"))
        self.assertContains(self.client.get(reverse("oceny:moje_sprawy")), "Anna Syntetyczna")

    def test_jak_obliczono(self):
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:jak_obliczono", args=[self.o.pk, "ocena"]))
        self.assertContains(r, "19.04.2027")
        self.assertContains(r, "art. 81 ust. 7")

    def test_szybkie_logowanie_tylko_demo(self):
        r = self.client.post(reverse("demo_zaloguj"), {"login": "oceniany"})
        self.assertRedirects(r, reverse("oceny:moje_sprawy"))
        self.assertEqual(self.client.post(reverse("demo_zaloguj"), {"login": "admin"}).status_code, 403)
        with self.settings(OKRES_DEMO=False):
            self.assertEqual(self.client.post(reverse("demo_zaloguj"), {"login": "oceniany"}).status_code, 403)

    def test_strona_sprawy_i_logowania(self):
        self.assertContains(self.client.get(reverse("login")), "Wybierz konto demonstracyjne")
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertContains(r, "DANE FIKCYJNE")
        self.assertContains(r, "Organizacja pracy i orientacja na osiąganie celów")
        self.assertContains(r, "19.04.2027")


@override_settings(OKRES_DEMO=True)
class PoTerminieTest(TestCase):
    def test_oznaczenie_po_terminie(self):
        jan = User.objects.create_user("jan")
        anna = User.objects.create_user("anna")
        o = Ocena.objects.create(arkusz="C", oceniany=jan, oceniajacy=anna, poczatek_okresu=date(2025, 3, 17))
        ZegarDemo(data=date(2025, 4, 16)).save()  # termin kryteriów 16.04.2025
        self.assertFalse(o.po_terminie)
        ZegarDemo(data=date(2025, 4, 17)).save()
        self.assertTrue(o.po_terminie)
