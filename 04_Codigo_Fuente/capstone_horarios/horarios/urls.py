from django.urls import path

from . import views, profesor_views, exportacion_views

urlpatterns = [
    path("planificacion/exportar/", exportacion_views.exportacion_planificacion, name="exportacion_planificacion"),
    path("ajax/exportacion/semestres/", exportacion_views.semestres_exportacion, name="semestres_exportacion"),
    path("profesor/", profesor_views.profesor_inicio, name="profesor_inicio"),
    path("profesor/horario/", profesor_views.profesor_horario, name="profesor_horario"),
    path("profesor/horario/exportar-pdf/", profesor_views.profesor_horario_pdf, name="profesor_horario_pdf"),
    path("profesor/calendario/eventos/", profesor_views.profesor_eventos, name="profesor_eventos"),
    path("profesor/calendario/horarios/<int:horario_id>/detalle/", profesor_views.profesor_detalle, name="profesor_detalle"),
    path("planificacion/calendario/ofertas/<int:oferta_id>/ocupaciones/", views.ocupaciones_oferta, name="ocupaciones_oferta"),
    path("planificacion/calendario/eliminar/", views.eliminar_horario_calendario, name="eliminar_horario_calendario"),
    path("planificacion/calendario/redimensionar/", views.redimensionar_horario, name="redimensionar_horario"),
    path("planificacion/calendario/asignar-aula/", views.asignar_aula_horario, name="asignar_aula_horario"),
    path("planificacion/calendario/horarios/<int:horario_id>/aulas/", views.aulas_horario_calendario, name="aulas_horario_calendario"),
    path("ajax/modalidades/", views.cargar_modalidades, name="cargar_modalidades"),
    path("planificacion/calendario/ofertas/<int:oferta_id>/", views.detalle_oferta_calendario, name="detalle_oferta_calendario"),
    path("planificacion/calendario/crear/", views.crear_horario_oferta, name="crear_horario_oferta"),
    path("planificacion/calendario/eventos/", views.eventos_calendario, name="eventos_calendario"),
    path("planificacion/calendario/mover/", views.mover_horario, name="mover_horario"),
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
        exportacion_views.descargar_excel,
        name="exportar_excel",
    ),
    # Selects dependientes
    path(
        "ajax/sedes/",
        views.cargar_sedes,
        name="cargar_sedes",
    ),
    path(
        "ajax/aulas/",
        views.cargar_aulas,
        name="cargar_aulas",
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
