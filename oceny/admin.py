from django.contrib import admin

from .models import Korekta, Nieobecnosc, Ocena, Pracownik, Sprzeciw, Urzad, ZegarDemo


class KorektaInline(admin.TabularInline):
    model = Korekta
    extra = 0
    can_delete = False
    readonly_fields = ("kiedy", "kto", "pole", "przed", "po", "powod")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ocena)
class OcenaAdmin(admin.ModelAdmin):
    list_display = ("id", "arkusz", "oceniany", "oceniajacy", "kryteria_potwierdzone_at", "sporzadzona_at", "pozytywna")
    list_filter = ("arkusz", "pozytywna")
    inlines = [KorektaInline]

    def has_delete_permission(self, request, obj=None):
        return False  # akta osobowe; usunięcie wyłącznie po upływie retencji, poza zwykłym panelem

    def get_readonly_fields(self, request, obj=None):
        # Pola zablokowane zmienia się tylko metodą korekty (z powodem i śladem), nie przez zwykły zapis formularza.
        if obj and obj.sporzadzona:
            return [f.name for f in self.model._meta.fields]
        zawsze = ["srednia", "poziom", "pozytywna", "sporzadzona_at", "kryteria_potwierdzone_at", "wersja_regul",
                  "kryteria_zatwierdzone_at", "data_zatwierdzenia_kryteriow", "data_potwierdzenia_kryteriow", "wersja",
                  "anulowana_powod"]
        if obj and obj.kryteria_zatwierdzone:
            zawsze += ["arkusz", "oceniany", "kryteria_dodatkowe", "data_rozmowy_rozpoczynajacej", "miejscowosc_czesc_i",
                       "poczatek_okresu", "podstawa_poczatku", "poprzednia"]
        return zawsze


@admin.register(Korekta)
class KorektaAdmin(admin.ModelAdmin):
    list_display = ("kiedy", "ocena", "kto", "pole", "powod")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sprzeciw)
class SprzeciwAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ("ocena", "wersja", "data_zlozenia", "decyzja", "data_decyzji")
    readonly_fields = ("ocena", "wersja", "data_zlozenia", "tresc", "decyzja", "data_decyzji", "uzasadnienie_decyzji",
                       "rozpatrujacy")

    def has_add_permission(self, request):
        return False


@admin.register(ZegarDemo)
class ZegarDemoAdmin(admin.ModelAdmin):
    list_display = ("data",)


class NieobecnoscInline(admin.TabularInline):
    model = Nieobecnosc
    extra = 1


@admin.register(Pracownik)
class PracownikAdmin(admin.ModelAdmin):
    list_display = ("imie_nazwisko", "stanowisko", "komorka", "arkusz", "przelozony", "urzednik")
    list_filter = ("rodzaj_stanowiska", "urzednik", "komorka")
    search_fields = ("user__first_name", "user__last_name", "stanowisko", "komorka")
    inlines = [NieobecnoscInline]


@admin.register(Urzad)
class UrzadAdmin(admin.ModelAdmin):
    list_display = ("nazwa", "miejscowosc")
