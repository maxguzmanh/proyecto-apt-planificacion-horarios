from django.contrib import admin
from django.urls import include, path
from usuarios.views import acceso_no_configurado

urlpatterns = [
    path("acceso-no-configurado/", acceso_no_configurado, name="acceso_no_configurado"),
    # ======================================================
    # ADMINISTRACIÓN DJANGO
    # ======================================================
    path(
        "admin/",
        admin.site.urls,
    ),
    # ======================================================
    # AUTENTICACIÓN
    # ======================================================
    path(
        "accounts/",
        include("usuarios.urls"),
    ),
    # ======================================================
    # MANTENEDORES
    # ======================================================
    path(
        "mantenedores/",
        include("academico.urls"),
    ),
    # ======================================================
    # APLICACIÓN PRINCIPAL
    # ======================================================
    path(
        "",
        include("horarios.urls"),
    ),
]
