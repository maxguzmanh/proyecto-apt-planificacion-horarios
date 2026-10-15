from functools import wraps
from urllib.parse import urlencode
from django.urls import reverse
from academico.models import Semestre
from academico.choices import DiaSemana
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from usuarios.roles import puede_dashboard
from .contexto_academico import semestres_del_programa
from .exportacion_forms import ExportacionPlanificacionForm
from .exportacion import crear_workbook, nombre_archivo, filas_exportacion, valores_presentacion, ENCABEZADOS


def acceso_exportacion(vista):
    @login_required
    @wraps(vista)
    def protegida(request, *args, **kwargs):
        if not puede_dashboard(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return protegida


def contexto_resultados(form):
    d = form.cleaned_data
    orden_semestres = {nombre: numero for numero, nombre in Semestre._meta.get_field("numero").choices}
    orden_dias = {nombre: numero for numero, (_, nombre) in enumerate(DiaSemana.choices)}
    filas = [{"valores": valores_presentacion(f), "semestre_orden": orden_semestres.get(f[4], 0),
        "dia_orden": orden_dias.get(f[10], 0)} for f in filas_exportacion(d)]
    parametros = {c: d[c].pk for c in ("periodo", "centro", "facultad", "programa", "semestre") if d.get(c)}
    if d.get("busqueda"):
        parametros["busqueda"] = d["busqueda"]
    return {"filas": filas, "encabezados": ENCABEZADOS, "filtrado": True,
        "export_url": reverse("exportar_excel") + "?" + urlencode(parametros)}


@acceso_exportacion
@require_GET
def exportacion_planificacion(request):
    filtrar = request.GET.get("filtrar") == "1"
    parametros = request.GET.copy()
    parametros.pop("busqueda", None)  # Filtrar inicia una consulta académica nueva.
    form = ExportacionPlanificacionForm(parametros if filtrar else None)
    context = {"form": form, "filtrado": False}
    status = 200
    if filtrar:
        if form.is_valid():
            context.update(contexto_resultados(form))
        else:
            status = 400
    return render(request, "horarios/exportar.html", context, status=status)


@acceso_exportacion
@require_GET
def descargar_excel(request):
    form = ExportacionPlanificacionForm(request.GET)
    if not form.is_valid():
        return render(request, "horarios/exportar.html", {"form": form, "filtrado": False}, status=400)
    libro = crear_workbook(form.cleaned_data)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo(form.cleaned_data)}"'
    libro.save(response)
    libro.close()
    return response


@acceso_exportacion
@require_GET
def semestres_exportacion(request):
    # El mismo formulario valida primero la dependencia académica Centro/Facultad/Programa.
    form = ExportacionPlanificacionForm(request.GET)
    if not form.is_valid() or not all(form.cleaned_data.get(c) for c in ("centro", "facultad", "programa")):
        return JsonResponse([], safe=False)
    d = form.cleaned_data
    semestres = semestres_del_programa(d["centro"], d["programa"], d["periodo"])
    return JsonResponse([{"id": s.pk, "nombre": s.get_numero_display()} for s in semestres], safe=False)
