"""Braki w obiegu: cele i oczekiwania z części I, powiadomienia o wniosku o stopień i o przesunięciu terminu."""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, Pracownik, ZegarDemo


@override_settings(OKRES_DEMO=True)
class CeleIOczekiwaniaTest(TestCase):
    def setUp(self):
        ZegarDemo(data=date(2025, 4, 1)).save()
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))

    def test_zapis_w_czesci_i_i_widok_dla_obu_stron(self):
        self.client.force_login(self.anna)
        r = self.client.post(reverse("oceny:zatwierdz_kryteria", args=[self.o.pk]),
                             {"data_rozmowy": "2025-03-31", "miejscowosc": "Bydgoszcz",
                              "cele_i_oczekiwania": "Obsługa wniosku w 14 dni; lista kontrolna."})
        self.assertContains(r, "Obsługa wniosku w 14 dni")
        self.o.refresh_from_db()
        self.assertEqual(self.o.cele_i_oczekiwania, "Obsługa wniosku w 14 dni; lista kontrolna.")
        self.client.force_login(self.jan)
        self.assertContains(self.client.get(reverse("oceny:szczegoly", args=[self.o.pk])), "Obsługa wniosku w 14 dni")

    def test_cele_wracaja_w_przygotowaniu_do_rozmowy_oceniajacej(self):
        self.o.zatwierdz_kryteria(date(2025, 3, 31), cele="Skrócić kolejkę o połowę.")
        self.client.force_login(self.jan)
        r = self.client.get(reverse("oceny:przygotowanie", args=[self.o.pk, "oceniajaca"]))
        self.assertContains(r, "Skrócić kolejkę o połowę.")
        self.assertContains(r, "§ 10 pkt 2")

    def test_bez_celow_jawna_informacja(self):
        self.o.zatwierdz_kryteria(date(2025, 3, 31))
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:przygotowanie", args=[self.o.pk, "oceniajaca"]))
        self.assertContains(r, "nie zapisano celów")

    def test_zmiana_stanowiska_w_6_miesiacach_czysci_cele_i_zachowuje_poprzednie(self):
        kadry = User.objects.create_user("kadry", is_staff=True)
        self.o.zatwierdz_kryteria(date(2025, 3, 31), cele="Stare cele.")
        self.o.potwierdz_kryteria()
        z = self.o.zmiana_stanowiska(kadry, date(2025, 4, 1))
        self.assertEqual(self.o.cele_i_oczekiwania, "")
        self.assertEqual(z.dane["poprzednie"]["cele_i_oczekiwania"], "Stare cele.")
