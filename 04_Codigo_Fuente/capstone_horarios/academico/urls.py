from django.urls import path

from . import views

urlpatterns = [
    # ======================================================
    # PANEL DE MANTENEDORES
    # ======================================================
    path(
        "",
        views.mantenedores,
        name="mantenedores",
    ),
    # ======================================================
    # PROFESORES
    # ======================================================
    path(
        "profesores/",
        views.profesores,
        name="profesores",
    ),
    path(
        "profesores/nuevo/",
        views.profesor_crear,
        name="profesor_crear",
    ),
    path(
        "profesores/<int:profesor_id>/editar/",
        views.profesor_editar,
        name="profesor_editar",
    ),
    path(
        "profesores/<int:profesor_id>/eliminar/",
        views.profesor_eliminar,
        name="profesor_eliminar",
    ),
    # ======================================================
    # CENTROS TUTORIALES
    # ======================================================
    path(
        "centros-tutoriales/",
        views.centros_tutoriales,
        name="centros_tutoriales",
    ),
    path(
        "centros-tutoriales/nuevo/",
        views.centro_tutorial_crear,
        name="centro_tutorial_crear",
    ),
    path(
        "centros-tutoriales/<int:centro_id>/editar/",
        views.centro_tutorial_editar,
        name="centro_tutorial_editar",
    ),
    path(
        "centros-tutoriales/<int:centro_id>/eliminar/",
        views.centro_tutorial_eliminar,
        name="centro_tutorial_eliminar",
    ),
    # ======================================================
    # SEDES
    # ======================================================
    path(
        "sedes/",
        views.sedes,
        name="sedes",
    ),
    path(
        "sedes/nueva/",
        views.sede_crear,
        name="sede_crear",
    ),
    path(
        "sedes/<int:sede_id>/editar/",
        views.sede_editar,
        name="sede_editar",
    ),
    path(
        "sedes/<int:sede_id>/eliminar/",
        views.sede_eliminar,
        name="sede_eliminar",
    ),
]
