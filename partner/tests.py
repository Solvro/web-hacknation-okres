from datetime import date, timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from oceny.models import Obserwacja, ZegarDemo

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
        self.assertIn("szkolenie", dict(s.dzialania))  # zmiany przepisów i procedur w czasie nieobecności

    def test_osiagniecie_czeka_na_docenienie_i_znika_po_docenieniu(self):
        s = self.rodzaje(self.jan)["osiagniecie_bez_docenienia"]
        Docenienie.dodaj(self.anna, self.jan, "Szkolenie nowych osób", "Ciągłość rejestru", obserwacja_id_lookup(s))
        self.assertNotIn("osiagniecie_bez_docenienia", self.rodzaje(self.jan))

    def test_docenienie_nie_pyta_o_wpisany_skutek_i_ma_jeden_formularz(self):
        s = self.rodzaje(self.jan)["osiagniecie_bez_docenienia"]
        Obserwacja.objects.filter(pk=s.obserwacja_id).update(skutek="Ciągłość rejestru")
        s = self.rodzaje(self.jan)["osiagniecie_bez_docenienia"]
        self.assertNotIn("Jaki był skutek", s.pytanie)
        self.assertEqual(s.skutek, "Ciągłość rejestru")
        self.client.force_login(self.anna)
        karta = self.client.get(reverse("partner:zespol")).content.decode().split(f'id="karta-{self.jan.pk}"')[1].split("</section>")[0]
        self.assertIn("Skutek ze zgłoszenia: Ciągłość rejestru", karta)
        self.assertNotIn("Doceń bez sygnału", karta)
        Obserwacja.objects.filter(pk=s.obserwacja_id).update(skutek="")
        self.assertEqual(self.rodzaje(self.jan)["osiagniecie_bez_docenienia"].pytanie,
                         "Jaki był skutek tego działania dla zespołu lub interesantów?")

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

    def test_dziennik_odrzuca_nieczytelna_date(self):
        """QA H3: nieczytelna data nie zamienia się po cichu na dzisiejszą."""
        self.client.force_login(self.anna)
        przed = ZdarzenieZadania.objects.count()
        r = self.client.post(reverse("partner:dodaj_zdarzenie", args=[self.jan.pk]),
                             {"data": "xyz", "rodzaj": "nowe_zadanie", "opis": "Test"})
        self.assertContains(r, "Nie rozpoznano daty")
        self.assertEqual(ZdarzenieZadania.objects.count(), przed)


def obserwacja_id_lookup(s):
    from oceny.models import Obserwacja
    return Obserwacja.objects.get(pk=s.obserwacja_id)


@override_settings(OKRES_DEMO=True)
class SpadekZaangazowaniaTest(TestCase):
    def setUp(self):
        from oceny.models import Ocena, Pracownik

        ZegarDemo(data=DZIS).save()
        self.anna_u = User.objects.create_user("anna")
        self.anna = Pracownik.objects.create(user=self.anna_u, stanowisko="Naczelniczka", rodzaj_stanowiska="kierujacy")
        self.ewa_u = User.objects.create_user("ewa")
        self.ewa = Pracownik.objects.create(user=self.ewa_u, stanowisko="Specjalistka", rodzaj_stanowiska="pozostale",
                                            przelozony=self.anna)
        self.ocena = Ocena.objects.create(arkusz="C", oceniany=self.ewa_u, oceniajacy=self.anna_u,
                                          poczatek_okresu=date(2025, 1, 2))

    def sygnaly(self):
        return [s for s in sygnaly.dla_pracownika(self.ewa) if s.rodzaj == "mozliwy_spadek_zaangazowania"]

    def uzgodnienie(self, ustalenie, data, sprawdzenie):
        return Uzgodnienie.objects.create(pracownik=self.ewa, autor=self.anna_u, sygnal="k", dzialanie="odciazenie",
                                          ustalenie=ustalenie, data=data, data_sprawdzenia=sprawdzenie)

    def test_uzgodnienie_nie_pomoglo_daje_sygnal_ze_zrodlami(self):
        u = self.uzgodnienie("Rejestr przejmuje Jan.", DZIS - timedelta(days=30), DZIS - timedelta(days=5))
        self.assertEqual(self.sygnaly(), [])
        u.zapisz_wynik(self.anna_u, "nie_pomoglo", "Nadal zaległości")
        [s] = self.sygnaly()
        self.assertIn("nie pomogło", s.tytul)
        self.assertIn("Nadal zaległości", s.zrodla[1])
        self.assertIn("ani diagnoza", s.uwaga)
        self.assertNotIn("zdrow", " ".join(s.zrodla).lower())

    def test_stare_nieskuteczne_uzgodnienie_poza_oknem(self):
        u = self.uzgodnienie("x", DZIS - timedelta(days=90), DZIS - timedelta(days=61))
        u.zapisz_wynik(self.anna_u, "nie_pomoglo")
        self.assertEqual(self.sygnaly(), [])

    def test_wiele_nowych_zadan_bez_osiagniec(self):
        for d in (80, 60, 40, 20):
            ZdarzenieZadania.objects.create(pracownik=self.ewa, autor=self.anna_u, data=DZIS - timedelta(days=d),
                                            rodzaj="nowe_zadanie", opis=f"Zadanie {d}")
        self.assertEqual(self.sygnaly(), [])  # 4 zadania: poniżej progu
        ZdarzenieZadania.objects.create(pracownik=self.ewa, autor=self.anna_u, data=DZIS - timedelta(days=10),
                                        rodzaj="nowe_zadanie", opis="Zadanie 10")
        [s] = self.sygnaly()
        self.assertIn("5 nowych zadań w 90 dni", s.tytul)
        self.assertEqual(s.zrodla[-1], "Brak zgłoszonych osiągnięć w systemie")
        # Zgłoszone osiągnięcie w oknie wygasza sygnał
        self.ocena.dodaj_obserwacje(self.ewa_u, DZIS - timedelta(days=3), "Uporządkowałam rejestr.")
        self.assertEqual(self.sygnaly(), [])

    def test_uzgodnienie_zamyka_sygnal(self):
        for d in (80, 60, 40, 20, 10):
            ZdarzenieZadania.objects.create(pracownik=self.ewa, autor=self.anna_u, data=DZIS - timedelta(days=d),
                                            rodzaj="nowe_zadanie", opis=f"Zadanie {d}")
        [s] = self.sygnaly()
        Uzgodnienie.zapisz(self.anna_u, self.ewa, s.klucz, "rozmowa_wspierajaca", "Rozmowa 1:1 co dwa tygodnie.",
                           DZIS + timedelta(days=14))
        self.assertEqual(self.sygnaly(), [])

