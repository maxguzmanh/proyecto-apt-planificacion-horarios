from django.contrib import admin

from .models import (
    Grupo,
    Horario,
    OfertaAcademica,
    OfertaGrupo,
)

# ==========================================================
# GRUPOS
# ==========================================================


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "programa",
        "centro_tutorial",
        "periodo",
        "semestre",
        "activo",
    )

    search_fields = (
        "codigo",
        "programa__codigo",
        "programa__nombre",
        "centro_tutorial__codigo",
        "centro_tutorial__nombre",
    )

    list_filter = (
        "centro_tutorial",
        "programa__facultad",
        "programa",
        "periodo",
        "semestre",
        "activo",
    )

    list_select_related = (
        "programa",
        "centro_tutorial",
        "periodo",
        "semestre",
    )


# ==========================================================
# OFERTA - GRUPO INLINE
# ==========================================================


class OfertaGrupoInline(admin.TabularInline):

    model = OfertaGrupo

    extra = 1

    fields = (
        "grupo",
        "cupos",
    )


# ==========================================================
# OFERTA ACADÉMICA
# ==========================================================


@admin.register(OfertaAcademica)
class OfertaAcademicaAdmin(admin.ModelAdmin):

    list_display = (
        "asignatura",
        "profesor",
        "periodo",
        "modalidad",
        "cantidad_grupos",
        "es_transversal",
        "activo",
    )

    search_fields = (
        "asignatura__codigo",
        "asignatura__nombre",
        "profesor__identificacion",
        "profesor__nombre",
        "profesor__apellido",
    )

    list_filter = (
        "periodo",
        "modalidad",
        "activo",
    )

    list_select_related = (
        "asignatura",
        "profesor",
        "periodo",
        "modalidad",
    )

    inlines = [
        OfertaGrupoInline,
    ]

    @admin.display(description="Grupos")
    def cantidad_grupos(self, obj):
        return obj.grupos.count()

    @admin.display(
        description="Transversal",
        boolean=True,
    )
    def es_transversal(self, obj):
        return obj.grupos.count() > 1


# ==========================================================
# OFERTA - GRUPO
# ==========================================================


@admin.register(OfertaGrupo)
class OfertaGrupoAdmin(admin.ModelAdmin):

    list_display = (
        "oferta",
        "grupo",
        "cupos",
    )

    search_fields = (
        "oferta__asignatura__codigo",
        "oferta__asignatura__nombre",
        "grupo__codigo",
        "grupo__programa__nombre",
    )

    list_filter = (
        "oferta__periodo",
        "grupo__centro_tutorial",
        "grupo__programa",
        "grupo__semestre",
    )

    list_select_related = (
        "oferta",
        "oferta__asignatura",
        "grupo",
        "grupo__programa",
    )


# ==========================================================
# HORARIOS
# ==========================================================


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):

    list_display = (
        "asignatura",
        "profesor",
        "grupos",
        "aula",
        "dia",
        "hora_inicio",
        "hora_fin",
        "periodo",
        "activo",
    )

    search_fields = (
        "oferta__asignatura__codigo",
        "oferta__asignatura__nombre",
        "oferta__profesor__identificacion",
        "oferta__profesor__nombre",
        "oferta__profesor__apellido",
        "aula__codigo",
        "aula__nombre",
        "oferta__grupos__codigo",
    )

    list_filter = (
        "oferta__periodo",
        "dia",
        "aula__sede",
        "oferta__modalidad",
        "activo",
    )

    list_select_related = (
        "oferta",
        "oferta__asignatura",
        "oferta__profesor",
        "oferta__periodo",
        "aula",
    )

    @admin.display(description="Asignatura")
    def asignatura(self, obj):
        return obj.oferta.asignatura

    @admin.display(description="Profesor")
    def profesor(self, obj):
        return obj.oferta.profesor

    @admin.display(description="Periodo")
    def periodo(self, obj):
        return obj.oferta.periodo

    @admin.display(description="Grupos")
    def grupos(self, obj):

        return ", ".join(grupo.codigo for grupo in obj.oferta.grupos.all())


# Register your models here.
