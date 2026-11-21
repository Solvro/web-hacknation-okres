from datetime import date, datetime

from django.core.exceptions import ValidationError


def z_formularza(wartosc: str | None, pole: str = "data") -> date | None:
    """Data z pola formularza: RRRR-MM-DD (input type=date) albo DD.MM.RRRR (przeglądarka bez kalendarza).
    Puste pole daje None; nieczytelna wartość to błąd, a nie cicha zamiana na dzisiejszą datę."""
    tekst = (wartosc or "").strip()
    if not tekst:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(tekst, fmt).date()
        except ValueError:
            pass
    raise ValidationError({pole: f"Nie rozpoznano daty „{tekst}”. Podaj datę w formacie DD.MM.RRRR, np. 21.11.2026."})
