from django.core.management.base import BaseCommand, CommandError

from oceny import rozwoj, rules


class Command(BaseCommand):
    help = ("Sprawdza pakiety reguł (wymagane klucze, spójność, przykłady wejście → wynik) przed aktywacją, "
            "a bez argumentów także katalog działań rozwojowych (rules/rozwoj.yaml).")

    def add_arguments(self, parser):
        parser.add_argument("wersje", nargs="*", help="Kody pakietów; domyślnie wszystkie z katalogu rules/.")

    def handle(self, *args, **options):
        wersje = options["wersje"] or [w["kod"] for w in rules.dostepne_wersje()]
        bledne = 0
        for w in wersje:
            bledy = rules.sprawdz(w)
            if bledy:
                bledne += 1
                self.stdout.write(self.style.ERROR(f"✗ {w}"))
                for b in bledy:
                    self.stdout.write(f"    {b}")
            else:
                przyklady = len(rules.load(w).get("przyklady", []))
                self.stdout.write(self.style.SUCCESS(f"✓ {w} ({przyklady} przykładów)"))
        if not options["wersje"]:
            bledy = rozwoj.sprawdz()
            if bledy:
                bledne += 1
                self.stdout.write(self.style.ERROR("✗ rozwoj (katalog działań rozwojowych)"))
                for b in bledy:
                    self.stdout.write(f"    {b}")
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ rozwoj ({len(rozwoj.katalog()['kryteria'])} kryteriów)"))
        if bledne:
            raise CommandError(f"Pakiety z błędami: {bledne}. Dotychczasowa wersja pozostaje aktywna.")
