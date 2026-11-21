import json
from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from . import asystent
from .models import Ocena, ZegarDemo


@override_settings(OKRES_DEMO=True)
class AsystentTest(TestCase):
    def setUp(self):
        ZegarDemo(data=date(2026, 11, 21)).save()
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))
        self.n1 = self.o.dodaj_obserwacje(self.anna, date(2026, 5, 4), "Jan Testowy złożył raport 5 dni po terminie", "rzetelnosc")
        self.n2 = self.o.dodaj_obserwacje(self.anna, date(2026, 6, 4), "Usprawnił obieg pism", "organizacja_pracy", "Krótsza kolejka")

    def test_bez_ai_deterministycznie_ze_zrodlami(self):
        z = asystent.zestaw(self.o, self.anna)
        self.assertEqual(z.tryb, "bez_ai")
        punkty = {g["kod"]: g["punkty"] for g in z.kryteria}
        self.assertEqual(punkty["rzetelnosc"][0].zrodla, [self.n1.pk])

    @override_settings(OKRES_AI="ollama")
    def test_ollama_odrzuca_zdania_bez_zrodla_i_pseudonimizuje(self):
        wyslane = {}

        def falszywy_model(prompt):
            wyslane["prompt"] = prompt
            return json.dumps({"kryteria": {
                "rzetelnosc": [{"zdanie": "[OCENIANY] złożył raport po terminie.", "zrodla": [self.n1.pk]},
                               {"zdanie": "Zawsze jest niesolidny.", "zrodla": []},
                               {"zdanie": "Wymyślone źródło.", "zrodla": [99999]}]}})

        with mock.patch.object(asystent, "_zapytaj_ollama", falszywy_model):
            z = asystent.zestaw(self.o, self.anna)
        self.assertNotIn("Testowy", wyslane["prompt"])
        self.assertIn("[OCENIANY]", wyslane["prompt"])
        punkty = {g["kod"]: g["punkty"] for g in z.kryteria}
        self.assertEqual(len(punkty["rzetelnosc"]), 1)
        self.assertIn("Jan Testowy", punkty["rzetelnosc"][0].tekst)  # przywrócone lokalnie
        self.assertIn("Odrzucono zdania bez źródła: 2", z.komunikat)

    @override_settings(OKRES_AI="ollama")
    def test_awaria_modelu_jawnie_oznaczona(self):
        with mock.patch.object(asystent, "_zapytaj_ollama", side_effect=OSError("brak połączenia")):
            z = asystent.zestaw(self.o, self.anna)
        self.assertEqual(z.tryb, "bez_ai")
        self.assertIn("niedostępny", z.komunikat)

    def test_widok_tylko_oceniajacy_i_elementy(self):
        self.o.zatwierdz_kryteria(date(2025, 4, 1))
        self.o.potwierdz_kryteria()
        dane = {f"kryterium_{k}": "5" for k in self.o.wszystkie_kryteria()} | {"kryterium_rzetelnosc": "1"}
        self.client.force_login(self.anna)
        r = self.client.post(reverse("oceny:asystent", args=[self.o.pk]), dane)
        self.assertContains(r, "Uzasadnienie jest obowiązkowe przy ocenie negatywnej")
        self.assertContains(r, f"[notatka {self.n1.pk}]")
        self.assertContains(r, "Zestawienie bez AI")
        self.client.force_login(self.jan)
        self.assertEqual(self.client.post(reverse("oceny:asystent", args=[self.o.pk]), dane).status_code, 403)
