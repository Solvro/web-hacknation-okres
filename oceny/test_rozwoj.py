import copy
from datetime import date

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from . import rozwoj, rules
from .models import Ocena, ZegarDemo


class KatalogRozwojuTest(SimpleTestCase):
    def test_katalog_kompletny_dla_14_kryteriow(self):
        self.assertEqual(rozwoj.sprawdz(), [])
        self.assertEqual(set(rozwoj.katalog()["kryteria"]), set(rules.criteria()))
        self.assertEqual(len(rozwoj.katalog()["kryteria"]), 14)

    def test_walidacja_wykrywa_braki(self):
        dane = copy.deepcopy(rozwoj.katalog())
        del dane["kryteria"]["komunikacja"]
        dane["kryteria"]["rzetelnosc"]["dzialania"] = dane["kryteria"]["rzetelnosc"]["dzialania"][:1]
        dane["kryteria"]["wspolpraca"]["dzialania"][0]["forma"] = "wycieczka"
        dane["kryteria"]["kreatywnosc"]["mocna_strona"] = ""
        dane["kryteria"]["nieznane"] = {"dzialania": [], "mocna_strona": "x"}
        dane["mocna_strona_przy"] = [8]
        bledy = " ".join(rozwoj.sprawdz(dane))
        for fragment in ("komunikacja", "rzetelnosc", "wspolpraca", "kreatywnosc", "nieznane",
                         "mocna_strona_przy"):
            self.assertIn(fragment, bledy)

    def test_podpowiedzi_tylko_dla_skrajnych_ocen(self):
        kryteria = {"rzetelnosc": "Rzetelność", "komunikacja": "Komunikacja", "wspolpraca": "Współpraca"}
        p = rozwoj.podpowiedzi(kryteria, {"rzetelnosc": 3, "komunikacja": 9, "wspolpraca": 5})
        self.assertEqual([(x["kod"], x["rodzaj"]) for x in p], [("rzetelnosc", "rozwoj"), ("komunikacja", "mocna")])
        self.assertTrue(2 <= len(p[0]["dzialania"]) <= 3)
        self.assertTrue(p[0]["dzialania"][0]["do_iprz"].startswith("Rzetelność: "))


@override_settings(OKRES_DEMO=True)
class RozwojWFormularzuTest(TestCase):
    def setUp(self):
        ZegarDemo(data=date(2027, 3, 1)).save()
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))
        self.o.zatwierdz_kryteria(date(2025, 4, 1))
        self.o.potwierdz_kryteria()
        self.client.force_login(self.anna)

    def test_podglad_pokazuje_propozycje_i_mocna_strone(self):
        dane = {f"kryterium_{k}": "5" for k in self.o.wszystkie_kryteria()} | {"kryterium_rzetelnosc": "1",
                                                                               "kryterium_komunikacja": "9"}
        r = self.client.post(reverse("oceny:podglad_wyniku", args=[self.o.pk]), dane)
        self.assertContains(r, 'id="rozwoj"')
        self.assertContains(r, 'hx-swap-oob="true"')
        self.assertContains(r, "propozycje do wniosków IPRZ")
        self.assertContains(r, "data-wstaw-iprz=\"Rzetelność: ")
        self.assertContains(r, "mocna strona:")
        self.assertContains(r, "ocena negatywna")

    def test_system_nie_wpisuje_wnioskow_sam(self):
        dane = {f"kryterium_{k}": "3" for k in self.o.wszystkie_kryteria()} | {
            "data_rozmowy": "2027-03-01", "uzasadnienie": "Uzasadnienie.", "wnioski_iprz": ""}
        r = self.client.post(reverse("oceny:sporzadz", args=[self.o.pk]), dane)
        self.assertContains(r, "Wpisz wnioski do indywidualnego programu rozwoju zawodowego")
        self.o.refresh_from_db()
        self.assertFalse(self.o.sporzadzona)
        self.assertEqual(self.o.wnioski_iprz, "")
