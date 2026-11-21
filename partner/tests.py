from datetime import date, timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from oceny.models import ZegarDemo

from . import sygnaly
from .models import Docenienie, Uzgodnienie, ZdarzenieZadania

DZIS = date(2026, 11, 21)


@override_settings(OKRES_DEMO=True)
class HRPartnerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=DZIS).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        cls.anna = User.objects.get(username="oceniajaca")
        cls.piotr = User.objects.get(username="piotr").pracownik
        cls.jan = User.objects.get(username="oceniany").pracownik
        cls.kadry = User.objects.get(username="kadry")

    def rodzaje(self, p):
        return {s.rodzaj: s for s in sygnaly.dla_pracownika(p)}

    def test_trzy_zmiany_priorytetu_ze_zrodlami(self):
        s = self.rodzaje(self.piotr)["zmiany_priorytetu"]
        self.assertEqual(s.tytul, "3 zmiany priorytetu zadań w ciągu 6 tygodni")
        self.assertEqual(len(s.zrodla), 3)
        self.assertEqual(s.pytanie, "Który termin możemy wspólnie przesunąć?")

    def test_ponizej_progu_brak_sygnalu(self):
        ZdarzenieZadania.objects.filter(pracownik=self.piotr, rodzaj="zmiana_priorytetu").first().delete()
        self.assertNotIn("zmiany_priorytetu", self.rodzaje(self.piotr))

    def test_powrot_po_nieobecnosci_bez_przyczyny(self):
        s = self.rodzaje(self.jan)["powrot_po_nieobecnosci"]
        self.assertIn("33 dniach", s.tytul)
        self.assertIn("bez przyczyny", s.zrodla[0])

    def test_osiagniecie_czeka_na_docenienie_i_znika_po_docenieniu(self):
        s = self.rodzaje(self.jan)["osiagniecie_bez_docenienia"]
        Docenienie.dodaj(self.anna, self.jan, "Szkolenie nowych osób", "Ciągłość rejestru", obserwacja_id_lookup(s))
        self.assertNotIn("osiagniecie_bez_docenienia", self.rodzaje(self.jan))

    def test_uzgodnienie_zamyka_sygnal_i_pracownik_widzi(self):
        s = self.rodzaje(self.piotr)["zmiany_priorytetu"]
        u = Uzgodnienie.zapisz(self.anna, self.piotr, s.klucz, "odciazenie", "Sprawozdanie przejmuje Jan do 15.12.",
                               DZIS + timedelta(days=21))
        self.assertNotIn("zmiany_priorytetu", self.rodzaje(self.piotr))
        u.dopisz_perspektywe(self.piotr.user, "Potrzebuję też stałej kolejności zadań.")
        with self.assertRaises(PermissionDenied):
            u.dopisz_perspektywe(self.anna, "x")
        u.zapisz_wynik(self.anna, "pomoglo", "Kolejka bez zaległości")
        self.assertEqual(u.get_wynik_display(), "pomogło")

    def test_uprawnienia(self):
        with self.assertRaises(PermissionDenied):
            ZdarzenieZadania.dodaj(self.jan.user, self.piotr, DZIS, "nowe_zadanie", "x")  # nie jest przełożonym
        with self.assertRaises(ValidationError):
            ZdarzenieZadania.dodaj(self.anna, self.piotr, DZIS, "wymyslone", "x")
        with self.assertRaises(ValidationError):
            Uzgodnienie.zapisz(self.anna, self.piotr, "k", "spoza_katalogu", "x", DZIS)

    def test_widoki(self):
        self.client.force_login(self.anna)
        r = self.client.get(reverse("partner:zespol"))
        self.assertContains(r, "3 zmiany priorytetu")
        self.assertContains(r, "Który termin możemy wspólnie przesunąć?")
        self.client.force_login(self.piotr.user)
        r = self.client.get(reverse("partner:moje"))
        self.assertContains(r, "3 zmiany priorytetu")  # pracownik widzi to samo co przełożony
        self.assertEqual(self.client.post(reverse("partner:dodaj_zdarzenie", args=[self.jan.pk]),
                                          {"rodzaj": "nowe_zadanie", "opis": "x"}).status_code, 404)
        self.client.force_login(self.kadry)
        self.assertNotContains(self.client.get(reverse("partner:zespol")), "zmiany priorytetu")


def obserwacja_id_lookup(s):
    from oceny.models import Obserwacja
    return Obserwacja.objects.get(pk=s.obserwacja_id)
