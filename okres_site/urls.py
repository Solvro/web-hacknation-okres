"""
URL configuration for okres_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from oceny import views as oceny_views
from django.urls import include, path

admin.site.site_header = "OKRES · Panel kadr"
admin.site.site_title = "OKRES"
admin.site.index_title = "Administracja ocenami okresowymi"

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='oceny:moje_sprawy')),
    path('logowanie/', auth_views.LoginView.as_view(template_name='oceny/logowanie.html'), name='login'),
    path('demo/zaloguj/', oceny_views.demo_zaloguj, name='demo_zaloguj'),
    path('wyloguj/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('oceny/', include('oceny.urls')),
    path('partner/', include('partner.urls')),
]
