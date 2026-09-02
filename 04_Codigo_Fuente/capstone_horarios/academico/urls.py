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
    # ======================================================
    # FACULTADES
    # ======================================================
    path(
        "facultades/",
        views.facultades,
        name="facultades",
    ),
    path(
        "facultades/nueva/",
        views.facultad_crear,
        name="facultad_crear",
    ),
    path(
        "facultades/<int:facultad_id>/editar/",
        views.facultad_editar,
        name="facultad_editar",
    ),
    path(
        "facultades/<int:facultad_id>/eliminar/",
        views.facultad_eliminar,
        name="facultad_eliminar",
    ),
    # ======================================================
    # PROGRAMAS ACADÉMICOS
    # ======================================================
    path(
        "programas/",
        views.programas_academicos,
        name="programas_academicos",
    ),
    path(
        "programas/nuevo/",
        views.programa_crear,
        name="programa_crear",
    ),
    path(
        "programas/<int:programa_id>/editar/",
        views.programa_editar,
        name="programa_editar",
    ),
    path(
        "programas/<int:programa_id>/eliminar/",
        views.programa_eliminar,
        name="programa_eliminar",
    ),
    # ======================================================
    # PERIODOS ACADÉMICOS
    # ======================================================
    path(
        "periodos/",
        views.periodos_academicos,
        name="periodos_academicos",
    ),
    path(
        "periodos/nuevo/",
        views.periodo_crear,
        name="periodo_crear",
    ),
    path(
        "periodos/<int:periodo_id>/editar/",
        views.periodo_editar,
        name="periodo_editar",
    ),
    path(
        "periodos/<int:periodo_id>/eliminar/",
        views.periodo_eliminar,
        name="periodo_eliminar",
    ),
    # ======================================================
    # SEMESTRES
    # ======================================================
    path(
        "semestres/",
        views.semestres,
        name="semestres",
    ),
    path(
        "semestres/nuevo/",
        views.semestre_crear,
        name="semestre_crear",
    ),
    path(
        "semestres/<int:semestre_id>/editar/",
        views.semestre_editar,
        name="semestre_editar",
    ),
    path(
        "semestres/<int:semestre_id>/eliminar/",
        views.semestre_eliminar,
        name="semestre_eliminar",
    ),
    # ======================================================
    # MODALIDADES
    # ======================================================
    path(
        "modalidades/",
        views.modalidades,
        name="modalidades",
    ),
    path(
        "modalidades/nueva/",
        views.modalidad_crear,
        name="modalidad_crear",
    ),
    path(
        "modalidades/<int:modalidad_id>/editar/",
        views.modalidad_editar,
        name="modalidad_editar",
    ),
    path(
        "modalidades/<int:modalidad_id>/eliminar/",
        views.modalidad_eliminar,
        name="modalidad_eliminar",
    ),
    # ======================================================
    # ÁREAS ACADÉMICAS
    # ======================================================
    path(
        "areas-academicas/",
        views.areas_academicas,
        name="areas_academicas",
    ),
    path(
        "areas-academicas/nueva/",
        views.area_crear,
        name="area_crear",
    ),
    path(
        "areas-academicas/<int:area_id>/editar/",
        views.area_editar,
        name="area_editar",
    ),
    path(
        "areas-academicas/<int:area_id>/eliminar/",
        views.area_eliminar,
        name="area_eliminar",
    ),
    # ======================================================
    # ASIGNATURAS
    # ======================================================
    path(
        "asignaturas/",
        views.asignaturas,
        name="asignaturas",
    ),
    path(
        "asignaturas/nueva/",
        views.asignatura_crear,
        name="asignatura_crear",
    ),
    path(
        "asignaturas/<int:asignatura_id>/editar/",
        views.asignatura_editar,
        name="asignatura_editar",
    ),
    path(
        "asignaturas/<int:asignatura_id>/eliminar/",
        views.asignatura_eliminar,
        name="asignatura_eliminar",
    ),
    # ======================================================
    # PLANES DE ESTUDIO
    # ======================================================
    path(
        "planes-estudio/",
        views.planes_estudio,
        name="planes_estudio",
    ),
    path(
        "planes-estudio/nuevo/",
        views.plan_estudio_crear,
        name="plan_estudio_crear",
    ),
    path(
        "planes-estudio/<int:plan_id>/editar/",
        views.plan_estudio_editar,
        name="plan_estudio_editar",
    ),
    path(
        "planes-estudio/<int:plan_id>/eliminar/",
        views.plan_estudio_eliminar,
        name="plan_estudio_eliminar",
    ),
    # ======================================================
    # AULAS
    # ======================================================
    path(
        "aulas/",
        views.aulas,
        name="aulas",
    ),
    path(
        "aulas/nueva/",
        views.aula_crear,
        name="aula_crear",
    ),
    path(
        "aulas/<int:aula_id>/editar/",
        views.aula_editar,
        name="aula_editar",
    ),
    path(
        "aulas/<int:aula_id>/eliminar/",
        views.aula_eliminar,
        name="aula_eliminar",
    ),
    # ======================================================
    # GRUPOS
    # ======================================================
    path(
        "grupos/",
        views.grupos,
        name="grupos",
    ),
    path(
        "grupos/nuevo/",
        views.grupo_crear,
        name="grupo_crear",
    ),
    path(
        "grupos/<int:grupo_id>/editar/",
        views.grupo_editar,
        name="grupo_editar",
    ),
    path(
        "grupos/<int:grupo_id>/eliminar/",
        views.grupo_eliminar,
        name="grupo_eliminar",
    ),
]
