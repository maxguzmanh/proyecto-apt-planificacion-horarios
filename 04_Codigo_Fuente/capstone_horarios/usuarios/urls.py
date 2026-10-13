from django.contrib.auth import views as auth_views
from django.urls import path
from django.contrib.auth.urls import urlpatterns as rutas_django
from .views import UniPlanLoginView

urlpatterns = [
    path(
        "login/",
        UniPlanLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]

# Conservar las rutas Django de contraseña/restablecimiento existentes.
urlpatterns += [ruta for ruta in rutas_django if ruta.name not in ("login", "logout")]
