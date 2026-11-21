from django.urls import path

from . import views

app_name = "partner"
urlpatterns = [
    path("zespol/", views.zespol, name="zespol"),
    path("ja/", views.moje, name="moje"),
    path("pracownik/<int:pk>/zdarzenie/", views.dodaj_zdarzenie, name="dodaj_zdarzenie"),
    path("pracownik/<int:pk>/uzgodnienie/", views.uzgodnij, name="uzgodnij"),
    path("pracownik/<int:pk>/docenienie/", views.docen, name="docen"),
    path("uzgodnienie/<int:pk>/wynik/", views.wynik, name="wynik"),
    path("uzgodnienie/<int:pk>/perspektywa/", views.perspektywa, name="perspektywa"),
]
