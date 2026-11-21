from django.contrib import admin

from .models import Korekta, Ocena, Sprzeciw, ZegarDemo


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

    def get_readonly_fields(self, request, obj=None):
        # Pola zablokowane zmienia się tylko metodą korekty (z powodem i śladem), nie przez zwykły zapis formularza.
        zawsze = ["srednia", "poziom", "pozytywna", "sporzadzona_at", "kryteria_potwierdzone_at", "wersja_regul"]
        if obj and obj.kryteria_zablokowane:
            zawsze += ["arkusz", "oceniany", "oceniajacy", "kryteria_dodatkowe"]
        if obj and obj.sporzadzona:
            zawsze += ["oceny_czastkowe", "data_rozmowy_oceniajacej", "uzasadnienie", "wnioski_iprz", "data_sporzadzenia"]
        if obj and obj.zapoznany:
            zawsze += ["data_zapoznania", "sposob_zapoznania", "uwagi_zapoznania"]
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
    list_display = ("ocena", "data_zlozenia")


@admin.register(ZegarDemo)
class ZegarDemoAdmin(admin.ModelAdmin):
    list_display = ("data",)
