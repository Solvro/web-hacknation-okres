import io

from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings

from . import poczta


class PocztaBezSMTPTest(SimpleTestCase):
    def test_wiadomosc_w_logu_z_ostrzezeniem(self):
        strumien = io.StringIO()
        with self.assertLogs("okres.poczta", level="WARNING") as logi:
            wyslane = poczta.BezSMTP(stream=strumien).send_messages([EmailMessage("Temat", "Treść", to=["a@urzad.local"])])
        self.assertEqual(wyslane, 1)
        self.assertIn("Temat", strumien.getvalue())
        self.assertIn("OKRES_SMTP_HOST", logi.output[0])

    @override_settings(MAILERS={"default": {"BACKEND": "oceny.poczta.BezSMTP"}})
    def test_ostrzezenie_przy_check_deploy_zamiast_bledu(self):
        [w] = poczta.sprawdz_poczte(None)
        self.assertEqual(w.id, "okres.W001")
        self.assertFalse(w.is_serious())

    @override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"}})
    def test_brak_ostrzezenia_przy_smtp(self):
        self.assertEqual(poczta.sprawdz_poczte(None), [])
