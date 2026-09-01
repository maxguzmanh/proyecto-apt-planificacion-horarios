from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from academico.models import (
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

from .forms import HorarioForm
from .models import Grupo, Horario, OfertaGrupo

# ==========================================================
# CONFIGURACIÓN DEL CALENDARIO
# ==========================================================

HORA_INICIO_CALENDARIO = 6
HORA_FIN_CALENDARIO = 22
PIXELES_POR_MINUTO = 0.75


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================


def agregar_errores_formulario(form, error):
    if hasattr(error, "message_dict"):
        for campo, errores in error.message_dict.items():
            campo_formulario = campo if campo in form.fields else None

            for mensaje in errores:
                form.add_error(campo_formulario, mensaje)
    else:
        form.add_error(None, error)


# ==========================================================
# PANTALLA DE INICIO
# ==========================================================


@login_required
def inicio(request):

    context = {
        "centros": CentroTutorial.objects.filter(activo=True).order_by("nombre"),
        "total_programas": ProgramaAcademico.objects.filter(activo=True).count(),
        "total_profesores": Profesor.objects.filter(activo=True).count(),
        "total_aulas": Aula.objects.filter(activo=True).count(),
        "total_horarios": Horario.objects.filter(activo=True).count(),
    }

    return render(
        request,
        "horarios/inicio.html",
        context,
    )


# ==========================================================
# PLANIFICACIÓN / CALENDARIO SEMANAL
# ==========================================================


@login_required
@permission_required(
    "horarios.view_horario",
    raise_exception=True,
)
def planificacion(request):
    centro_id = request.GET.get("centro")
    sede_id = request.GET.get("sede")
    facultad_id = request.GET.get("facultad")
    programa_id = request.GET.get("programa") or request.GET.get("carrera")
    periodo_id = request.GET.get("periodo")
    semestre_id = request.GET.get("semestre")

    if not all(
        [
            centro_id,
            sede_id,
            facultad_id,
            programa_id,
            periodo_id,
            semestre_id,
        ]
    ):
        return redirect("inicio")

    centro = get_object_or_404(
        CentroTutorial,
        pk=centro_id,
        activo=True,
    )

    sede = get_object_or_404(
        Sede,
        pk=sede_id,
        centro_tutorial=centro,
        activo=True,
    )

    facultad = get_object_or_404(
        Facultad,
        pk=facultad_id,
        activo=True,
    )

    programa = get_object_or_404(
        ProgramaAcademico,
        pk=programa_id,
        facultad=facultad,
        activo=True,
    )

    get_object_or_404(
        ProgramaCentroTutorial,
        programa=programa,
        centro_tutorial=centro,
        activo=True,
    )

    periodo = get_object_or_404(
        PeriodoAcademico,
        pk=periodo_id,
    )

    semestre = get_object_or_404(
        Semestre,
        pk=semestre_id,
    )

    horarios = list(
        Horario.objects.filter(
            activo=True,
            oferta__activo=True,
            oferta__periodo=periodo,
            oferta__grupos__centro_tutorial=centro,
            oferta__grupos__programa=programa,
            oferta__grupos__semestre=semestre,
            aula__sede=sede,
        )
        .select_related(
            "oferta",
            "oferta__asignatura",
            "oferta__profesor",
            "oferta__periodo",
            "oferta__modalidad",
            "aula",
            "aula__sede",
        )
        .prefetch_related("oferta__grupos")
        .distinct()
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
        ("DO", "Domingo"),
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
        "programa": programa,
        # Alias temporal para que los templates antiguos no fallen
        # mientras reemplazamos Carrera por Programa Académico.
        "carrera": programa,
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


# ==========================================================
# SELECTS DEPENDIENTES - AJAX
# ==========================================================


@login_required
def cargar_sedes(request):
    centro_id = request.GET.get("centro")

    sedes = Sede.objects.filter(
        centro_tutorial_id=centro_id,
        activo=True,
    ).values(
        "id",
        "nombre",
    )

    return JsonResponse(
        list(sedes),
        safe=False,
    )


@login_required
def cargar_facultades(request):
    centro_id = request.GET.get("centro")
    sede_id = request.GET.get("sede")

    if not centro_id and sede_id:
        centro_id = (
            Sede.objects.filter(pk=sede_id)
            .values_list("centro_tutorial_id", flat=True)
            .first()
        )

    if not centro_id:
        return JsonResponse([], safe=False)

    facultades = (
        Facultad.objects.filter(
            activo=True,
            programas_academicos__activo=True,
            programas_academicos__centros_tutoriales__centro_tutorial_id=centro_id,
            programas_academicos__centros_tutoriales__activo=True,
        )
        .distinct()
        .values(
            "id",
            "nombre",
        )
    )

    return JsonResponse(
        list(facultades),
        safe=False,
    )


@login_required
def cargar_programas(request):
    facultad_id = request.GET.get("facultad")
    centro_id = request.GET.get("centro")
    sede_id = request.GET.get("sede")

    if not centro_id and sede_id:
        centro_id = (
            Sede.objects.filter(pk=sede_id)
            .values_list("centro_tutorial_id", flat=True)
            .first()
        )

    programas = ProgramaAcademico.objects.filter(
        facultad_id=facultad_id,
        activo=True,
    )

    if centro_id:
        programas = programas.filter(
            centros_tutoriales__centro_tutorial_id=centro_id,
            centros_tutoriales__activo=True,
        )

    programas = programas.distinct().values(
        "id",
        "nombre",
    )

    return JsonResponse(
        list(programas),
        safe=False,
    )


@login_required
def cargar_periodos(request):

    centro_id = request.GET.get("centro")
    programa_id = request.GET.get("programa")

    periodos = PeriodoAcademico.objects.filter(
        activo=True,
    )

    if centro_id and programa_id:

        periodos = periodos.filter(
            grupos__centro_tutorial_id=centro_id,
            grupos__programa_id=programa_id,
            grupos__activo=True,
        )

    periodos = (
        periodos.distinct()
        .order_by("-codigo")
        .values(
            "id",
            "nombre",
        )
    )

    return JsonResponse(
        list(periodos),
        safe=False,
    )


@login_required
def cargar_semestres(request):

    centro_id = request.GET.get("centro")
    programa_id = request.GET.get("programa")
    periodo_id = request.GET.get("periodo")

    semestres = Semestre.objects.all()

    if centro_id and programa_id and periodo_id:

        semestres = semestres.filter(
            grupos__centro_tutorial_id=centro_id,
            grupos__programa_id=programa_id,
            grupos__periodo_id=periodo_id,
            grupos__activo=True,
        )

    elif programa_id:

        semestres = semestres.filter(
            planes_estudio__programa_id=programa_id,
            planes_estudio__activo=True,
        )

    semestres = semestres.distinct().order_by("numero")

    datos = [
        {
            "id": semestre.id,
            "numero": semestre.numero,
            "nombre": semestre.get_numero_display(),
        }
        for semestre in semestres
    ]

    return JsonResponse(
        datos,
        safe=False,
    )


@login_required
def cargar_grupos(request):
    centro_id = request.GET.get("centro")
    programa_id = request.GET.get("programa") or request.GET.get("carrera")
    periodo_id = request.GET.get("periodo")
    semestre_id = request.GET.get("semestre")

    grupos = Grupo.objects.filter(activo=True)

    if centro_id:
        grupos = grupos.filter(centro_tutorial_id=centro_id)

    if programa_id:
        grupos = grupos.filter(programa_id=programa_id)

    if periodo_id:
        grupos = grupos.filter(periodo_id=periodo_id)

    if semestre_id:
        grupos = grupos.filter(semestre_id=semestre_id)

    grupos = grupos.values(
        "id",
        "codigo",
    )

    return JsonResponse(
        list(grupos),
        safe=False,
    )


# ==========================================================
# NUEVA ASIGNACIÓN
# ==========================================================


@login_required
@permission_required(
    "horarios.add_horario",
    raise_exception=True,
)
def nueva_asignacion(request):
    periodo_id = request.GET.get("periodo") or request.POST.get("periodo")
    semestre_id = request.GET.get("semestre") or request.POST.get("semestre")
    sede_id = request.GET.get("sede") or request.POST.get("sede")
    programa_id = (
        request.GET.get("programa")
        or request.GET.get("carrera")
        or request.POST.get("programa")
        or request.POST.get("carrera")
    )

    if not all(
        [
            periodo_id,
            semestre_id,
            sede_id,
            programa_id,
        ]
    ):
        messages.error(
            request,
            "Falta información académica para crear la asignación.",
        )
        return redirect("inicio")

    periodo = get_object_or_404(
        PeriodoAcademico,
        pk=periodo_id,
    )

    semestre = get_object_or_404(
        Semestre,
        pk=semestre_id,
    )

    sede = get_object_or_404(
        Sede,
        pk=sede_id,
        activo=True,
    )

    programa = get_object_or_404(
        ProgramaAcademico,
        pk=programa_id,
        activo=True,
    )

    centro = sede.centro_tutorial

    get_object_or_404(
        ProgramaCentroTutorial,
        programa=programa,
        centro_tutorial=centro,
        activo=True,
    )

    volver_a = (
        request.POST.get("volver_a")
        or request.GET.get("volver_a")
        or request.META.get("HTTP_REFERER")
        or "/"
    )

    if request.method == "POST":
        form = HorarioForm(
            request.POST,
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            sede=sede,
            periodo=periodo,
        )

        if form.is_valid():
            horario = form.save(commit=False)

            try:
                horario.full_clean()
            except ValidationError as error:
                agregar_errores_formulario(form, error)
            else:
                horario.save()

                messages.success(
                    request,
                    "Horario creado correctamente.",
                )

                return redirect(volver_a)
    else:
        form = HorarioForm(
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            sede=sede,
            periodo=periodo,
        )

    context = {
        "form": form,
        "periodo": periodo,
        "semestre": semestre,
        "sede": sede,
        "programa": programa,
        "carrera": programa,
        "centro": centro,
        "volver_a": volver_a,
    }

    return render(
        request,
        "horarios/nueva_asignacion.html",
        context,
    )


# ==========================================================
# EDITAR ASIGNACIÓN
# ==========================================================


@login_required
@permission_required(
    "horarios.change_horario",
    raise_exception=True,
)
def editar_asignacion(request, horario_id):
    horario = get_object_or_404(
        Horario.objects.select_related(
            "oferta",
            "oferta__periodo",
            "aula",
            "aula__sede",
            "aula__sede__centro_tutorial",
        ).prefetch_related("oferta__grupos"),
        pk=horario_id,
    )

    grupo_referencia = horario.oferta.grupos.first()

    if not grupo_referencia:
        messages.error(
            request,
            "La oferta académica no tiene grupos asociados.",
        )
        return redirect("inicio")

    periodo = horario.oferta.periodo
    semestre = grupo_referencia.semestre
    programa = grupo_referencia.programa
    centro = grupo_referencia.centro_tutorial
    sede = horario.aula.sede

    volver_a = request.POST.get("volver_a") or request.GET.get("volver_a") or "/"

    if request.method == "POST":
        form = HorarioForm(
            request.POST,
            instance=horario,
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            sede=sede,
            periodo=periodo,
        )

        if form.is_valid():
            horario_editado = form.save(commit=False)

            try:
                horario_editado.full_clean()
            except ValidationError as error:
                agregar_errores_formulario(form, error)
            else:
                horario_editado.save()

                messages.success(
                    request,
                    "Horario actualizado correctamente.",
                )

                return redirect(volver_a)
    else:
        form = HorarioForm(
            instance=horario,
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            sede=sede,
            periodo=periodo,
        )

    context = {
        "form": form,
        "horario": horario,
        "periodo": periodo,
        "semestre": semestre,
        "sede": sede,
        "programa": programa,
        "carrera": programa,
        "centro": centro,
        "volver_a": volver_a,
    }

    return render(
        request,
        "horarios/editar_asignacion.html",
        context,
    )


# ==========================================================
# ELIMINAR ASIGNACIÓN
# ==========================================================


@login_required
@permission_required(
    "horarios.delete_horario",
    raise_exception=True,
)
def eliminar_asignacion(request, horario_id):
    horario = get_object_or_404(
        Horario,
        pk=horario_id,
    )

    volver_a = request.POST.get("volver_a") or request.GET.get("volver_a") or "/"

    if request.method == "POST":
        horario.delete()

        messages.success(
            request,
            "Horario eliminado correctamente.",
        )

        return redirect(volver_a)

    context = {
        "horario": horario,
        "volver_a": volver_a,
    }

    return render(
        request,
        "horarios/eliminar_asignacion.html",
        context,
    )


# ==========================================================
# EXPORTAR PROGRAMACIÓN A EXCEL
# ESTRUCTURA BASADA EN EL ARCHIVO REAL DE LA UNIVERSIDAD
# ==========================================================


@login_required
@permission_required(
    "horarios.view_horario",
    raise_exception=True,
)
def exportar_excel(request):
    centro_id = request.GET.get("centro")
    sede_id = request.GET.get("sede")
    facultad_id = request.GET.get("facultad")
    programa_id = request.GET.get("programa") or request.GET.get("carrera")
    periodo_id = request.GET.get("periodo")
    semestre_id = request.GET.get("semestre")
    asignatura_id = request.GET.get("asignatura")
    profesor_id = request.GET.get("profesor")
    modalidad_id = request.GET.get("modalidad")
    grupo_id = request.GET.get("grupo")
    aula_id = request.GET.get("aula")
    area_id = request.GET.get("area")
    dia = request.GET.get("dia")

    horarios_exportacion = Horario.objects.filter(
        activo=True,
    ).select_related(
        "aula",
        "aula__sede",
    )

    if sede_id:
        horarios_exportacion = horarios_exportacion.filter(aula__sede_id=sede_id)

    if aula_id:
        horarios_exportacion = horarios_exportacion.filter(aula_id=aula_id)

    if dia:
        horarios_exportacion = horarios_exportacion.filter(dia=dia)

    ofertas_grupo = OfertaGrupo.objects.filter(
        oferta__activo=True,
        grupo__activo=True,
        oferta__horarios__activo=True,
    )

    if centro_id:
        ofertas_grupo = ofertas_grupo.filter(grupo__centro_tutorial_id=centro_id)

    if facultad_id:
        ofertas_grupo = ofertas_grupo.filter(grupo__programa__facultad_id=facultad_id)

    if programa_id:
        ofertas_grupo = ofertas_grupo.filter(grupo__programa_id=programa_id)

    if periodo_id:
        ofertas_grupo = ofertas_grupo.filter(
            oferta__periodo_id=periodo_id,
            grupo__periodo_id=periodo_id,
        )

    if semestre_id:
        ofertas_grupo = ofertas_grupo.filter(grupo__semestre_id=semestre_id)

    if asignatura_id:
        ofertas_grupo = ofertas_grupo.filter(oferta__asignatura_id=asignatura_id)

    if profesor_id:
        ofertas_grupo = ofertas_grupo.filter(oferta__profesor_id=profesor_id)

    if modalidad_id:
        ofertas_grupo = ofertas_grupo.filter(oferta__modalidad_id=modalidad_id)

    if grupo_id:
        ofertas_grupo = ofertas_grupo.filter(grupo_id=grupo_id)

    if sede_id:
        ofertas_grupo = ofertas_grupo.filter(oferta__horarios__aula__sede_id=sede_id)

    if aula_id:
        ofertas_grupo = ofertas_grupo.filter(oferta__horarios__aula_id=aula_id)

    if dia:
        ofertas_grupo = ofertas_grupo.filter(oferta__horarios__dia=dia)

    ofertas_grupo = (
        ofertas_grupo.select_related(
            "oferta",
            "oferta__asignatura",
            "oferta__profesor",
            "oferta__periodo",
            "oferta__modalidad",
            "grupo",
            "grupo__centro_tutorial",
            "grupo__programa",
            "grupo__programa__facultad",
            "grupo__semestre",
        )
        .prefetch_related(
            Prefetch(
                "oferta__horarios",
                queryset=horarios_exportacion,
                to_attr="horarios_exportacion",
            )
        )
        .distinct()
        .order_by(
            "grupo__centro_tutorial__nombre",
            "grupo__programa__nombre",
            "grupo__semestre__numero",
            "oferta__asignatura__nombre",
            "grupo__codigo",
        )
    )

    planes = PlanEstudioAsignatura.objects.filter(
        activo=True,
    ).select_related(
        "area_academica",
    )

    if programa_id:
        planes = planes.filter(programa_id=programa_id)

    if semestre_id:
        planes = planes.filter(semestre_id=semestre_id)

    if asignatura_id:
        planes = planes.filter(asignatura_id=asignatura_id)

    mapa_planes = {
        (
            plan.programa_id,
            plan.asignatura_id,
            plan.semestre_id,
        ): plan
        for plan in planes
    }

    workbook = Workbook()
    hoja = workbook.active
    hoja.title = "PROGRAMACIÓN"

    encabezados = [
        "Lugar de Desarrollo y/o Centro Tutorial",
        "Facultad",
        "Modalidad",
        "Programa Académico",
        "SEM",
        "Asignatura",
        "Grupo",
        "Cupos",
        "# Créditos",
        "Profesor",
        "Día",
        "Hora inicio",
        "Hora final",
        "Aula",
        "Sede",
        "Área Académica",
    ]

    for columna, encabezado in enumerate(encabezados, start=1):
        celda = hoja.cell(
            row=1,
            column=columna,
            value=encabezado,
        )

        celda.font = Font(
            bold=True,
            color="FFFFFF",
        )

        celda.fill = PatternFill(
            fill_type="solid",
            fgColor="212529",
        )

        celda.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    fila_actual = 2

    for oferta_grupo in ofertas_grupo:
        oferta = oferta_grupo.oferta
        grupo = oferta_grupo.grupo

        plan = mapa_planes.get(
            (
                grupo.programa_id,
                oferta.asignatura_id,
                grupo.semestre_id,
            )
        )

        if area_id:
            if not plan or str(plan.area_academica_id) != str(area_id):
                continue

        for horario in oferta.horarios_exportacion:
            valores = [
                grupo.centro_tutorial.nombre,
                grupo.programa.facultad.nombre,
                oferta.modalidad.nombre,
                grupo.programa.nombre,
                grupo.semestre.get_numero_display(),
                oferta.asignatura.nombre,
                grupo.codigo,
                oferta_grupo.cupos,
                plan.creditos if plan else "",
                str(oferta.profesor),
                horario.get_dia_display(),
                horario.hora_inicio.strftime("%H:%M"),
                horario.hora_fin.strftime("%H:%M"),
                horario.aula.nombre,
                horario.aula.sede.nombre,
                (plan.area_academica.nombre if plan and plan.area_academica else ""),
            ]

            for columna, valor in enumerate(valores, start=1):
                hoja.cell(
                    row=fila_actual,
                    column=columna,
                    value=valor,
                )

            fila_actual += 1

    anchos = {
        "A": 35,
        "B": 25,
        "C": 18,
        "D": 32,
        "E": 10,
        "F": 38,
        "G": 18,
        "H": 10,
        "I": 12,
        "J": 30,
        "K": 15,
        "L": 14,
        "M": 14,
        "N": 18,
        "O": 25,
        "P": 25,
    }

    for columna, ancho in anchos.items():
        hoja.column_dimensions[columna].width = ancho

    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = f"A1:P{max(1, fila_actual - 1)}"

    nombre_archivo = "programacion_horarios.xlsx"

    response = HttpResponse(
        content_type=(
            "application/" "vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'

    workbook.save(response)

    return response
