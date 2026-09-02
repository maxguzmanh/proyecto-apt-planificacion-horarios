from django.contrib import admin
from django.urls import include, path

urlpatterns = [
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
        include("django.contrib.auth.urls"),
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
