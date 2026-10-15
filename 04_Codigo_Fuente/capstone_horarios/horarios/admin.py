from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from .services import operacion_planificacion, revalidar_oferta
from .forms import HorarioAdminForm

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


class PlanificacionSeguraAdmin:
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method != "POST":
            return super().changeform_view(request, object_id, form_url, extra_context)
        ids = set()
        if object_id:
            campo = "profesor_id" if self.model is OfertaAcademica else "oferta__profesor_id"
            ids.update(self.model.objects.filter(pk=object_id).values_list(campo, flat=True))
        if self.model is OfertaAcademica:
            valor = request.POST.get("profesor", "")
            if valor.isdigit():
                ids.add(int(valor))
        else:
            valor = request.POST.get("oferta", "")
            if valor.isdigit():
                ids.update(OfertaAcademica.objects.filter(pk=int(valor)).values_list("profesor_id", flat=True))
        try:
            with operacion_planificacion(ids):
                return super().changeform_view(request, object_id, form_url, extra_context)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            return HttpResponseRedirect(request.path)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if self.model is OfertaAcademica:
            revalidar_oferta(form.instance)


@admin.register(OfertaAcademica)
class OfertaAcademicaAdmin(PlanificacionSeguraAdmin, admin.ModelAdmin):

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
class HorarioAdmin(PlanificacionSeguraAdmin, admin.ModelAdmin):
    form = HorarioAdminForm

    list_display = (
        "asignatura",
        "profesor",
        "grupos",
        "sede",
        "aula_estado",
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
        "sede",
        "oferta__modalidad",
        "activo",
    )

    list_select_related = (
        "oferta",
        "oferta__asignatura",
        "oferta__profesor",
        "oferta__periodo",
        "aula",
        "sede",
    )

    @admin.display(description="Aula")
    def aula_estado(self, obj):
        return obj.aula.nombre if obj.aula_id else "Aula pendiente"

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
