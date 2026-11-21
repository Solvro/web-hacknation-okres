"""Poczta bez serwera SMTP: wiadomości trafiają do logu kontenera, a nie do adresatów.

Używana tylko, gdy urząd nie podał OKRES_SMTP_HOST. Powiadomienia w aplikacji (model Przypomnienie) działają
niezależnie od poczty, więc proces nie traci informacji o terminach.
"""

import logging

from django.conf import settings
from django.core.checks import Tags, register
from django.core.checks import Warning as Ostrzezenie
from django.core.mail.backends.console import EmailBackend as KonsolaBackend

log = logging.getLogger("okres.poczta")

KOMUNIKAT = ("Brak OKRES_SMTP_HOST: wiadomości e-mail nie są wysyłane, tylko zapisywane w logu. "
             "Powiadomienia w aplikacji działają bez zmian.")


class BezSMTP(KonsolaBackend):
    def send_messages(self, email_messages):
        if email_messages:
            log.warning(KOMUNIKAT)
        return super().send_messages(email_messages)


@register(Tags.mail, deploy=True)
def sprawdz_poczte(app_configs, **kwargs):
    backend = settings.MAILERS.get("default", {}).get("BACKEND", "")
    if backend == "oceny.poczta.BezSMTP":
        return [Ostrzezenie(KOMUNIKAT, hint="Podaj OKRES_SMTP_HOST (serwer SMTP urzędu), aby wysyłać powiadomienia e-mail.",
                            id="okres.W001")]
    return []
