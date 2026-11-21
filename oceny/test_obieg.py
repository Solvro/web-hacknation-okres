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

    def test_formularz_zachowuje_wybor_i_cele_po_bledzie_daty(self):
        self.client.force_login(self.anna)
        url = reverse("oceny:zatwierdz_kryteria", args=[self.o.pk])
        dane = {"data_rozmowy": "2025-04-02", "kryteria": ["kreatywnosc", "", ""],
                "cele_i_oczekiwania": "Skrócić czas obsługi skarg."}

        r = self.client.post(url, dane, headers={"HX-Request": "true"})
        self.assertContains(r, "Rozmowa nie może mieć daty z przyszłości.")
        self.assertContains(r, '<option value="kreatywnosc" selected>Kreatywność</option>', html=True)
        self.assertContains(r, dane["cele_i_oczekiwania"])
        self.o.refresh_from_db()
        self.assertEqual(self.o.kryteria_dodatkowe, [])
        self.assertFalse(self.o.kryteria_zatwierdzone)

        r = self.client.post(url, dane | {"data_rozmowy": "2025-04-01"}, headers={"HX-Request": "true"})
        self.assertContains(r, "Oczekuje na potwierdzenie ocenianego.")
        self.assertContains(r, 'hx-swap-oob="true"')
        self.o.refresh_from_db()
        self.assertEqual(self.o.kryteria_dodatkowe, ["kreatywnosc"])
        self.assertEqual(self.o.cele_i_oczekiwania, dane["cele_i_oczekiwania"])

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


@override_settings(OKRES_DEMO=True)
class PowiadomieniaTest(TestCase):
    def setUp(self):
        ZegarDemo(data=date(2026, 11, 23)).save()
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        self.kadry = User.objects.create_user("kadry", is_staff=True)
        self.dg = User.objects.create_user("dg", first_name="Dorota", last_name="Generalna")
        Pracownik.objects.create(user=self.dg, stanowisko="Dyrektor generalny", rodzaj_stanowiska="kierujacy",
                                 dyrektor_generalny=True)
        self.prac = Pracownik.objects.create(user=self.jan, stanowisko="Starszy specjalista", rodzaj_stanowiska="pozostale",
                                             urzednik=True, rok_mianowania=2019, stopien_sluzbowy=2,
                                             data_stopnia=date(2021, 5, 4))
        self.o = Ocena.objects.create(oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 16))

    def test_wniosek_o_stopien_powiadamia_dg_i_kadry(self):
        self.o.zatwierdz_kryteria(date(2025, 3, 20))
        self.o.potwierdz_kryteria()
        komplet = {k: 7 for k in self.o.wszystkie_kryteria()}
        self.o.sporzadz(komplet, date(2026, 11, 23), "", "Kurs", poprz_ocena="brak", wniosek_stopien="tak",
                        umotywowanie_wniosku="Prowadzi wdrożenie nowych procedur.")
        odbiorcy = set(self.o.przypomnienia.filter(klucz__startswith="wniosek_stopien").values_list("odbiorca__username",
                                                                                                    flat=True))
        self.assertEqual(odbiorcy, {"dg", "kadry"})
        tresc = self.o.przypomnienia.get(odbiorca=self.dg, klucz__startswith="wniosek_stopien").tresc
        self.assertIn("3. stopnia służbowego", tresc)
        self.assertIn("art. 89 ust. 1", tresc)
        self.client.force_login(self.dg)  # DG widzi sprawę, o której dostał powiadomienie
        self.assertEqual(self.client.get(reverse("oceny:szczegoly", args=[self.o.pk])).status_code, 200)

    def test_bez_wniosku_bez_powiadomienia_i_dg_nie_widzi_sprawy(self):
        self.o.zatwierdz_kryteria(date(2025, 3, 20))
        self.o.potwierdz_kryteria()
        self.o.sporzadz({k: 7 for k in self.o.wszystkie_kryteria()}, date(2026, 11, 23), "", "Kurs",
                        poprz_ocena="brak", wniosek_stopien="nie")
        self.assertFalse(self.o.przypomnienia.filter(klucz__startswith="wniosek_stopien").exists())
        self.client.force_login(self.dg)
        self.assertEqual(self.client.get(reverse("oceny:szczegoly", args=[self.o.pk])).status_code, 404)

    def test_nieobecnosc_przesuwajaca_termin_powiadamia_strony(self):
        from .models import Nieobecnosc

        self.assertEqual(self.o.termin_oceny, date(2027, 3, 16))
        Nieobecnosc.objects.create(pracownik=self.prac, od=date(2026, 10, 5), do=date(2026, 10, 16))
        self.assertFalse(self.o.przypomnienia.exists())  # 12 dni: termin bez zmian
        n = Nieobecnosc.objects.create(pracownik=self.prac, od=date(2026, 10, 19), do=date(2026, 11, 6))
        p = self.o.przypomnienia.filter(klucz__startswith="termin_nieobecnosc")
        self.assertEqual(set(p.values_list("odbiorca__username", flat=True)), {"jan", "anna"})
        self.assertIn("z 16.03.2027 na 19.04.2027", p.first().tresc)
        self.assertEqual(p.first().termin, date(2027, 4, 19))
        n.save()  # ponowny zapis bez zmiany: bez duplikatów
        self.assertEqual(p.count(), 2)
        n.delete()  # usunięcie przywraca termin: nowe powiadomienie
        self.assertTrue(self.o.przypomnienia.filter(tresc__contains="z 19.04.2027 na 16.03.2027").exists())

    def test_nieobecnosc_nie_dotyczy_sporzadzonej_oceny(self):
        from .models import Nieobecnosc

        self.o.zatwierdz_kryteria(date(2025, 3, 20))
        self.o.potwierdz_kryteria()
        self.o.sporzadz({k: 5 for k in self.o.wszystkie_kryteria()}, date(2026, 11, 23), "", "Kurs",
                        poprz_ocena="brak", wniosek_stopien="nie")
        Nieobecnosc.objects.create(pracownik=self.prac, od=date(2026, 9, 1), do=date(2026, 10, 30))
        self.assertFalse(self.o.przypomnienia.filter(klucz__startswith="termin_nieobecnosc").exists())
