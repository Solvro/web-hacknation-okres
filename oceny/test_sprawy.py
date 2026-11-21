from io import StringIO
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .management.commands import seed_demo
from .models import Nieobecnosc, Ocena, Pracownik, Urzad, ZegarDemo
from .pomoc_testow import sprawa_od_kryteriow


@override_settings(OKRES_DEMO=True)
class SprawyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        sprawa_od_kryteriow(User.objects.get(username="oceniany"))  # seed ma sprawy w toku
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
        self.assertContains(r, "Jan Borkowski")
        self.assertNotContains(r, "Piotr Wysocki</a>")
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:moje_sprawy") + "?filtr=moje")
        self.assertContains(r, "Piotr Wysocki")
        self.assertNotContains(r, "Anna Leszczyńska</a>")  # jej własna sprawa nie wymaga jej działania
        self.client.force_login(User.objects.get(username="kadry"))
        self.assertContains(self.client.get(reverse("oceny:moje_sprawy")), "Anna Leszczyńska")

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

    def test_zmiana_roli_z_naglowka_tylko_w_demo(self):
        self.client.force_login(self.anna)
        start = reverse("oceny:moje_sprawy")
        self.assertContains(self.client.get(start), "Zmień rolę demo")
        self.assertRedirects(self.client.post(reverse("demo_zaloguj"), {"login": "oceniany"}), start)
        self.assertEqual(self.client.get(start).wsgi_request.user, self.jan)
        with self.settings(OKRES_DEMO=False):
            self.assertNotContains(self.client.get(start), "Zmień rolę demo")

    def test_strona_sprawy_i_logowania(self):
        self.assertContains(self.client.get(reverse("login")), "Wybierz konto demonstracyjne")
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:szczegoly", args=[self.o.pk]))
        self.assertNotContains(r, "DANE FIKCYJNE")
        self.assertContains(r, "Data systemowa ustawiona na 23.11.2026")
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


@override_settings(OKRES_DEMO=True)
class AktualizacjaDemoTest(TestCase):
    def test_start_uzupelnia_starszy_zestaw_bez_nadpisywania_danych(self):
        with (
            patch.object(seed_demo, "OSOBY", seed_demo.OSOBY[:5]),
            patch.object(seed_demo.Command, "_przygotowane_sprawy"),
            patch.object(seed_demo.Command, "_hr_partner"),
        ):
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Ocena.objects.count(), 3)

        Urzad.objects.update(nazwa="Urząd Testowy w Bydgoszczy (DEMO)")
        jan = User.objects.get(username="oceniany")
        jan.last_name = "Testowy"
        jan.set_password("zmienione-haslo-testowe")
        jan.save()
        Pracownik.objects.filter(user=jan).update(stanowisko="Zmodyfikowane stanowisko")
        ZegarDemo(data=date(2026, 11, 19)).save()
        sprawa = Ocena.objects.get(oceniany=jan)
        sprawa.zatwierdz_kryteria(date(2026, 11, 18), "Bydgoszcz", "Zapisane ustalenia")
        for _ in range(2):
            call_command("seed_demo", na_starcie=True, stdout=StringIO())

        self.assertEqual(Pracownik.objects.count(), 14)  # z oceniającą kierownika urzędu spoza urzędu
        # 3 sprawy starszego zestawu (bez przebiegu, więc bez kolejnej sprawy Piotra) + 9 przygotowanych + kolejna Rafała
        self.assertEqual(Ocena.objects.count(), 13)
        self.assertEqual(ZegarDemo.objects.get().data, date(2026, 11, 19))
        self.assertIn("A", Ocena.objects.values_list("arkusz", flat=True))
        self.assertIn("zapoznanie", {o.etap for o in Ocena.objects.filter(oceniany__username="natalia")})
        self.assertIn("sprzeciw", {o.etap for o in Ocena.objects.filter(oceniany__username="joanna")})
        self.assertIn("zakonczona", {o.etap for o in Ocena.objects.filter(oceniany__username="rafal")})
        sprawa.refresh_from_db()
        self.assertEqual(sprawa.cele_i_oczekiwania, "Zapisane ustalenia")
        jan.refresh_from_db()
        self.assertTrue(jan.check_password("zmienione-haslo-testowe"))
        self.assertEqual(jan.last_name, "Testowy")
        self.assertEqual(jan.pracownik.stanowisko, "Zmodyfikowane stanowisko")

    def test_start_pomija_nierozpoznana_baze(self):
        User.objects.create_user("koordynator")
        call_command("seed_demo", na_starcie=True, stdout=StringIO())
        self.assertEqual(list(User.objects.values_list("username", flat=True)), ["koordynator"])
        self.assertFalse(Ocena.objects.exists())


@override_settings(OKRES_DEMO=True)
class NieznaneAdresyTest(TestCase):
    """QA M8: nieznany rodzaj w adresie to 404 (nie wyjaśnienie zastępcze ani 403)."""

    def setUp(self):
        self.jan = User.objects.create_user("jan")
        self.anna = User.objects.create_user("anna")
        self.obcy = User.objects.create_user("obcy")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))

    def test_nieznany_rodzaj_terminu_i_przygotowania(self):
        self.client.force_login(self.anna)
        self.assertEqual(self.client.get(reverse("oceny:jak_obliczono", args=[self.o.pk, "xyz"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("oceny:przygotowanie", args=[self.o.pk, "xyz"])).status_code, 404)
        for rodzaj in ("kryteria", "ocena"):
            self.assertEqual(self.client.get(reverse("oceny:jak_obliczono", args=[self.o.pk, rodzaj])).status_code, 200)
        self.assertEqual(self.client.get(reverse("oceny:przygotowanie", args=[self.o.pk, "rozpoczynajaca"])).status_code, 200)

    def test_nieznane_zdarzenie_kadrowe(self):
        self.client.force_login(User.objects.create_user("kadry", is_staff=True))
        self.assertEqual(self.client.post(reverse("oceny:zdarzenie_kadrowe", args=[self.o.pk, "xyz"])).status_code, 404)


@override_settings(OKRES_DEMO=True)
class BrakUprawnienTest(TestCase):
    """QA L7: 403 z komunikatem z PermissionDenied, w HTMX jako tekst do komunikatu na stronie."""

    def setUp(self):
        self.jan = User.objects.create_user("jan")
        self.anna = User.objects.create_user("anna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))
        self.client.force_login(self.jan)

    def test_strona_403_z_komunikatem(self):
        r = self.client.get(reverse("oceny:statystyki"))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "<!doctype html>", status_code=403)
        self.assertContains(r, "Statystyki są dostępne dla kierownictwa i kadr.", status_code=403)
        self.assertContains(r, reverse("oceny:moje_sprawy"), status_code=403)

    def test_htmx_403_jako_tekst(self):
        r = self.client.post(reverse("oceny:zatwierdz_kryteria", args=[self.o.pk]), {"data_rozmowy": "2025-04-01"},
                             headers={"HX-Request": "true"})
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r["Content-Type"].startswith("text/plain"))
        self.assertEqual(r.content.decode(), "Rozmowę i kryteria zatwierdza oceniający.")

    def test_skrypt_pokazuje_bledy_htmx(self):
        from django.contrib.staticfiles import finders

        with open(finders.find("oceny/okres.js"), encoding="utf-8") as f:
            self.assertIn("htmx:responseError", f.read())


@override_settings(OKRES_DEMO=True)
class PanelKadrDatyTest(TestCase):
    """QA M5: panel kadr pokazuje daty z arkusza, a nie moment zapisu danych demo."""

    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=date(2026, 11, 21)).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())

    def test_lista_i_formularz_bez_technicznych_znacznikow(self):
        from django.utils.formats import date_format

        self.client.force_login(User.objects.get(username="kadry"))
        o = Ocena.objects.filter(data_sporzadzenia__isnull=False).exclude(data_sporzadzenia=date(2026, 11, 21)).first()
        r = self.client.get(reverse("admin:oceny_ocena_changelist"))
        self.assertNotContains(r, "Sporzadzona at")
        self.assertNotContains(r, "potwierdzone at")
        self.assertContains(r, date_format(o.data_sporzadzenia, "j E Y"))
        r = self.client.get(reverse("admin:oceny_ocena_change", args=[o.pk]))
        self.assertNotContains(r, " at:")  # techniczne znaczniki zapisu (moment seedowania) ukryte


@override_settings(OKRES_DEMO=True)
class ZaproszenieKalendarzTest(TestCase):
    """QA L6: po odbytej rozmowie nie proponujemy zaproszenia do kalendarza."""

    def setUp(self):
        ZegarDemo(data=date(2026, 11, 21)).save()
        self.jan = User.objects.create_user("jan", email="jan@example.invalid")
        self.anna = User.objects.create_user("anna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2026, 11, 2))
        self.client.force_login(self.anna)
        self.url = reverse("oceny:szczegoly", args=[self.o.pk])
        self.ics = reverse("oceny:zaproszenie_ics", args=[self.o.pk])

    def test_zaproszenie_tylko_przed_rozmowa(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Zaproszenie do kalendarza")
        self.assertContains(r, 'min="2026-11-21"')
        self.assertEqual(self.client.get(self.ics, {"data": "2026-11-25", "rodzaj": "kryteria"}).status_code, 200)
        self.o.zatwierdz_kryteria(date(2026, 11, 17), "Bydgoszcz")
        self.assertNotContains(self.client.get(self.url), "Zaproszenie do kalendarza")
        r = self.client.get(self.ics, {"data": "2026-11-25", "rodzaj": "kryteria"})
        self.assertContains(r, "już się odbyła", status_code=400)

    def test_zaproszenie_na_date_z_przeszlosci(self):
        r = self.client.get(self.ics, {"data": "2026-11-20", "rodzaj": "kryteria"})
        self.assertContains(r, "w przeszłości", status_code=400)


@override_settings(OKRES_DEMO=True)
class SpojnoscDanychDemoTest(TestCase):
    """QA H1, H2, H4, H5, M4: dane demo są spójne w dniu pokazu (21.11.2026)."""

    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=seed_demo.DZIEN_DEMO).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())

    def test_zadna_sprawa_nie_stoi_po_terminie(self):
        self.assertEqual([o.pk for o in Ocena.objects.all() if o.po_terminie], [])
        self.assertEqual(Ocena.objects.get(oceniany__username="oceniany").etap, "ocena")
        biezaca = Ocena.objects.get(oceniany__username="piotr", poprzednia__isnull=False)
        self.assertEqual((biezaca.etap, biezaca.rachunek_kryteriow().termin), ("kryteria", date(2026, 12, 4)))

    def test_kolejna_sprawa_tylko_po_ocenie_ostatecznej(self):
        for o in Ocena.objects.filter(nastepna__isnull=False):
            self.assertEqual(o.etap, "zakonczona", o)
        for login in ("natalia", "joanna"):
            self.assertEqual(Ocena.objects.filter(oceniany__username=login).count(), 1)

    def test_aktywnosc_jana_poza_nieobecnoscia(self):
        from partner.models import ZdarzenieZadania
        jan = Pracownik.objects.get(user__username="oceniany")
        daty = list(ZdarzenieZadania.objects.filter(pracownik=jan).values_list("data", flat=True))
        daty += list(Ocena.objects.get(oceniany=jan.user).obserwacje.values_list("data", flat=True))
        for d in daty:
            self.assertFalse(jan.nieobecnosci.filter(od__lte=d, do__gte=d).exists(), d)

    def test_kierownika_urzedu_nie_ocenia_dyrektor_generalny(self):
        o = Ocena.objects.get(arkusz="A")
        self.assertFalse(o.oceniajacy.pracownik.dyrektor_generalny)
        self.assertFalse(o.oceniajacy.has_usable_password())  # osoba spoza urzędu, bez konta w pokazie

    def test_kazdy_poza_dg_i_osoba_spoza_urzedu_ma_sprawe(self):
        bez_sprawy = Pracownik.objects.filter(dyrektor_generalny=False, user__oceny_wlasne__isnull=True)
        self.assertEqual(list(bez_sprawy.values_list("user__username", flat=True)), ["nadrzedny"])

    def test_wnioski_nie_kopiuja_celow(self):
        for o in Ocena.objects.filter(data_sporzadzenia__isnull=False):
            self.assertNotEqual(o.wnioski_iprz, o.cele_i_oczekiwania)
            self.assertTrue(o.obserwacje.exists())
