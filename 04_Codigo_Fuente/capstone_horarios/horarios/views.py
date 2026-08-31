from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.core.exceptions import ValidationError

from .forms import HorarioForm

from academico.models import (
    CentroTutorial,
    Sede,
    Facultad,
    Carrera,
    PeriodoAcademico,
    Semestre,
)

from .models import Horario

HORA_INICIO_CALENDARIO = 6
HORA_FIN_CALENDARIO = 22
PIXELES_POR_MINUTO = 0.75


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

    horarios = list(
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

    dias = [
        ("LU", "Lunes"),
        ("MA", "Martes"),
        ("MI", "Miércoles"),
        ("JU", "Jueves"),
        ("VI", "Viernes"),
        ("SA", "Sábado"),
    ]

    inicio_calendario = HORA_INICIO_CALENDARIO * 60
    fin_calendario = HORA_FIN_CALENDARIO * 60

    altura_calendario = int((fin_calendario - inicio_calendario) * PIXELES_POR_MINUTO)

    horas_calendario = []

    for hora in range(
        HORA_INICIO_CALENDARIO,
        HORA_FIN_CALENDARIO,
    ):
        minutos = hora * 60

        top = int((minutos - inicio_calendario) * PIXELES_POR_MINUTO)

        horas_calendario.append(
            {
                "texto": f"{hora:02d}:00",
                "top": top,
            }
        )

    dias_calendario = []

    for codigo, nombre in dias:

        bloques = []

        for horario in horarios:

            if horario.dia != codigo:
                continue

            inicio = horario.hora_inicio.hour * 60 + horario.hora_inicio.minute

            fin = horario.hora_fin.hour * 60 + horario.hora_fin.minute

            # Solo mostramos horarios dentro del rango visible.
            if fin <= inicio_calendario or inicio >= fin_calendario:
                continue

            inicio_visible = max(
                inicio,
                inicio_calendario,
            )

            fin_visible = min(
                fin,
                fin_calendario,
            )

            top = int((inicio_visible - inicio_calendario) * PIXELES_POR_MINUTO)

            altura = max(
                int((fin_visible - inicio_visible) * PIXELES_POR_MINUTO),
                30,
            )

            bloques.append(
                {
                    "horario": horario,
                    "top": top,
                    "altura": altura,
                }
            )

        dias_calendario.append(
            {
                "codigo": codigo,
                "nombre": nombre,
                "horarios": bloques,
            }
        )

    context = {
        "centro": centro,
        "sede": sede,
        "facultad": facultad,
        "carrera": carrera,
        "periodo": periodo,
        "semestre": semestre,
        "dias_calendario": dias_calendario,
        "horas_calendario": horas_calendario,
        "altura_calendario": altura_calendario,
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


def nueva_asignacion(request):

    periodo_id = request.GET.get("periodo")
    semestre_id = request.GET.get("semestre")
    sede_id = request.GET.get("sede")

    periodo = get_object_or_404(
        PeriodoAcademico,
        pk=periodo_id,
    )

    semestre = get_object_or_404(
        Semestre,
        pk=semestre_id,
        periodo=periodo,
    )

    sede = get_object_or_404(
        Sede,
        pk=sede_id,
    )

    if request.method == "POST":

        form = HorarioForm(
            request.POST,
            semestre=semestre,
            sede=sede,
            periodo=periodo,
        )

        if form.is_valid():

            horario = form.save(commit=False)

            # El periodo no viene en el formulario,
            # por eso lo asignamos manualmente.
            horario.periodo = periodo

            try:
                # IMPORTANTE:
                # ejecutamos nuevamente todas las validaciones
                # del modelo con el periodo ya asignado.
                horario.full_clean()

            except ValidationError as error:

                # Si clean() devolvió errores asociados
                # a campos específicos.
                if hasattr(error, "message_dict"):

                    for campo, errores in error.message_dict.items():

                        if campo in form.fields:
                            campo_formulario = campo
                        else:
                            campo_formulario = None

                        for mensaje in errores:
                            form.add_error(
                                campo_formulario,
                                mensaje,
                            )

                else:

                    form.add_error(
                        None,
                        error,
                    )

            else:

                # Solo se guarda si full_clean()
                # terminó sin ningún conflicto.
                horario.save()

                return redirect(
                    request.POST.get(
                        "volver_a",
                        "/",
                    )
                )

    else:

        form = HorarioForm(
            semestre=semestre,
            sede=sede,
            periodo=periodo,
        )

    context = {
        "form": form,
        "periodo": periodo,
        "semestre": semestre,
        "sede": sede,
        "volver_a": request.META.get(
            "HTTP_REFERER",
            "/",
        ),
    }

    return render(
        request,
        "horarios/nueva_asignacion.html",
        context,
    )
