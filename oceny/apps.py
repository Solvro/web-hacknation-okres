from django.apps import AppConfig


class OcenyConfig(AppConfig):
    name = 'oceny'

    def ready(self):
        from . import poczta  # noqa: F401 - rejestracja sprawdzenia konfiguracji poczty
