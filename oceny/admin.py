from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.auth import get_user_model
from django.utils.html import format_html

from .models import Korekta, Nieobecnosc, Ocena, Pracownik, Sprzeciw, Urzad, ZegarDemo


def _nazwisko(user) -> str:
    return (user.get_full_name() or user.username) if user else "—"


# Etykiety z polskimi znakami dla pól, których nazwy w modelach są bez diakrytyków (bez zmiany modeli i migracji).
# Działa dla pól edytowalnych i tylko do odczytu (Meta.labels formularza panelu).
ETYKIETY = {
    "miejscowosc": "miejscowość", "user": "konto użytkownika", "przelozony": "przełożony",
    "dyrektor_generalny": "dyrektor generalny", "stopien_sluzbowy": "stopień służbowy",
    "miejscowosc_pracy": "miejscowość pracy", "od": "od", "do": "do",
    "wersja_regul": "pakiet reguł", "oceniajacy": "oceniający", "podstawa_poczatku": "podstawa początku okresu",
    "poprzednia": "poprzednia ocena (sprawa)", "anulowana_powod": "powód anulowania",
    "termin_oceny_zmieniony": "zmieniony termin oceny", "termin_kryteriow_zmieniony": "zmieniony termin kryteriów",
    "najwczesniej_sporzadzenia": "najwcześniejsza data sporządzenia",
    "data_rozmowy_rozpoczynajacej": "data rozmowy rozpoczynającej",
    "kryteria_zatwierdzone_at": "zapis zatwierdzenia kryteriów (czas systemowy)",
    "data_zatwierdzenia_kryteriow": "data zatwierdzenia kryteriów", "miejscowosc_czesc_i": "miejscowość (część I)",
    "kryteria_potwierdzone_at": "zapis potwierdzenia kryteriów (czas systemowy)",
    "data_potwierdzenia_kryteriow": "data potwierdzenia kryteriów", "oceny_czastkowe": "oceny cząstkowe",
    "data_rozmowy_oceniajacej": "data rozmowy oceniającej", "wnioski_iprz": "wnioski dotyczące IPRZ",
    "sporzadzona_at": "zapis sporządzenia oceny (czas systemowy)", "data_sporzadzenia": "data sporządzenia",
    "srednia": "średnia", "miejscowosc_czesc_ii": "miejscowość (część II)", "poprz_ocena": "poprzednia ocena",
    "poprz_poziom": "poziom poprzedniej oceny", "poprz_data": "data poprzedniej oceny",
    "wniosek_stopien": "wniosek o kolejny stopień służbowy", "miejscowosc_zapoznania": "miejscowość zapoznania",
    "sposob_zapoznania": "sposób zapoznania", "powod": "powód", "data_zlozenia": "data złożenia", "tresc": "treść",
    "rozpatrujacy": "rozpatrujący",
}


ETYKIETY = {k: v[:1].upper() + v[1:] for k, v in ETYKIETY.items()}  # jak etykiety Django (capfirst)


class PolskieEtykietyInline:
    def get_formset(self, request, obj=None, **kwargs):
        return super().get_formset(request, obj, **{"labels": ETYKIETY} | kwargs)


class PolskiPanel(admin.ModelAdmin):
    """Tytuły z poprawną odmianą („Wybierz ocenę do zmiany”) i imiona z nazwiskami zamiast loginów na listach wyboru."""

    biernik = ""  # nazwa modelu w bierniku; pusta = verbose_name bez zmian

    def _biernik(self):
        return self.biernik or self.model._meta.verbose_name

    def changelist_view(self, request, extra_context=None):
        tryb = "do zmiany" if self.has_change_permission(request) else "do podglądu"
        return super().changelist_view(request, {"title": f"Wybierz {self._biernik()} {tryb}"} | (extra_context or {}))

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if object_id is None:
            tytul = f"Dodaj {self._biernik()}"
        else:
            obj = self.get_object(request, unquote(object_id))
            tytul = f"{'Zmień' if self.has_change_permission(request, obj) else 'Zobacz'} {self._biernik()}"
        return super().changeform_view(request, object_id, form_url, {"title": tytul} | (extra_context or {}))

    def get_form(self, request, obj=None, change=False, **kwargs):
        return super().get_form(request, obj, change, **{"labels": ETYKIETY} | kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        pole = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if pole is not None and db_field.related_model is get_user_model():
            pole.label_from_instance = _nazwisko
        return pole


class KorektaInline(PolskieEtykietyInline, admin.TabularInline):
    model = Korekta
    extra = 0
    can_delete = False
    readonly_fields = ("kiedy", "kto", "pole", "przed", "po", "powod")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ocena)
class OcenaAdmin(PolskiPanel):
    biernik = "ocenę"
    list_display = ("id", "arkusz", "kol_oceniany", "kol_oceniajacy", "kol_etap", "kol_kryteria", "kol_sporzadzona", "pozytywna")
    list_select_related = ("oceniany", "oceniajacy")

    @admin.display(description="Oceniany", ordering="oceniany__last_name")
    def kol_oceniany(self, obj):
        return _nazwisko(obj.oceniany)

    @admin.display(description="Oceniający", ordering="oceniajacy__last_name")
    def kol_oceniajacy(self, obj):
        return _nazwisko(obj.oceniajacy)

    @admin.display(description="Etap")
    def kol_etap(self, obj):
        return obj.etap_nazwa

    # Daty z arkusza (części I i II), nie techniczne znaczniki zapisu w systemie.
    @admin.display(description="Kryteria potwierdzone", ordering="data_potwierdzenia_kryteriow")
    def kol_kryteria(self, obj):
        return obj.data_potwierdzenia_kryteriow

    @admin.display(description="Ocena sporządzona", ordering="data_sporzadzenia")
    def kol_sporzadzona(self, obj):
        return obj.data_sporzadzenia

    list_filter = ("arkusz", "pozytywna")
    inlines = [KorektaInline]

    def has_delete_permission(self, request, obj=None):
        return False  # akta osobowe; usunięcie wyłącznie po upływie retencji, poza zwykłym panelem

    def get_fields(self, request, obj=None):
        # Techniczne znaczniki zapisu (*_at) przeczyłyby datom z arkusza (np. w danych demo); zostają w bazie i w eksporcie.
        return [f for f in super().get_fields(request, obj) if not f.endswith("_at")]

    def get_readonly_fields(self, request, obj=None):
        # Pola zablokowane zmienia się tylko metodą korekty (z powodem i śladem), nie przez zwykły zapis formularza.
        if obj and obj.sporzadzona:
            return [f.name for f in self.model._meta.fields]
        zawsze = ["srednia", "poziom", "pozytywna", "sporzadzona_at", "kryteria_potwierdzone_at", "wersja_regul",
                  "kryteria_zatwierdzone_at", "data_zatwierdzenia_kryteriow", "data_potwierdzenia_kryteriow", "wersja",
                  "anulowana_powod"]
        if obj and obj.kryteria_zatwierdzone:
            zawsze += ["arkusz", "oceniany", "kryteria_dodatkowe", "data_rozmowy_rozpoczynajacej", "miejscowosc_czesc_i", "cele_i_oczekiwania",
                       "poczatek_okresu", "podstawa_poczatku", "poprzednia"]
        return zawsze


@admin.register(Korekta)
class KorektaAdmin(PolskiPanel):
    biernik = "korektę"
    list_display = ("kiedy", "kol_ocena", "kol_kto", "pole", "kol_powod")

    @admin.display(description="Powód")
    def kol_powod(self, obj):
        return obj.powod

    @admin.display(description="Ocena")
    def kol_ocena(self, obj):
        return f"Ocena {obj.ocena_id} · {_nazwisko(obj.ocena.oceniany)}"

    @admin.display(description="Kto")
    def kol_kto(self, obj):
        return _nazwisko(obj.kto)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sprzeciw)
class SprzeciwAdmin(PolskiPanel):
    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ("kol_ocena", "wersja", "kol_data_zlozenia", "decyzja", "data_decyzji")

    @admin.display(description="Data złożenia", ordering="data_zlozenia")
    def kol_data_zlozenia(self, obj):
        return obj.data_zlozenia

    @admin.display(description="Ocena")
    def kol_ocena(self, obj):
        return f"Ocena {obj.ocena_id} · {_nazwisko(obj.ocena.oceniany)}"
    readonly_fields = ("ocena", "wersja", "data_zlozenia", "tresc", "decyzja", "data_decyzji", "uzasadnienie_decyzji",
                       "rozpatrujacy")

    def has_add_permission(self, request):
        return False


@admin.register(ZegarDemo)
class ZegarDemoAdmin(PolskiPanel):
    list_display = ("data",)


class NieobecnoscInline(PolskieEtykietyInline, admin.TabularInline):
    model = Nieobecnosc
    extra = 1


def _biezace_sprawy() -> dict:
    """Ostatnia niezakończona i nieanulowana sprawa każdego ocenianego (user_id → Ocena)."""
    return {o.oceniany_id: o for o in Ocena.objects.order_by("pk") if o.etap not in ("zakonczona", "anulowana")}


class BiezacaSprawaFilter(admin.SimpleListFilter):
    title = "bieżąca sprawa"
    parameter_name = "sprawa"

    def lookups(self, request, model_admin):
        return [("brak", "brak bieżącej sprawy"), ("jest", "jest bieżąca sprawa")]

    def queryset(self, request, queryset):
        if self.value() not in ("brak", "jest"):
            return queryset
        z_sprawa = _biezace_sprawy().keys()
        return queryset.exclude(user_id__in=z_sprawa) if self.value() == "brak" else queryset.filter(user_id__in=z_sprawa)


@admin.register(Pracownik)
class PracownikAdmin(PolskiPanel):
    biernik = "pracownika"
    list_display = ("kol_imie_nazwisko", "stanowisko", "komorka", "kol_arkusz", "kol_przelozony", "urzednik", "kol_sprawa")
    list_filter = (BiezacaSprawaFilter, "rodzaj_stanowiska", "urzednik", "komorka")
    list_select_related = ("user", "przelozony__user")

    def changelist_view(self, request, extra_context=None):
        self._sprawy = _biezace_sprawy()  # jedno zapytanie na listę zamiast jednego na wiersz
        return super().changelist_view(request, extra_context)

    @admin.display(description="Imię i nazwisko", ordering="user__last_name")
    def kol_imie_nazwisko(self, obj):
        return obj.imie_nazwisko

    @admin.display(description="Arkusz")
    def kol_arkusz(self, obj):
        return obj.arkusz

    @admin.display(description="Przełożony", ordering="przelozony__user__last_name")
    def kol_przelozony(self, obj):
        return obj.przelozony.imie_nazwisko if obj.przelozony else "—"

    @admin.display(description="Bieżąca sprawa")
    def kol_sprawa(self, obj):
        o = getattr(self, "_sprawy", {}).get(obj.user_id)
        if o is None:
            return format_html('<strong class="brak-sprawy">{}</strong>', "brak bieżącej sprawy")
        return f"nr {o.pk} · {o.etap_nazwa}"
    search_fields = ("user__first_name", "user__last_name", "stanowisko", "komorka")
    inlines = [NieobecnoscInline]


@admin.register(Urzad)
class UrzadAdmin(PolskiPanel):
    list_display = ("nazwa", "kol_miejscowosc")

    @admin.display(description="Miejscowość")
    def kol_miejscowosc(self, obj):
        return obj.miejscowosc
