import io
import json
import tempfile
import zipfile
from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ocena, Pracownik, ZegarDemo


@override_settings(OKRES_DEMO=True)
class StatystykiEksportImportTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        ZegarDemo(data=date(2026, 11, 21)).save()
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        cls.jan = User.objects.get(username="oceniany")
        cls.dg = User.objects.get(username="dyrektor")
        cls.kadry = User.objects.get(username="kadry")

    def test_statystyki_dostep_i_brak_notatek(self):
        self.client.force_login(self.jan)
        self.assertEqual(self.client.get(reverse("oceny:statystyki")).status_code, 403)
        self.client.force_login(self.dg)
        r = self.client.get(reverse("oceny:statystyki"))
        self.assertContains(r, "Sprawy w systemie")
        self.assertNotContains(r, "Raport kwartalny")
        csv = self.client.get(reverse("oceny:statystyki") + "?format=csv").content.decode()
        self.assertIn("liczba_spraw;14", csv)

    def test_eksport_zip(self):
        o = Ocena.objects.get(oceniany=self.jan)
        self.client.force_login(self.kadry)
        r = self.client.get(reverse("oceny:eksport_sprawy", args=[o.pk]))
        z = zipfile.ZipFile(io.BytesIO(r.content))
        self.assertEqual(set(z.namelist()), {"arkusz.html", "dane.json", "CZYTAJ.txt"})
        dane = json.loads(z.read("dane.json"))
        self.assertEqual(dane["terminy"]["ocena"], "2027-04-19")
        self.assertNotIn("Raport kwartalny", z.read("dane.json").decode())  # notatki nie trafiają do akt
        self.assertIn("<style>", z.read("arkusz.html").decode())
        self.client.force_login(User.objects.get(username="oceniajaca"))
        self.assertEqual(self.client.get(reverse("oceny:eksport_sprawy", args=[o.pk])).status_code, 403)

    def test_import_csv(self):
        tresc = ("login;imie;nazwisko;email;komorka;stanowisko;rodzaj_stanowiska;przelozony;urzednik;rok_mianowania;stopien;data_stopnia\n"
                 "ewa;Ewa;Nowa;;Wydział Finansów;Naczelniczka;kierujacy;dyrektor;tak;2018;3;2021-02-01\n"
                 "olek;Aleksander;Próbny;;Wydział Finansów;Referent;pozostale;ewa;nie;;;\n")
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(tresc)
        call_command("import_pracownikow", f.name, stdout=StringIO())
        call_command("import_pracownikow", f.name, stdout=StringIO())  # idempotentnie
        olek = Pracownik.objects.get(user__username="olek")
        self.assertEqual((olek.arkusz, olek.przelozony.user.username), ("C", "ewa"))
        self.assertEqual(Pracownik.objects.get(user__username="ewa").stopien_sluzbowy, 3)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("login;imie;nazwisko;stanowisko;rodzaj_stanowiska\nx;X;Y;Z;nieznany\n")
        with self.assertRaises(CommandError):
            call_command("import_pracownikow", f.name, stdout=StringIO())
