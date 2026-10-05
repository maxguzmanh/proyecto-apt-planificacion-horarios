from django.contrib import admin

from .models import (
    AreaAcademica,
    Asignatura,
    Aula,
    CentroTutorial,
    Facultad,
    Modalidad,
    PeriodoAcademico,
    PlanEstudioAsignatura,
    Profesor,
    ProgramaAcademico,
    ProgramaCentroTutorial,
    Sede,
    Semestre,
)

# ==========================================================
# CENTROS TUTORIALES
# ==========================================================


@admin.register(CentroTutorial)
class CentroTutorialAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = ("activo",)


# ==========================================================
# SEDES
# ==========================================================


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "centro_tutorial",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
        "centro_tutorial__nombre",
    )

    list_filter = (
        "centro_tutorial",
        "activo",
    )

    list_select_related = ("centro_tutorial",)


# ==========================================================
# FACULTADES
# ==========================================================


@admin.register(Facultad)
class FacultadAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = ("activo",)


# ==========================================================
# PROGRAMAS ACADÉMICOS
# ==========================================================


@admin.register(ProgramaAcademico)
class ProgramaAcademicoAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "facultad",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
        "facultad__nombre",
    )

    list_filter = (
        "facultad",
        "activo",
    )

    list_select_related = ("facultad",)


# ==========================================================
# PROGRAMAS POR CENTRO TUTORIAL
# ==========================================================


@admin.register(ProgramaCentroTutorial)
class ProgramaCentroTutorialAdmin(admin.ModelAdmin):

    list_display = (
        "programa",
        "centro_tutorial",
        "activo",
    )

    search_fields = (
        "programa__codigo",
        "programa__nombre",
        "centro_tutorial__codigo",
        "centro_tutorial__nombre",
    )

    list_filter = (
        "centro_tutorial",
        "programa__facultad",
        "activo",
    )

    list_select_related = (
        "programa",
        "centro_tutorial",
    )


# ==========================================================
# PERIODOS ACADÉMICOS
# ==========================================================


@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "fecha_inicio",
        "fecha_fin",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = ("activo",)


# ==========================================================
# SEMESTRES
# ==========================================================


@admin.register(Semestre)
class SemestreAdmin(admin.ModelAdmin):

    list_display = (
        "numero",
        "nombre_semestre",
    )

    ordering = ("numero",)

    @admin.display(description="Semestre")
    def nombre_semestre(self, obj):
        return obj.get_numero_display()


# ==========================================================
# MODALIDADES
# ==========================================================


@admin.register(Modalidad)
class ModalidadAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = ("activo",)


# ==========================================================
# ÁREAS ACADÉMICAS
# ==========================================================


@admin.register(AreaAcademica)
class AreaAcademicaAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = ("activo",)


# ==========================================================
# ASIGNATURAS
# ==========================================================


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_filter = ("activo",)


# ==========================================================
# PLAN DE ESTUDIO
# ==========================================================


@admin.register(PlanEstudioAsignatura)
class PlanEstudioAsignaturaAdmin(admin.ModelAdmin):

    list_display = (
        "programa",
        "asignatura",
        "semestre",
        "creditos",
        "area_academica",
        "activo",
    )

    search_fields = (
        "programa__codigo",
        "programa__nombre",
        "asignatura__codigo",
        "asignatura__nombre",
    )

    list_filter = (
        "programa__facultad",
        "programa",
        "semestre",
        "area_academica",
        "activo",
    )

    list_select_related = (
        "programa",
        "asignatura",
        "semestre",
        "area_academica",
    )


# ==========================================================
# PROFESORES
# ==========================================================


@admin.register(Profesor)
class ProfesorAdmin(admin.ModelAdmin):

    list_display = (
        "identificacion",
        "nombre",
        "apellido",
        "correo_institucional",
        "usuario",
        "activo",
    )

    search_fields = (
        "identificacion",
        "nombre",
        "apellido",
        "correo_institucional",
    )

    list_filter = ("activo",)

    list_select_related = ("usuario",)


# ==========================================================
# AULAS
# ==========================================================


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "sede",
        "capacidad",
        "tipo",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
        "sede__nombre",
        "sede__centro_tutorial__nombre",
    )

    list_filter = (
        "tipo",
        "sede__centro_tutorial",
        "sede",
        "activo",
    )

    list_select_related = (
        "sede",
        "sede__centro_tutorial",
    )


# Register your models here.
