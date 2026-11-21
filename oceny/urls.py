from django.urls import path

from . import views

app_name = "oceny"
urlpatterns = [
    path("<int:pk>/", views.szczegoly, name="szczegoly"),
    path("<int:pk>/kryteria/", views.ustaw_kryteria, name="ustaw_kryteria"),
    path("<int:pk>/kryteria/potwierdz/", views.potwierdz_kryteria, name="potwierdz_kryteria"),
    path("<int:pk>/podglad/", views.podglad_wyniku, name="podglad_wyniku"),
    path("<int:pk>/sporzadz/", views.sporzadz, name="sporzadz"),
]
