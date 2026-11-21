from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from . import scheduler
from .models import Ocena, ZegarDemo


def zegar(d):
    ZegarDemo(data=d).save()


@override_settings(OKRES_DEMO=True)
class RozpatrzenieSprzeciwuTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        cls.piotr = User.objects.get(username="piotr")
        cls.anna = User.objects.get(username="oceniajaca")
        cls.dg = User.objects.get(username="dyrektor")

    def setUp(self):
        zegar(date(2026, 11, 2))
        self.o = Ocena.objects.get(oceniany=self.piotr)
        self.o.zatwierdz_kryteria(date(2024, 12, 10))
        self.o.potwierdz_kryteria()
        self.komplet = {k: 5 for k in self.o.wszystkie_kryteria()}
        self.o.sporzadz(self.komplet | {"rzetelnosc": 1}, date(2026, 11, 2), "Opóźnienia w raportach", "Szkolenie")
        self.o.potwierdz_zapoznanie()
        zegar(date(2026, 11, 5))
        self.sprzeciw = self.o.zloz_sprzeciw("Opóźnienia wynikały z braków kadrowych.")

    def test_terminy_rozpatrzenia_i_sadu(self):
        self.assertEqual(self.sprzeciw.termin_rozpatrzenia, date(2026, 11, 19))
        self.assertIsNone(self.sprzeciw.termin_odwolania)
        zegar(date(2026, 11, 20))  # bezczynność DG
        self.assertEqual(self.sprzeciw.termin_odwolania, date(2026, 12, 3))
        self.assertEqual(self.o.nastepny_krok(self.dg)["termin"], date(2026, 11, 19))
        self.assertTrue(self.o.nastepny_krok(self.dg)["moj"])

    def test_tylko_dg(self):
        with self.assertRaises(PermissionDenied):
            self.o.rozpatrz_sprzeciw(self.anna, "nieuwzgledniony", "x")
        with self.assertRaises(ValidationError):
            self.o.rozpatrz_sprzeciw(self.dg, "nieuwzgledniony", " ")

    def test_nieuwzglednienie(self):
        zegar(date(2026, 11, 10))
        s = self.o.rozpatrz_sprzeciw(self.dg, "nieuwzgledniony", "Opóźnienia udokumentowane.")
        self.assertEqual(s.termin_odwolania, date(2026, 11, 24))
        self.assertEqual(self.o.etap, "zakonczona")

    def test_zmiana_oceny_z_historia(self):
        with self.assertRaises(ValidationError):
            self.o.rozpatrz_sprzeciw(self.dg, "zmiana", "Uzasadnienie", {"rzetelnosc": 3})
        self.o.rozpatrz_sprzeciw(self.dg, "zmiana", "Braki kadrowe nie zależały od ocenianego.", self.komplet | {"rzetelnosc": 3})
        self.o.refresh_from_db()
        self.assertTrue(self.o.pozytywna)
        self.assertEqual(self.o.poziom, "na poziomie oczekiwań")
        w = self.o.wersje.get()
        self.assertEqual((w.wersja, w.dane["pozytywna"], w.dane["srednia"]), (1, False, "4.20"))

    def test_ponowne_sporzadzenie_i_drugi_sprzeciw(self):
        scheduler.uruchom()  # założona kolejna sprawa od oceny negatywnej
        self.assertTrue(Ocena.objects.filter(poprzednia=self.o).exists())
        self.o.rozpatrz_sprzeciw(self.dg, "ponowne", "Ocena nie uwzględniła zmiany zadań.")
        self.o.refresh_from_db()
        self.assertEqual((self.o.wersja, self.o.etap, self.o.oceny_czastkowe), (2, "ocena", {}))
        self.assertTrue(self.o.kryteria_zablokowane)  # kryteria z części I bez zmian
        self.assertFalse(Ocena.objects.filter(poprzednia=self.o).exists())  # nietknięta kolejna sprawa usunięta
        self.o.sporzadz(self.komplet, date(2026, 11, 5), "", "Szkolenie")
        self.o.potwierdz_zapoznanie()
        drugi = self.o.zloz_sprzeciw("Nadal się nie zgadzam.")  # art. 83 ust. 4 zd. 2
        self.assertEqual(drugi.wersja, 2)
        with self.assertRaises(ValidationError):
            self.o.rozpatrz_sprzeciw(self.dg, "ponowne", "Trzeci raz")

    def test_widok_dg(self):
        self.client.force_login(self.dg)
        r = self.client.get(reverse("oceny:moje_sprawy") + "?filtr=moje")
        self.assertContains(r, "Rozpatrz sprzeciw")
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertContains(r, "Rozstrzygnięcie sprzeciwu")
        self.assertNotContains(r, "Obserwacje z okresu oceny")  # DG nie widzi notatek
        dane = {f"kryterium_{k}": "5" for k in self.komplet} | {"decyzja": "zmiana", "uzasadnienie_decyzji": "Zasadny"}
        r = self.client.post(reverse("oceny:rozpatrz_sprzeciw", args=[self.o.pk]), dane)
        self.assertContains(r, "uwzględniony: zmiana oceny")
        self.assertContains(r, "Historia wersji oceny")
        self.client.force_login(self.anna)
        self.assertEqual(self.client.post(reverse("oceny:rozpatrz_sprzeciw", args=[self.o.pk]), dane).status_code, 403)


@override_settings(OKRES_DEMO=True)
class PoprawkiZPrzegladuTest(RozpatrzenieSprzeciwuTest):
    def test_dg_strona_oceny_nie_rozpatruje(self):
        anna_ocena = Ocena.objects.get(oceniany=self.anna)  # oceniająca: dyrektor
        with self.assertRaises(PermissionDenied):
            anna_ocena.rozpatrz_sprzeciw(self.dg, "nieuwzgledniony", "x")

    def test_zmiana_wymaga_ponownego_zapoznania(self):
        self.o.rozpatrz_sprzeciw(self.dg, "zmiana", "Zasadny", self.komplet)
        self.assertEqual(self.o.etap, "zapoznanie")
        self.o.potwierdz_zapoznanie()
        self.assertEqual(self.o.etap, "zakonczona")  # bez drugiego sprzeciwu od zmienionej oceny

    def test_ponowne_anuluje_zaawansowana_kolejna_sprawe(self):
        scheduler.uruchom()
        nastepna = Ocena.objects.get(poprzednia=self.o)
        nastepna.zatwierdz_kryteria(date(2026, 11, 5))
        nastepna.dodaj_obserwacje(self.anna, date(2026, 11, 5), "Notatka w nowym okresie")
        self.o.rozpatrz_sprzeciw(self.dg, "ponowne", "Ponownie")
        nastepna.refresh_from_db()
        self.assertEqual(nastepna.etap, "anulowana")
        self.assertEqual(nastepna.obserwacje.count(), 1)  # nic nie znika po cichu
        self.o.sporzadz(self.komplet, date(2026, 11, 5), "", "Szkolenie")
        self.assertEqual(scheduler.uruchom()["nowe_sprawy"], 1)

    def test_ponowna_po_negatywnej_nie_przed_szescioma_miesiacami(self):
        scheduler.uruchom()
        nastepna = Ocena.objects.get(poprzednia=self.o)
        nastepna.zatwierdz_kryteria(date(2026, 11, 5))
        nastepna.potwierdz_kryteria()
        komplet = {k: 5 for k in nastepna.wszystkie_kryteria()}
        self.assertIn("termin", nastepna.bledy_formalne(komplet, date(2026, 11, 5), "", "Szkolenie"))
