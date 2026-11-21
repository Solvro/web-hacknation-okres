from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, Pracownik, ZegarDemo


@override_settings(OKRES_DEMO=True)
class CzescIIiIIITest(TestCase):
    def setUp(self):
        ZegarDemo(data=date(2026, 11, 23)).save()
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        Pracownik.objects.create(user=self.jan, stanowisko="Starszy specjalista", rodzaj_stanowiska="pozostale",
                                 urzednik=True, rok_mianowania=2019, stopien_sluzbowy=2, data_stopnia=date(2021, 5, 4))
        self.o = Ocena.objects.create(oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2024, 12, 2))
        self.o.zatwierdz_kryteria(date(2024, 12, 10))
        self.o.potwierdz_kryteria()
        self.komplet = {k: 7 for k in self.o.wszystkie_kryteria()}
        self.dzis = date(2026, 11, 23)

    def test_domyslne_okres_i_dane_urzednika(self):
        d = self.o.domyslne_pola()
        self.assertEqual(d["okres_od"], self.dzis)  # przypis 6: data zapoznania ocenianego z kryteriami
        self.assertEqual(d["okres_do"], self.dzis)  # przed terminem: data bieżąca
        self.assertEqual((d["rok_mianowania"], d["stopien_sluzbowy"]), (2019, 2))

    def test_urzednik_musi_wskazac_poprzednia_i_wniosek(self):
        bledy = self.o.bledy_formalne(self.komplet, self.dzis, "", "Kurs")
        self.assertEqual(set(bledy), {"poprz_ocena", "wniosek_stopien"})
        bledy = self.o.bledy_formalne(self.komplet, self.dzis, "", "Kurs", poprz_ocena="pozytywna")
        self.assertIn("poprz_ocena", bledy)  # brak poziomu i daty

    def test_wniosek_tak_wymaga_umotywowania_i_oceny_pozytywnej(self):
        pola = dict(poprz_ocena="brak", wniosek_stopien="tak")
        self.assertIn("umotywowanie_wniosku", self.o.bledy_formalne(self.komplet, self.dzis, "", "Kurs", **pola))
        negatywna = self.komplet | {"rzetelnosc": 1}
        bledy = self.o.bledy_formalne(negatywna, self.dzis, "Uzas.", "Kurs", umotywowanie_wniosku="x", **pola)
        self.assertIn("wniosek_stopien", bledy)

    def test_dziewiaty_stopien(self):
        bledy = self.o.bledy_formalne(self.komplet, self.dzis, "", "Kurs", poprz_ocena="brak", wniosek_stopien="tak",
                                      stopien_sluzbowy=9, umotywowanie_wniosku="x")
        self.assertIn("najwyższy możliwy stopień", bledy["stopien_sluzbowy"])

    def test_sporzadzenie_z_wnioskiem(self):
        self.o.sporzadz(self.komplet, self.dzis, "", "Kurs", poprz_ocena="brak", wniosek_stopien="tak",
                        umotywowanie_wniosku="Prowadzi wdrożenie nowych procedur.", miejscowosc="Bydgoszcz")
        self.o.refresh_from_db()
        self.assertEqual(self.o.wniosek_stopien, "tak")
        self.assertEqual(self.o.stopien_sluzbowy, 2)
        self.assertEqual(self.o.okres_od, self.dzis)
        self.assertIsNone(self.o.poprz_data)

    def test_pracownik_nie_dotyczy(self):
        self.jan.pracownik.urzednik = False
        self.jan.pracownik.save()
        self.assertEqual(self.o.bledy_formalne(self.komplet, self.dzis, "", "Kurs"), {})
        self.o.sporzadz(self.komplet, self.dzis, "", "Kurs", wniosek_stopien="tak", stopien_sluzbowy=3)
        self.assertEqual((self.o.wniosek_stopien, self.o.stopien_sluzbowy), ("nie_dotyczy", None))

    def test_okres_z_przyszlosci(self):
        bledy = self.o.bledy_formalne(self.komplet, self.dzis, "", "Kurs", okres_do=date(2026, 12, 1))
        self.assertIn("okres", bledy)

    def test_rozmowa_oceniajaca_przed_rozmowa_o_kryteriach(self):
        self.assertIn("data_rozmowy", self.o.bledy_formalne(self.komplet, date(2024, 12, 9), "", "Kurs"))

    def test_poprzednia_z_historii(self):
        nastepna = Ocena.objects.create(oceniany=self.jan, oceniajacy=self.anna, poprzednia=self.o,
                                        poczatek_okresu=self.dzis, podstawa_poczatku="poprzednia_ocena")
        self.o.sporzadz(self.komplet, self.dzis, "", "Kurs", poprz_ocena="brak", wniosek_stopien="nie")
        self.assertEqual(nastepna.poprzednia_z_historii(),
                         {"poprz_ocena": "pozytywna", "poprz_poziom": "powyżej oczekiwań", "poprz_data": self.dzis})

    def test_widok_formularza(self):
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertContains(r, "Okres podlegania ocenie")
        self.assertContains(r, 'value="2026-11-23"')
        dane = {f"kryterium_{k}": "7" for k in self.komplet} | {
            "data_rozmowy": "2026-11-23", "okres_od": "2024-12-10", "okres_do": "2026-11-23", "wnioski_iprz": "Kurs",
            "poprz_ocena": "brak", "wniosek_stopien": "tak", "rok_mianowania": "2019", "stopien_sluzbowy": "2",
            "data_stopnia": "2021-05-04", "umotywowanie_wniosku": "Wyróżniające wyniki", "miejscowosc": "Bydgoszcz"}
        r = self.client.post(reverse("oceny:sporzadz", args=[self.o.pk]), dane)
        self.assertContains(r, "Część III")
        self.assertContains(r, "Wnioskowany stopień: 3")
