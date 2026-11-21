from django.urls import path

from . import views

app_name = "oceny"
urlpatterns = [
    path("", views.moje_sprawy, name="moje_sprawy"),
    path("<int:pk>/termin/<str:rodzaj>/", views.jak_obliczono, name="jak_obliczono"),
    path("<int:pk>/kryteria/zatwierdz/", views.zatwierdz_kryteria, name="zatwierdz_kryteria"),
    path("<int:pk>/", views.szczegoly, name="szczegoly"),
    path("<int:pk>/kryteria/", views.ustaw_kryteria, name="ustaw_kryteria"),
    path("<int:pk>/kryteria/potwierdz/", views.potwierdz_kryteria, name="potwierdz_kryteria"),
    path("<int:pk>/podglad/", views.podglad_wyniku, name="podglad_wyniku"),
    path("<int:pk>/sporzadz/", views.sporzadz, name="sporzadz"),
    path("<int:pk>/zapoznanie/", views.potwierdz_zapoznanie, name="potwierdz_zapoznanie"),
    path("<int:pk>/zapoznanie/fikcja/", views.fikcja_zapoznania, name="fikcja_zapoznania"),
    path("<int:pk>/sprzeciw/", views.zloz_sprzeciw, name="zloz_sprzeciw"),
]
