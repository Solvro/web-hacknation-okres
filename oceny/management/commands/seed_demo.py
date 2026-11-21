from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from oceny.models import Ocena

# Dane wyłącznie syntetyczne. Hasło jest jawne, więc komenda działa tylko w trybie deweloperskim.
OSOBY = [
    ("kadry", "Krystyna", "Kadrowa (DEMO)", True),
    ("oceniajaca", "Anna", "Syntetyczna (DEMO)", False),
    ("oceniany", "Jan", "Testowy (DEMO)", False),
]
HASLO = "demo"


class Command(BaseCommand):
    help = "Tworzy syntetycznych użytkowników i ocenę na arkuszu C do demonstracji."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo działa tylko przy DJANGO_DEBUG=1.")
        konta = {}
        for login, imie, nazwisko, kadry in OSOBY:
            u, _ = User.objects.get_or_create(username=login, defaults={"first_name": imie, "last_name": nazwisko})
            u.is_staff = u.is_superuser = kadry
            u.set_password(HASLO)
            u.save()
            konta[login] = u
        ocena, _ = Ocena.objects.get_or_create(arkusz="C", oceniany=konta["oceniany"], oceniajacy=konta["oceniajaca"])
        self.stdout.write(f"Konta: {', '.join(konta)} (hasło: {HASLO}). Ocena: /oceny/{ocena.pk}/")
