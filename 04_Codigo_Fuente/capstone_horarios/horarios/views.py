from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse

from academico.models import (
    CentroTutorial,
    Sede,
    Facultad,
    Carrera,
    PeriodoAcademico,
    Semestre,
)

from .models import Horario


def inicio(request):
    context = {
        "centros": CentroTutorial.objects.all(),
    }

    return render(
        request,
        "horarios/inicio.html",
        context,
    )

    return render(
        request,
        "horarios/inicio.html",
        context,
    )


def planificacion(request):

    centro_id = request.GET.get("centro")
    sede_id = request.GET.get("sede")
    facultad_id = request.GET.get("facultad")
    carrera_id = request.GET.get("carrera")
    periodo_id = request.GET.get("periodo")
    semestre_id = request.GET.get("semestre")

    centro = get_object_or_404(
        CentroTutorial,
        pk=centro_id,
    )

    sede = get_object_or_404(
        Sede,
        pk=sede_id,
        centro_tutorial=centro,
    )

    facultad = get_object_or_404(
        Facultad,
        pk=facultad_id,
        sede=sede,
    )

    carrera = get_object_or_404(
        Carrera,
        pk=carrera_id,
        facultad=facultad,
    )

    periodo = get_object_or_404(
        PeriodoAcademico,
        pk=periodo_id,
    )

    semestre = get_object_or_404(
        Semestre,
        pk=semestre_id,
        carrera=carrera,
        periodo=periodo,
    )

    horarios = (
        Horario.objects.filter(
            periodo=periodo,
            asignatura__semestre=semestre,
        )
        .select_related(
            "asignatura",
            "profesor",
            "aula",
        )
        .order_by(
            "dia",
            "hora_inicio",
        )
    )

    context = {
        "centro": centro,
        "sede": sede,
        "facultad": facultad,
        "carrera": carrera,
        "periodo": periodo,
        "semestre": semestre,
        "horarios": horarios,
    }

    return render(
        request,
        "horarios/planificacion.html",
        context,
    )


def cargar_sedes(request):
    centro_id = request.GET.get("centro")

    sedes = Sede.objects.filter(centro_tutorial_id=centro_id).values(
        "id",
        "nombre",
    )

    return JsonResponse(
        list(sedes),
        safe=False,
    )


def cargar_facultades(request):
    sede_id = request.GET.get("sede")

    facultades = Facultad.objects.filter(sede_id=sede_id).values(
        "id",
        "nombre",
    )

    return JsonResponse(
        list(facultades),
        safe=False,
    )


def cargar_carreras(request):
    facultad_id = request.GET.get("facultad")

    carreras = Carrera.objects.filter(facultad_id=facultad_id).values(
        "id",
        "nombre",
    )

    return JsonResponse(
        list(carreras),
        safe=False,
    )


def cargar_periodos(request):
    carrera_id = request.GET.get("carrera")

    periodos = (
        PeriodoAcademico.objects.filter(semestres__carrera_id=carrera_id)
        .distinct()
        .values(
            "id",
            "nombre",
        )
    )

    return JsonResponse(
        list(periodos),
        safe=False,
    )


def cargar_semestres(request):
    carrera_id = request.GET.get("carrera")
    periodo_id = request.GET.get("periodo")

    semestres = Semestre.objects.filter(
        carrera_id=carrera_id,
        periodo_id=periodo_id,
    ).values(
        "id",
        "numero",
    )

    return JsonResponse(
        list(semestres),
        safe=False,
    )
