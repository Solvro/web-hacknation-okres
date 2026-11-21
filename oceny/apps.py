from django.apps import AppConfig


class OcenyConfig(AppConfig):
    name = 'oceny'

    def ready(self):
        from django.db.models import fields

        from . import poczta  # noqa: F401 - rejestracja sprawdzenia konfiguracji poczty

        # Django 6.1 nie ma jeszcze polskiego tłumaczenia pustej opcji list wyboru („- Select an option -”).
        fields.BLANK_CHOICE_LABEL = "— wybierz —"

        # W panelu kadr i opisach spraw osoba to imię i nazwisko, nie login (login zostaje w kolumnie konta).
        from django.contrib.auth.models import User

        User.__str__ = lambda u: u.get_full_name() or u.username
