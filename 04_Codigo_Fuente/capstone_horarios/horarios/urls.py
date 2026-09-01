from django.urls import path

from . import views

urlpatterns = [
    path(
        "",
        views.inicio,
        name="inicio",
    ),
    path(
        "planificacion/",
        views.planificacion,
        name="planificacion",
    ),
    path(
        "planificacion/nueva/",
        views.nueva_asignacion,
        name="nueva_asignacion",
    ),
    path(
        "planificacion/editar/<int:horario_id>/",
        views.editar_asignacion,
        name="editar_asignacion",
    ),
    path(
        "planificacion/eliminar/<int:horario_id>/",
        views.eliminar_asignacion,
        name="eliminar_asignacion",
    ),
    path(
        "planificacion/exportar-excel/",
        views.exportar_excel,
        name="exportar_excel",
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
        "ajax/programas/",
        views.cargar_programas,
        name="cargar_programas",
    ),
    # Ruta temporal de compatibilidad con el JavaScript anterior.
    # La eliminaremos cuando cambiemos Carrera por Programa Académico
    # en los templates y en selects.js.
    path(
        "ajax/carreras/",
        views.cargar_programas,
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
    path(
        "ajax/grupos/",
        views.cargar_grupos,
        name="cargar_grupos",
    ),
]
