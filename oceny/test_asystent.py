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


class OllamaPayloadTest(TestCase):
    def _wyslij(self):
        wyslane = {}

        class Odp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"message": {"content": "{}"}}).encode()

        def urlopen(req, timeout):
            wyslane["body"] = json.loads(req.data)
            return Odp()

        with mock.patch.object(asystent.urllib.request, "urlopen", urlopen):
            asystent._zapytaj_ollama("x")
        return wyslane["body"]

    @override_settings(OKRES_AI_MODEL="dowolny:model", OKRES_AI_THINK=False)
    def test_domyslnie_bez_rozumowania_dla_kazdego_modelu(self):
        body = self._wyslij()
        self.assertIs(body["think"], False)
        self.assertEqual(body["model"], "dowolny:model")

    @override_settings(OKRES_AI_THINK=True)
    def test_rozumowanie_wlaczane_zmienna(self):
        self.assertIs(self._wyslij()["think"], True)


@override_settings(OKRES_DEMO=True, OKRES_AI="ollama")
class AsystentOdpornoscTest(TestCase):
    def setUp(self):
        ZegarDemo(data=date(2026, 11, 21)).save()
        self.jan = User.objects.create_user("jan", first_name="Jan", last_name="Testowy")
        self.anna = User.objects.create_user("anna", first_name="Anna", last_name="Syntetyczna")
        self.o = Ocena.objects.create(arkusz="C", oceniany=self.jan, oceniajacy=self.anna, poczatek_okresu=date(2025, 3, 17))
        self.n = self.o.dodaj_obserwacje(self.anna, date(2026, 5, 4), "Raport 5 dni po terminie", "rzetelnosc")

    def _zestaw(self, odpowiedz):
        with mock.patch.object(asystent, "_zapytaj_ollama", return_value=json.dumps(odpowiedz)):
            return asystent.zestaw(self.o, self.anna)

    def test_formaty_identyfikatorow_notatek(self):
        pk = self.n.pk
        for zrodla in ([pk], [str(pk)], [f"N{pk}"], [f"[N{pk}]"], [f"[{pk}]"], [f" n{pk} "], pk, f"N{pk}"):
            with self.subTest(zrodla=zrodla):
                z = self._zestaw({"kryteria": {"rzetelnosc": [{"zdanie": "Raport po terminie.", "zrodla": zrodla}]}})
                punkty = {g["kod"]: g["punkty"] for g in z.kryteria}["rzetelnosc"]
                self.assertEqual([p.zrodla for p in punkty], [[pk]])
                self.assertEqual(z.tryb, "ai")

    def test_smieci_odrzucane_bez_bledu(self):
        z = self._zestaw({"kryteria": {"rzetelnosc": ["tekst zamiast obiektu", 12, None,
                                                      {"zdanie": "Bez źródła", "zrodla": ["abc", True, "N", "[]"]},
                                                      {"zdanie": "", "zrodla": [self.n.pk]}],
                                       "komunikacja": "nie lista"}})
        punkty = {g["kod"]: g["punkty"] for g in z.kryteria}
        self.assertEqual(punkty["rzetelnosc"], [])
        self.assertIn("Odrzucono zdania bez źródła: 6", z.komunikat)
        for odp in ([], "tekst", {"kryteria": []}, {"kryteria": "x"}, None):
            with self.subTest(odp=odp):
                self.assertEqual(self._zestaw(odp).tryb, "ai")

    def test_widok_nie_konczy_sie_bledem_przy_smieciach(self):
        self.o.zatwierdz_kryteria(date(2025, 4, 1))
        self.o.potwierdz_kryteria()
        self.client.force_login(self.anna)
        with mock.patch.object(asystent, "_zapytaj_ollama", return_value=json.dumps({"kryteria": {"rzetelnosc": ["x", 1]}})):
            r = self.client.post(reverse("oceny:asystent", args=[self.o.pk]), {})
        self.assertEqual(r.status_code, 200)

    def test_niedostepna_ollama_daje_jawny_komunikat_a_nie_wynik(self):
        import urllib.error

        with mock.patch.object(asystent.urllib.request, "urlopen", side_effect=urllib.error.URLError("connection refused")):
            z = asystent.zestaw(self.o, self.anna)
        self.assertEqual(z.tryb, "bez_ai")
        self.assertIn("Model lokalny niedostępny", z.komunikat)
        self.assertFalse(any(p.ai for g in z.kryteria for p in g["punkty"]))

    def test_niepoprawny_json_z_modelu_jawnie_oznaczony(self):
        with mock.patch.object(asystent, "_zapytaj_ollama", return_value="to nie jest JSON"):
            z = asystent.zestaw(self.o, self.anna)
        self.assertEqual(z.tryb, "bez_ai")
        self.assertIn("niedostępny", z.komunikat)
