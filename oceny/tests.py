from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from datetime import date, timedelta
from fractions import Fraction

from django.utils import timezone
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import punktacja
from .models import Ocena


class KryteriaDodatkoweTest(TestCase):
    def setUp(self):
        self.oceniany = User.objects.create_user("jan.testowy")
        self.oceniajacy = User.objects.create_user("anna.syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.oceniany, oceniajacy=self.oceniajacy, poczatek_okresu=date(2025, 3, 17))

    def test_maks_trzy(self):
        self.o.ustaw_kryteria(["kreatywnosc", "negocjowanie", "wystapienia_publiczne"])
        with self.assertRaises(ValidationError):
            self.o.ustaw_kryteria(["kreatywnosc", "negocjowanie", "wystapienia_publiczne", "myslenie_analityczne"])

    def test_bez_powtorzen_i_spoza_wykazu(self):
        with self.assertRaises(ValidationError):
            self.o.ustaw_kryteria(["kreatywnosc", "kreatywnosc"])
        with self.assertRaises(ValidationError):
            self.o.ustaw_kryteria(["wymyslone"])
        with self.assertRaises(ValidationError):
            self.o.ustaw_kryteria(["rzetelnosc"])  # obowiązkowe w arkuszu C (§ 4 ust. 3)

    def test_zgodnosc_z_rozporzadzeniem(self):
        from . import rules
        self.assertEqual(len(rules.criteria()), 14)  # Załącznik nr 1
        self.assertEqual(list(rules.mandatory_criteria("C").values()), [
            "Wykorzystywanie wiedzy i doskonalenie zawodowe", "Rzetelność",
            "Organizacja pracy i orientacja na osiąganie celów", "Współpraca", "Komunikacja"])
        self.assertEqual(len(rules.mandatory_criteria("A")), 6)
        self.assertEqual(list(rules.mandatory_criteria("B")), list(rules.mandatory_criteria("A"))[:5])
        self.assertIn("rzetelnosc", rules.extra_criteria("B"))
        self.assertNotIn("zarzadzanie_ludzmi", rules.extra_criteria("B"))
        self.assertEqual(len(rules.extra_criteria("C")), 9)

    def test_blokada_po_potwierdzeniu(self):
        self.o.ustaw_kryteria(["kreatywnosc"])
        self.o.zatwierdz_kryteria(timezone.localdate())
        self.o.potwierdz_kryteria()
        with self.assertRaises(PermissionDenied):
            self.o.ustaw_kryteria(["negocjowanie"])
        self.o.refresh_from_db()
        self.assertEqual(self.o.kryteria_dodatkowe, ["kreatywnosc"])
        kadry = User.objects.create_user("kadry", is_staff=True)
        with self.assertRaises(ValidationError):
            self.o.ustaw_kryteria(["negocjowanie"], korekta_przez=kadry, powod=" ")
        with self.assertRaises(PermissionDenied):
            self.o.ustaw_kryteria(["negocjowanie"], korekta_przez=self.oceniajacy, powod="pomyłka")
        self.o.ustaw_kryteria(["negocjowanie"], korekta_przez=kadry, powod="Pomyłka przy wpisie")
        self.assertEqual(self.o.kryteria_dodatkowe, ["negocjowanie"])
        k = self.o.korekty.get()
        self.assertEqual((k.przed, k.po, k.kto), (["kreatywnosc"], ["negocjowanie"], kadry))


class WidokiKryteriowTest(TestCase):
    def setUp(self):
        self.oceniany = User.objects.create_user("jan.testowy")
        self.oceniajacy = User.objects.create_user("anna.syntetyczna")
        self.obcy = User.objects.create_user("obcy")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.oceniany, oceniajacy=self.oceniajacy, poczatek_okresu=date(2025, 3, 17))
        self.url_ustaw = reverse("oceny:ustaw_kryteria", args=[self.o.pk])
        self.url_potwierdz = reverse("oceny:potwierdz_kryteria", args=[self.o.pk])

    def test_pelny_przebieg(self):
        self.client.force_login(self.oceniajacy)
        r = self.client.post(self.url_ustaw, {"kryteria": ["kreatywnosc", "negocjowanie", ""]})
        self.assertContains(r, "Kreatywność")
        self.client.force_login(self.oceniany)
        self.assertEqual(self.client.post(self.url_potwierdz).status_code, 403)  # najpierw oceniający
        self.client.force_login(self.oceniajacy)
        r = self.client.post(reverse("oceny:zatwierdz_kryteria", args=[self.o.pk]),
                             {"data_rozmowy": timezone.localdate().isoformat(), "miejscowosc": "Bydgoszcz"})
        self.assertContains(r, "Oczekuje na potwierdzenie ocenianego")
        self.client.force_login(self.oceniany)
        r = self.client.post(self.url_potwierdz)
        self.assertContains(r, "Potwierdził oceniany")
        self.client.force_login(self.oceniajacy)
        r = self.client.post(self.url_ustaw, {"kryteria": ["wystapienia_publiczne"]})
        self.assertEqual(r.status_code, 403)
        self.o.refresh_from_db()
        self.assertEqual(self.o.kryteria_dodatkowe, ["kreatywnosc", "negocjowanie"])

    def test_blad_walidacji_wraca_w_formularzu(self):
        self.client.force_login(self.oceniajacy)
        r = self.client.post(self.url_ustaw, {"kryteria": ["kreatywnosc", "negocjowanie", "wystapienia_publiczne", "myslenie_analityczne"]})
        self.assertContains(r, "maksymalnie 3")
        self.o.refresh_from_db()
        self.assertEqual(self.o.kryteria_dodatkowe, [])

    def test_role(self):
        self.o.zatwierdz_kryteria(timezone.localdate())
        self.client.force_login(self.oceniany)
        self.assertEqual(self.client.post(self.url_ustaw, {"kryteria": ["kreatywnosc"]}).status_code, 403)
        self.client.force_login(self.oceniajacy)
        self.assertEqual(self.client.post(self.url_potwierdz).status_code, 403)
        self.assertEqual(self.client.post(self.url_ustaw, {"kryteria": ["kreatywnosc"]}).status_code, 403)  # zatwierdzone
        self.client.force_login(self.obcy)
        self.assertEqual(self.client.get(reverse("oceny:szczegoly", args=[self.o.pk])).status_code, 404)

    def test_wymaga_logowania(self):
        self.assertEqual(self.client.post(self.url_ustaw).status_code, 302)


class PunktacjaTest(SimpleTestCase):
    def test_przyklad_z_koncepcji(self):
        w = punktacja.oblicz([1, 7, 7, 7, 9])
        self.assertEqual(w.srednia, Fraction(31, 5))
        self.assertEqual(w.poziom_kod, "powyzej")
        self.assertFalse(w.pozytywna)  # cząstkowa 1 przesądza (§ 11 ust. 1 pkt 4)

    def test_granice_przedzialow(self):
        # Górna granica należy do niższego poziomu: 4,00 to jeszcze „poniżej oczekiwań”.
        przypadki = {
            (1, 3): ("znacznie_ponizej", False),  # 2
            (3, 5): ("ponizej", False),  # 4
            (5, 7): ("na_poziomie", True),  # 6
            (7, 9): ("powyzej", True),  # 8
            (9, 9): ("znacznie_powyzej", True),
            (3, 3, 7): ("na_poziomie", True),  # 4,33
        }
        for czastkowe, (poziom, pozytywna) in przypadki.items():
            with self.subTest(czastkowe=czastkowe):
                w = punktacja.oblicz(list(czastkowe))
                self.assertEqual((w.poziom_kod, w.pozytywna), (poziom, pozytywna))

    def test_powyzej_progu_bez_bledu_float(self):
        # 6 kryteriów: 5,5,5,5,5,7 → 5,333…; 3,3,5,5,5,3 → 4,0 dokładnie
        self.assertEqual(punktacja.oblicz([3, 3, 5, 5, 5, 3]).poziom_kod, "ponizej")

    def test_niedozwolona_ocena(self):
        with self.assertRaises(ValueError):
            punktacja.oblicz([5, 4])
        with self.assertRaises(ValueError):
            punktacja.oblicz([])


class SporzadzenieTest(TestCase):
    def setUp(self):
        self.oceniany = User.objects.create_user("jan.testowy")
        self.oceniajacy = User.objects.create_user("anna.syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.oceniany, oceniajacy=self.oceniajacy, poczatek_okresu=date(2025, 3, 17))
        self.o.ustaw_kryteria(["kreatywnosc"])
        self.o.zatwierdz_kryteria(timezone.localdate())
        self.o.potwierdz_kryteria()
        self.komplet = {k: 7 for k in self.o.wszystkie_kryteria()}

    def test_wymaga_wszystkich_kryteriow_w_tym_dodatkowego(self):
        self.assertEqual(len(self.komplet), 6)
        niepelne = dict(self.komplet)
        del niepelne["kreatywnosc"]
        bledy = self.o.bledy_formalne(niepelne, date.today(), "", "Szkolenie z negocjacji")
        self.assertIn("kryterium_kreatywnosc", bledy)

    def test_negatywna_wymaga_uzasadnienia(self):
        z_jedynka = self.komplet | {"rzetelnosc": 1}
        with self.assertRaises(ValidationError) as cm:
            self.o.sporzadz(z_jedynka, date.today(), "", "Szkolenie")
        self.assertIn("uzasadnienie", cm.exception.message_dict)

    def test_rozmowa_nie_po_sporzadzeniu_i_wnioski_obowiazkowe(self):
        bledy = self.o.bledy_formalne(self.komplet, date.today() + timedelta(days=1), "", "")
        self.assertEqual(set(bledy), {"data_rozmowy", "wnioski_iprz"})

    def test_sporzadzenie_blokuje(self):
        self.o.sporzadz(self.komplet, date.today(), "", "Mentoring w zespole")
        self.o.refresh_from_db()
        self.assertTrue(self.o.pozytywna)
        self.assertEqual(str(self.o.srednia), "7.00")
        self.assertEqual(self.o.poziom, "powyżej oczekiwań")
        with self.assertRaises(PermissionDenied):
            self.o.sporzadz(self.komplet, date.today(), "", "x")
        with self.assertRaises(PermissionDenied):
            self.o.ustaw_kryteria([], korekta_przez=User.objects.create_user("k", is_staff=True), powod="x")

    def test_bez_potwierdzenia_kryteriow(self):
        inna = Ocena.objects.create(arkusz="C", oceniany=self.oceniany, oceniajacy=self.oceniajacy, poczatek_okresu=date(2025, 3, 17))
        komplet = {k: 5 for k in inna.wszystkie_kryteria()}
        self.assertIn("kryteria", inna.bledy_formalne(komplet, date.today(), "", "x"))


class WidokSporzadzeniaTest(TestCase):
    def setUp(self):
        self.oceniany = User.objects.create_user("jan.testowy")
        self.oceniajacy = User.objects.create_user("anna.syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.oceniany, oceniajacy=self.oceniajacy, poczatek_okresu=date(2025, 3, 17))
        self.o.zatwierdz_kryteria(timezone.localdate())
        self.o.potwierdz_kryteria()
        self.dane = {f"kryterium_{k}": "5" for k in self.o.wszystkie_kryteria()} | {
            "data_rozmowy": date.today().isoformat(), "uzasadnienie": "", "wnioski_iprz": "Kurs z analizy danych"}

    def test_podglad_i_sporzadzenie(self):
        self.client.force_login(self.oceniajacy)
        r = self.client.post(reverse("oceny:podglad_wyniku", args=[self.o.pk]), self.dane | {"kryterium_rzetelnosc": "1"})
        self.assertContains(r, "ocena negatywna")
        r = self.client.post(reverse("oceny:sporzadz", args=[self.o.pk]), self.dane | {"kryterium_rzetelnosc": "1"})
        self.assertContains(r, "§ 11 ust. 3")
        self.assertContains(r, "Kurs z analizy danych")  # wpisane dane nie giną po błędzie
        r = self.client.post(reverse("oceny:sporzadz", args=[self.o.pk]), self.dane)
        self.assertContains(r, "ocena pozytywna")
        self.o.refresh_from_db()
        self.assertTrue(self.o.sporzadzona)

    def test_oceniany_nie_sporzadza(self):
        self.client.force_login(self.oceniany)
        self.assertEqual(self.client.post(reverse("oceny:sporzadz", args=[self.o.pk]), self.dane).status_code, 403)
        self.assertEqual(self.client.post(reverse("oceny:podglad_wyniku", args=[self.o.pk]), self.dane).status_code, 403)
