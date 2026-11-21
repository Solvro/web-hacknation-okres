from datetime import date

from django.test import SimpleTestCase

from . import terminy
from .terminy import Okres, dluzsza_niz, dodaj_miesiace, scal_nieobecnosci, termin_dniowy, termin_miesieczny, termin_oceny


class PrzykladyKPRMTest(SimpleTestCase):
    """Przykłady z dokumentu KPRM „liczenie terminów”."""

    def test_24_miesiace(self):
        self.assertEqual(termin_miesieczny(date(2024, 3, 16), 24), date(2026, 3, 16))

    def test_brak_dnia_w_miesiacu(self):
        self.assertEqual(dodaj_miesiace(date(2024, 1, 31), 13), date(2025, 2, 28))
        self.assertEqual(dodaj_miesiace(date(2024, 1, 31), 1), date(2024, 2, 29))

    def test_ciaglosc_nieobecnosci(self):
        l4, urlop = Okres(date(2026, 10, 5), date(2026, 10, 16)), Okres(date(2026, 10, 19), date(2026, 11, 6))
        [scalona] = scal_nieobecnosci([urlop, l4])
        self.assertEqual(scalona, Okres(date(2026, 10, 5), date(2026, 11, 6)))
        self.assertTrue(dluzsza_niz(scalona, 1))
        self.assertFalse(dluzsza_niz(l4, 1))


class TerminyTest(SimpleTestCase):
    def test_przesuniecie_z_soboty_i_swieta(self):
        self.assertEqual(termin_miesieczny(date(2024, 3, 14), 24), date(2026, 3, 16))  # sobota 14.03 → pon.
        self.assertEqual(termin_dniowy(date(2026, 10, 4), 7), date(2026, 10, 12))  # niedziela → pon.
        self.assertEqual(termin_dniowy(date(2026, 10, 25), 7), date(2026, 11, 2))  # 1.11 niedziela → pon. 2.11
        self.assertEqual(termin_dniowy(date(2026, 11, 4), 7), date(2026, 11, 12))  # 11.11 święto

    def test_dzien_zdarzenia_nie_liczy_sie(self):
        self.assertEqual(termin_dniowy(date(2026, 11, 16), 7), date(2026, 11, 23))

    def test_przerwa_w_dzien_roboczy_przerywa_ciaglosc(self):
        a, b = Okres(date(2026, 10, 5), date(2026, 10, 15)), Okres(date(2026, 10, 19), date(2026, 11, 6))
        self.assertEqual(len(scal_nieobecnosci([a, b])), 2)  # piątek 16.10 był dniem pracy

    def test_dokladnie_miesiac_nie_przedluza(self):
        self.assertFalse(dluzsza_niz(Okres(date(2026, 10, 5), date(2026, 11, 4)), 1))
        self.assertTrue(dluzsza_niz(Okres(date(2026, 10, 5), date(2026, 11, 5)), 1))

    def test_termin_oceny_przedluzony(self):
        start = date(2025, 3, 16)
        self.assertEqual(termin_oceny(start), date(2027, 3, 16))
        krotka = [Okres(date(2026, 1, 5), date(2026, 1, 20))]
        self.assertEqual(termin_oceny(start, krotka), date(2027, 3, 16))
        dluga = [Okres(date(2026, 10, 5), date(2026, 10, 16)), Okres(date(2026, 10, 19), date(2026, 11, 6))]
        # 33 dni nieobecności: 16.03.2027 + 33 dni = 18.04.2027 (niedziela) → 19.04.2027
        self.assertEqual(termin_oceny(start, dluga), date(2027, 4, 19))

    def test_nieobecnosc_sprzed_okresu_liczona_od_poczatku(self):
        # 01.12.2023–31.03.2024 przy początku okresu 01.02.2024: liczy się 60 dni (01.02–31.03), nie 122
        start = date(2024, 2, 1)
        r = termin_oceny(start, [Okres(date(2023, 12, 1), date(2024, 3, 31))])
        self.assertEqual(r, date(2026, 4, 2))  # 01.02.2026 + 60 dni = 02.04.2026 (czwartek)


class PodstawyPrawneTest(SimpleTestCase):
    def test_rachunek_cytuje_wlasciwe_przepisy(self):
        r = terminy.rachunek_terminu_oceny(date(2025, 3, 16), [terminy.Okres(date(2026, 10, 5), date(2026, 10, 16)),
                                                                terminy.Okres(date(2026, 10, 19), date(2026, 11, 6))])
        podstawy = [k.podstawa for k in r.kroki]
        self.assertIn("art. 81 ust. 4 ustawy", podstawy)  # ocena co 24 miesiące
        self.assertIn("art. 81 ust. 7 ustawy", podstawy)  # przedłużenie o nieobecność
        self.assertNotIn("art. 81 ust. 1 ustawy", podstawy)
