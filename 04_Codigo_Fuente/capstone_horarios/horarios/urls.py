from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path(
        "planificacion/",
        views.planificacion,
        name="planificacion",
    ),
    # Selects dependientes
    path(
        "ajax/sedes/",
        views.cargar_sedes,
        name="cargar_sedes",
    ),
    path(
        "ajax/facultades/",
        views.cargar_facultades,
        name="cargar_facultades",
    ),
    path(
        "ajax/carreras/",
        views.cargar_carreras,
        name="cargar_carreras",
    ),
    path(
        "ajax/periodos/",
        views.cargar_periodos,
        name="cargar_periodos",
    ),
    path(
        "ajax/semestres/",
        views.cargar_semestres,
        name="cargar_semestres",
    ),
]
