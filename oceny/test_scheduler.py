from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from . import scheduler
from .models import Ocena, Przypomnienie, ZegarDemo


def zegar(d):
    ZegarDemo(data=d).save()


@override_settings(OKRES_DEMO=True)
class SchedulerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(OKRES_DEMO=True):
            call_command("seed_demo", stdout=StringIO())
        cls.jan = User.objects.get(username="oceniany")
        cls.anna = User.objects.get(username="oceniajaca")
        cls.piotr = User.objects.get(username="piotr")

    def test_przypomnienia_o_kryteriach_i_idempotencja(self):
        o = Ocena.objects.get(oceniany=self.jan)  # termin kryteriów 15.04.2025
        zegar(date(2025, 4, 7))
        self.assertEqual(scheduler.przypomnienia_dla(o), 0)
        zegar(date(2025, 4, 8))  # T-7
        self.assertEqual(scheduler.przypomnienia_dla(o), 1)
        self.assertEqual(scheduler.przypomnienia_dla(o), 0)  # ponowne uruchomienie
        zegar(date(2025, 4, 15))  # T-2 i T-0
        self.assertEqual(scheduler.przypomnienia_dla(o), 2)
        p = Przypomnienie.objects.filter(ocena=o).last()
        self.assertEqual(p.odbiorca, self.anna)
        self.assertIn("15.04.2025", p.tresc)

    def test_przypomnienie_trafia_do_ocenianego_po_zatwierdzeniu(self):
        o = Ocena.objects.get(oceniany=self.jan)
        zegar(date(2025, 4, 14))
        o.zatwierdz_kryteria(date(2025, 4, 1))
        scheduler.przypomnienia_dla(o)
        self.assertTrue(Przypomnienie.objects.filter(ocena=o, odbiorca=self.jan).exists())

    def test_kolejna_sprawa_po_negatywnej(self):
        zegar(date(2026, 11, 23))
        o = Ocena.objects.get(oceniany=self.piotr)
        o.zatwierdz_kryteria(date(2024, 12, 10))
        o.potwierdz_kryteria()
        komplet = {k: 5 for k in o.wszystkie_kryteria()} | {"rzetelnosc": 1}
        o.sporzadz(komplet, date(2026, 11, 23), "Uzasadnienie", "Szkolenie")
        self.assertEqual(scheduler.uruchom()["nowe_sprawy"], 1)
        self.assertEqual(scheduler.uruchom()["nowe_sprawy"], 0)
        nowa = Ocena.objects.get(poprzednia=o)
        self.assertTrue(nowa.po_negatywnej)
        self.assertEqual(nowa.rachunek_kryteriow().termin, date(2026, 11, 30))  # 7 dni od sporządzenia
        self.assertIsNone(nowa.termin_oceny)  # do zapoznania brak daty początku sześciu miesięcy
        o.potwierdz_zapoznanie()
        nowa.refresh_from_db()
        nowa.poprzednia.refresh_from_db()
        self.assertEqual(nowa.termin_oceny, date(2027, 5, 24))  # 23.05.2027 to niedziela

    def test_komenda_i_widok_demo(self):
        zegar(date(2025, 4, 15))
        out = StringIO()
        call_command("scheduler", stdout=out)
        self.assertIn("Przypomnienia:", out.getvalue())
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:moje_sprawy"))
        self.assertContains(r, "Przypomnienia")
        p = self.anna.przypomnienia.first()
        self.client.post(reverse("oceny:przeczytane", args=[p.pk]))
        p.refresh_from_db()
        self.assertTrue(p.przeczytane)
        self.assertEqual(self.client.post(reverse("oceny:uruchom_scheduler")).status_code, 403)
        self.client.force_login(User.objects.get(username="kadry"))
        self.assertRedirects(self.client.post(reverse("oceny:uruchom_scheduler")), reverse("oceny:moje_sprawy"))

    def test_zaproszenie_ics(self):
        o = Ocena.objects.get(oceniany=self.jan)
        self.client.force_login(self.anna)
        r = self.client.get(reverse("oceny:zaproszenie_ics", args=[o.pk]), {"data": "2026-12-01", "godzina": "09:30"})
        tresc = r.content.decode()
        self.assertEqual(r["Content-Type"], "text/calendar; charset=utf-8")
        self.assertIn("DTSTART;TZID=Europe/Warsaw:20261201T093000", tresc)
        self.assertIn("SUMMARY:Spotkanie z przełożonym", tresc)
        self.assertNotIn("ocen", tresc.split("SUMMARY:")[1].split("\r\n")[0].lower())
        self.client.force_login(self.jan)
        self.assertEqual(self.client.get(reverse("oceny:zaproszenie_ics", args=[o.pk]), {"data": "2026-12-01"}).status_code, 403)
