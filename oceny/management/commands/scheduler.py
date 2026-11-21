from django.core.management.base import BaseCommand

from oceny import scheduler


class Command(BaseCommand):
    help = "Przypomnienia o terminach i zakładanie kolejnych okresów oceny (uruchamiać codziennie, np. z cron)."

    def handle(self, *args, **options):
        wynik = scheduler.uruchom()
        self.stdout.write(f"Przypomnienia: {wynik['przypomnienia']}, nowe sprawy: {wynik['nowe_sprawy']}")
