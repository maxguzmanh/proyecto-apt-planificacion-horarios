import json
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from academico.choices import DiaSemana

from academico.models import (
    Asignatura,
    DisponibilidadProfesor,
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

from .services import (obtener_panel_academico, obtener_resumen_docente,
    calcular_horas_planificadas, obtener_carga_activa, calcular_horas_pendientes, operacion_planificacion)
from .forms import HorarioForm, NuevaAsignacionForm, MoverHorarioForm, CrearHorarioOfertaForm, AsignarAulaHorarioForm
from .presentacion import respuesta_error
from .calendario import sedes_de_modalidad, SEMANA_REFERENCIA, horarios_del_contexto, resolver_contexto_calendario, serializar_evento, oferta_del_contexto, aulas_del_contexto, ofertas_de_programa
from .models import (
    Grupo,
    Horario,
    OfertaAcademica,
    OfertaGrupo,
)

# ==========================================================
# CONFIGURACIÓN DEL CALENDARIO
# ==========================================================



# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================


def agregar_errores_formulario(form, error, candidato=None):
    """
    Agrega los errores de validación del modelo como
    errores generales del formulario.

    De esta forma los conflictos de profesor, aula,
    grupo, etc. se muestran con el mismo estilo visual
    en la parte superior del formulario.
    """

    if hasattr(error, "message_dict"):

        for errores in respuesta_error(error, candidato)["errors"].values():

            for mensaje in errores:

                form.add_error(
                    None,
                    mensaje,
                )

    else:

        mensajes = getattr(
            error,
            "messages",
            [str(error)],
        )

        for mensaje in mensajes:

            form.add_error(
                None,
                mensaje,
            )


# ==========================================================
# PANTALLA DE INICIO
# ==========================================================


@login_required
def inicio(request):
    if not request.user.has_perm("horarios.view_horario") or not any(request.user.has_perm(f"horarios.{accion}_horario") for accion in ("add","change","delete")):
        raise PermissionDenied
    from .dashboard import resumen_dashboard
    periodos=list(PeriodoAcademico.objects.filter(activo=True).order_by("-fecha_inicio","-pk"))
    periodo_id=request.GET.get("periodo")
    if periodo_id:
        periodo=next((p for p in periodos if str(p.pk)==periodo_id),None)
        if periodo is None: raise Http404("Periodo académico no disponible.")
    else: periodo=periodos[0] if periodos else None
    context=resumen_dashboard(periodo)
    acciones=[("Ir a Planificación","planificacion","horarios.view_horario"),("Profesores","profesores","academico.view_profesor"),("Aulas","aulas","academico.view_aula"),("Programas Académicos","programas_academicos","academico.view_programaacademico"),("Disponibilidad Docente","disponibilidades_profesores","academico.view_disponibilidadprofesor"),("Carga Docente","cargas_docentes","academico.view_cargadocente")]
    context.update(periodos=periodos,periodo=periodo,acciones=[{"nombre":n,"ruta":r} for n,r,p in acciones if request.user.has_perm(p)])
    return render(request,"horarios/inicio.html",context)


# ==========================================================
# PLANIFICACIÓN / CALENDARIO SEMANAL
# ==========================================================


@login_required
@permission_required(
    "horarios.view_horario",
    raise_exception=True,
)
def planificacion(request):

    # ======================================================
    # FILTROS
    # ======================================================

    centro_id = request.GET.get("centro", "").strip()
    sede_id = request.GET.get("sede", "").strip()
    facultad_id = request.GET.get("facultad", "").strip()
    programa_id = request.GET.get("programa", "").strip()
    periodo_id = request.GET.get("periodo", "").strip()
    semestre_id = request.GET.get("semestre", "").strip()
    modalidad_id = request.GET.get("modalidad", "").strip()

    # ======================================================
    # FILTROS OBLIGATORIOS
    #
    # Modalidad y Sede forman parte del contexto obligatorio.
    # ======================================================

    filtros_completos = all(
        [
            centro_id,
            facultad_id,
            programa_id,
            modalidad_id,
            sede_id,
            periodo_id,
            semestre_id,
        ]
    )

    # ======================================================
    # OBJETOS SELECCIONADOS
    # ======================================================

    centro = None
    sede = None
    facultad = None
    programa = None
    periodo = None
    semestre = None
    modalidad = None

    horarios = []

    # ======================================================
    # CARGAR PLANIFICACIÓN
    # ======================================================

    if filtros_completos:
        try:
            contexto = resolver_contexto_calendario(request.GET)
        except ValidationError as error:
            raise Http404("Filtros de planificación inválidos.") from error
        centro, facultad, programa = contexto["centro"], contexto["facultad"], contexto["programa"]
        periodo, semestre = contexto["periodo"], contexto["semestre"]
        sede, modalidad = contexto["sede"], contexto["modalidad"]
        horarios = list(horarios_del_contexto(**contexto))

    asignaturas_semestre = []
    if filtros_completos:
        asignaturas_semestre = obtener_panel_academico(
            programa, semestre, centro, periodo, sede=sede, modalidad=modalidad,
        )

    context = {
        "asignaturas_semestre": asignaturas_semestre,
        # Datos iniciales
        "centros": (CentroTutorial.objects.filter(activo=True).order_by("nombre")),
        # Objetos seleccionados
        "centro": centro,
        "sede": sede,
        "facultad": facultad,
        "programa": programa,
        "periodo": periodo,
        "semestre": semestre,
        "modalidad": modalidad,
        # IDs seleccionados
        "centro_id": centro_id,
        "sede_id": sede_id,
        "facultad_id": facultad_id,
        "programa_id": programa_id,
        "periodo_id": periodo_id,
        "semestre_id": semestre_id,
        "modalidad_id": modalidad_id,
        # Estado
        "filtros_completos": filtros_completos,
        "hay_horarios": bool(horarios),
        # Calendario
        "semana_referencia": SEMANA_REFERENCIA.isoformat(),
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
    if not centro_id or not centro_id.isdigit():
        return JsonResponse([], safe=False)
    modalidad = None
    modalidad_id = request.GET.get("modalidad")
    if modalidad_id:
        if not modalidad_id.isdigit(): return JsonResponse([], safe=False)
        modalidad = Modalidad.objects.filter(pk=modalidad_id, activo=True).first()
        if modalidad is None: return JsonResponse([], safe=False)
    sedes = sedes_de_modalidad(centro_id, modalidad).order_by("nombre").values("id", "nombre", "codigo")
    return JsonResponse(list(sedes), safe=False)


@login_required
def cargar_modalidades(request):
    centro_id, programa_id = request.GET.get("centro", ""), request.GET.get("programa", "")
    if not centro_id.isdigit() or not programa_id.isdigit():
        return JsonResponse([], safe=False)
    ofertas = ofertas_de_programa(centro_id, programa_id)
    modalidades = Modalidad.objects.filter(activo=True, pk__in=ofertas.values("modalidad_id")).order_by("nombre").values("id", "nombre", "codigo")
    return JsonResponse(list(modalidades), safe=False)


@login_required
def cargar_aulas(request):

    sede_id = request.GET.get("sede")

    if not sede_id:

        return JsonResponse(
            [],
            safe=False,
        )

    aulas = (
        Aula.objects.filter(
            sede_id=sede_id,
            activo=True,
        )
        .order_by(
            "nombre",
        )
        .values(
            "id",
            "nombre",
            "capacidad",
            "tipo",
        )
    )

    return JsonResponse(
        list(aulas),
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


def ofertas_para_selects(request):
    valores = {campo: request.GET.get(campo, "") for campo in ["centro", "programa", "modalidad", "sede"]}
    if not all(valor.isdigit() and int(valor) > 0 for valor in valores.values()):
        return OfertaAcademica.objects.none()
    if not Sede.objects.filter(pk=valores["sede"], centro_tutorial_id=valores["centro"], activo=True).exists():
        return OfertaAcademica.objects.none()
    return ofertas_de_programa(valores["centro"], valores["programa"]).filter(modalidad_id=valores["modalidad"])


@login_required
def cargar_periodos(request):
    ofertas = ofertas_para_selects(request)
    periodos = PeriodoAcademico.objects.filter(activo=True, pk__in=ofertas.values("periodo_id")).order_by("-codigo").values("id", "nombre")
    return JsonResponse(list(periodos), safe=False)


@login_required
def cargar_semestres(request):
    periodo_id = request.GET.get("periodo", "")
    ofertas = ofertas_para_selects(request)
    if not periodo_id.isdigit() or not ofertas.filter(periodo_id=periodo_id).exists():
        return JsonResponse([], safe=False)
    semestres = Semestre.objects.filter(
        grupos__centro_tutorial_id=request.GET["centro"], grupos__programa_id=request.GET["programa"],
        grupos__periodo_id=periodo_id, grupos__activo=True,
    ).distinct().order_by("numero")
    return JsonResponse([{"id": s.pk, "numero": s.numero, "nombre": s.get_numero_display()} for s in semestres], safe=False)


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

    # ======================================================
    # CONTEXTO ACADÉMICO
    # ======================================================

    centro_id = request.GET.get("centro") or request.POST.get("centro")

    periodo_id = request.GET.get("periodo") or request.POST.get("periodo")

    semestre_id = request.GET.get("semestre") or request.POST.get("semestre")

    programa_id = request.GET.get("programa") or request.POST.get("programa")

    sede_id = request.GET.get("sede") or request.POST.get("sede")

    # ------------------------------------------------------
    # Centro, Programa, Periodo y Semestre son necesarios.
    #
    # Sede es opcional porque ahora puede seleccionarse
    # directamente dentro del formulario.
    # ------------------------------------------------------

    if not all(
        [
            centro_id,
            programa_id,
            periodo_id,
            semestre_id,
        ]
    ):

        messages.error(
            request,
            ("Falta información académica para " "crear la asignación."),
        )

        return redirect("planificacion")

    # ======================================================
    # OBTENER CONTEXTO
    # ======================================================

    centro = get_object_or_404(
        CentroTutorial,
        pk=centro_id,
        activo=True,
    )

    programa = get_object_or_404(
        ProgramaAcademico,
        pk=programa_id,
        activo=True,
    )

    periodo = get_object_or_404(
        PeriodoAcademico,
        pk=periodo_id,
        activo=True,
    )

    semestre = get_object_or_404(
        Semestre,
        pk=semestre_id,
    )

    # ------------------------------------------------------
    # Verificar que el programa esté disponible
    # en el Centro Tutorial.
    # ------------------------------------------------------

    get_object_or_404(
        ProgramaCentroTutorial,
        programa=programa,
        centro_tutorial=centro,
        activo=True,
    )

    # ======================================================
    # SEDE INICIAL OPCIONAL
    # ======================================================

    sede_inicial = None

    if sede_id:

        sede_inicial = get_object_or_404(
            Sede,
            pk=sede_id,
            centro_tutorial=centro,
            activo=True,
        )

    # ======================================================
    # URL DE RETORNO
    # ======================================================

    volver_a = (
        request.POST.get("volver_a")
        or request.GET.get("volver_a")
        or request.META.get("HTTP_REFERER")
        or "/"
    )

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        form = NuevaAsignacionForm(
            request.POST,
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            periodo=periodo,
            sede_inicial=sede_inicial,
        )

        if form.is_valid():

            asignatura = form.cleaned_data["asignatura"]

            profesor = form.cleaned_data["profesor"]

            modalidad = form.cleaned_data["modalidad"]

            grupos = form.cleaned_data["grupos"]

            cupos = form.cleaned_data["cupos"]

            aula = form.cleaned_data["aula"]

            dia = form.cleaned_data["dia"]

            hora_inicio = form.cleaned_data["hora_inicio"]

            hora_fin = form.cleaned_data["hora_fin"]

            try:

                # ==========================================
                # TRANSACCIÓN
                #
                # Si falla cualquier validación,
                # no queda información parcial guardada.
                # ==========================================

                with transaction.atomic():

                    # ======================================
                    # 1. CREAR OFERTA ACADÉMICA
                    # ======================================

                    oferta = OfertaAcademica(
                        asignatura=asignatura,
                        profesor=profesor,
                        periodo=periodo,
                        modalidad=modalidad,
                        activo=True,
                    )

                    oferta.full_clean()
                    oferta.save()

                    # ======================================
                    # 2. ASOCIAR GRUPOS
                    # ======================================

                    for grupo in grupos:

                        oferta_grupo = OfertaGrupo(
                            oferta=oferta,
                            grupo=grupo,
                            cupos=cupos,
                        )

                        oferta_grupo.full_clean()
                        oferta_grupo.save()

                    # ======================================
                    # 3. CREAR HORARIO
                    # ======================================

                    horario = Horario(
                        oferta=oferta,
                        sede=form.cleaned_data["sede"],
                        aula=aula,
                        dia=dia,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        activo=True,
                    )

                    # --------------------------------------
                    # Aquí se ejecutan las validaciones de:
                    #
                    # - profesor
                    # - aula
                    # - grupos
                    # - superposición horaria
                    # --------------------------------------

                    horario.full_clean()

                    horario.save()

            except ValidationError as error:

                agregar_errores_formulario(
                    form,
                    error,
                    locals().get("horario"),
                )

            else:

                cantidad_grupos = grupos.count()

                if cantidad_grupos > 1:

                    mensaje = "Asignación transversal creada " "correctamente."

                else:

                    mensaje = "Asignación creada " "correctamente."

                messages.success(
                    request,
                    mensaje,
                )

                return redirect(volver_a)

    # ======================================================
    # GET
    # ======================================================

    else:

        form = NuevaAsignacionForm(
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            periodo=periodo,
            sede_inicial=sede_inicial,
        )

    # ======================================================
    # CONTEXTO
    # ======================================================

    context = {
        "form": form,
        "centro": centro,
        "programa": programa,
        "periodo": periodo,
        "semestre": semestre,
        "sede": sede_inicial,
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
def editar_asignacion(
    request,
    horario_id,
):

    # ======================================================
    # HORARIO ACTUAL
    # ======================================================

    horario = get_object_or_404(
        Horario.objects.select_related(
            "oferta",
            "oferta__asignatura",
            "oferta__profesor",
            "oferta__periodo",
            "oferta__modalidad",
            "aula",
            "aula__sede",
            "aula__sede__centro_tutorial",
        ).prefetch_related(
            "oferta__grupos",
        ),
        pk=horario_id,
    )

    oferta = horario.oferta

    # ======================================================
    # GRUPOS ACTUALES
    # ======================================================

    grupos_actuales = list(
        oferta.grupos.select_related(
            "programa",
            "centro_tutorial",
            "periodo",
            "semestre",
        ).all()
    )

    if not grupos_actuales:

        messages.error(
            request,
            ("La oferta académica no tiene " "grupos asociados."),
        )

        return redirect("planificacion")

    # ------------------------------------------------------
    # Utilizamos el primer grupo como contexto de referencia.
    #
    # En una asignación transversal pueden existir varios
    # programas, pero todos pertenecen al mismo periodo,
    # centro y semestre.
    # ------------------------------------------------------

    grupo_referencia = grupos_actuales[0]

    centro = grupo_referencia.centro_tutorial

    programa = grupo_referencia.programa

    periodo = oferta.periodo

    semestre = grupo_referencia.semestre

    sede_actual = horario.sede

    # ======================================================
    # URL DE RETORNO
    # ======================================================

    volver_a = (
        request.POST.get("volver_a")
        or request.GET.get("volver_a")
        or request.META.get("HTTP_REFERER")
        or "/"
    )

    # ======================================================
    # CUPOS ACTUALES
    # ======================================================

    oferta_grupos_actuales = list(
        OfertaGrupo.objects.filter(
            oferta=oferta,
        ).select_related(
            "grupo",
            "grupo__programa",
        )
    )

    if oferta_grupos_actuales:

        cupos_actuales = oferta_grupos_actuales[0].cupos

    else:

        cupos_actuales = 30

    # ======================================================
    # POST
    # ======================================================

    if request.method == "POST":

        form = NuevaAsignacionForm(
            request.POST,
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            periodo=periodo,
            sede_inicial=sede_actual,
        )

        if form.is_valid():

            asignatura = form.cleaned_data["asignatura"]

            profesor = form.cleaned_data["profesor"]

            modalidad = form.cleaned_data["modalidad"]

            grupos = form.cleaned_data["grupos"]

            cupos = form.cleaned_data["cupos"]

            aula = form.cleaned_data["aula"]

            dia = form.cleaned_data["dia"]

            hora_inicio = form.cleaned_data["hora_inicio"]

            hora_fin = form.cleaned_data["hora_fin"]

            try:

                # ==========================================
                # TRANSACCIÓN
                #
                # Si una validación falla, toda la edición
                # vuelve automáticamente a su estado previo.
                # ==========================================

                with operacion_planificacion([oferta.profesor_id, profesor.pk], excluir_horario=horario.pk):

                    # ======================================
                    # 1. ACTUALIZAR OFERTA
                    # ======================================

                    oferta.asignatura = asignatura
                    oferta.profesor = profesor
                    oferta.modalidad = modalidad
                    oferta.periodo = periodo
                    oferta.activo = True

                    oferta.full_clean()

                    oferta.save()

                    # ======================================
                    # 2. ACTUALIZAR GRUPOS
                    #
                    # Eliminamos las asociaciones anteriores
                    # y reconstruimos las seleccionadas.
                    # ======================================

                    OfertaGrupo.objects.filter(
                        oferta=oferta,
                    ).delete()

                    for grupo in grupos:

                        oferta_grupo = OfertaGrupo(
                            oferta=oferta,
                            grupo=grupo,
                            cupos=cupos,
                        )

                        oferta_grupo.full_clean()

                        oferta_grupo.save()

                    # ======================================
                    # 3. ACTUALIZAR HORARIO
                    # ======================================

                    horario.sede = form.cleaned_data["sede"]
                    horario.aula = aula
                    horario.dia = dia
                    horario.hora_inicio = hora_inicio
                    horario.hora_fin = hora_fin
                    horario.activo = True

                    # --------------------------------------
                    # Horario.clean() excluye su propio PK,
                    # por lo que no se detectará a sí mismo
                    # como conflicto.
                    # --------------------------------------

                    horario.full_clean()

                    horario.save()

            except ValidationError as error:

                agregar_errores_formulario(
                    form,
                    error,
                    locals().get("horario"),
                )

            else:

                if grupos.count() > 1:

                    mensaje = "Asignación transversal " "actualizada correctamente."

                else:

                    mensaje = "Asignación actualizada " "correctamente."

                messages.success(
                    request,
                    mensaje,
                )

                return redirect(volver_a)

    # ======================================================
    # GET
    # ======================================================

    else:

        form = NuevaAsignacionForm(
            programa=programa,
            semestre=semestre,
            centro_tutorial=centro,
            periodo=periodo,
            sede_inicial=sede_actual,
            initial={
                "asignatura": (oferta.asignatura_id),
                "profesor": (oferta.profesor_id),
                "modalidad": (oferta.modalidad_id),
                "grupos": [grupo.id for grupo in grupos_actuales],
                "cupos": (cupos_actuales),
                "sede": (sede_actual.id if sede_actual else None),
                "aula": (horario.aula_id),
                "dia": (horario.dia),
                "hora_inicio": (horario.hora_inicio),
                "hora_fin": (horario.hora_fin),
            },
        )

    # ======================================================
    # CONTEXTO
    # ======================================================

    context = {
        "form": form,
        "horario": horario,
        "oferta": oferta,
        "centro": centro,
        "programa": programa,
        "periodo": periodo,
        "semestre": semestre,
        "sede": sede_actual,
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
def eliminar_asignacion(
    request,
    horario_id,
):

    horario = get_object_or_404(
        Horario.objects.select_related(
            "oferta",
            "oferta__asignatura",
            "oferta__profesor",
            "aula",
        ),
        pk=horario_id,
    )

    oferta = horario.oferta

    volver_a = request.POST.get("volver_a") or request.GET.get("volver_a") or "/"

    # ======================================================
    # INFORMACIÓN PARA LA CONFIRMACIÓN
    # ======================================================

    grupos = list(
        oferta.grupos.select_related(
            "programa",
        ).all()
    )

    # ======================================================
    # ELIMINAR
    # ======================================================

    if request.method == "POST":

        try:

            with transaction.atomic():

                # Guardamos información antes de eliminar.

                nombre_asignatura = oferta.asignatura.nombre

                # ------------------------------------------
                # Eliminamos el horario seleccionado.
                # ------------------------------------------

                horario.delete()

                # ------------------------------------------
                # ¿La oferta todavía tiene otros horarios?
                # ------------------------------------------

                tiene_otros_horarios = Horario.objects.filter(
                    oferta=oferta,
                ).exists()

                # ------------------------------------------
                # Si no quedan horarios, la Oferta Académica
                # ya no tiene razón de existir.
                #
                # Al eliminar OfertaAcademica se eliminarán
                # también sus OfertaGrupo mediante CASCADE.
                # ------------------------------------------

                if not tiene_otros_horarios:

                    oferta.delete()

        except Exception:

            messages.error(
                request,
                ("No fue posible eliminar la " "asignación."),
            )

        else:

            messages.success(
                request,
                (
                    f'La asignación "{nombre_asignatura}" '
                    "fue eliminada correctamente."
                ),
            )

        return redirect(volver_a)

    # ======================================================
    # CONFIRMACIÓN
    # ======================================================

    context = {
        "horario": horario,
        "oferta": oferta,
        "grupos": grupos,
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
        "aula__sede", "sede",
    )

    if sede_id:
        horarios_exportacion = horarios_exportacion.filter(sede_id=sede_id)

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
        ofertas_grupo = ofertas_grupo.filter(oferta__horarios__sede_id=sede_id)

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
                horario.aula.nombre if horario.aula_id else "Aula pendiente",
                horario.sede.nombre,
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


@require_GET
def eventos_calendario(request):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.view_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para consultar horarios."]}}, status=403)
    try:
        contexto = resolver_contexto_calendario(request.GET)
    except ValidationError as error:
        return JsonResponse({"errors": error.message_dict}, status=400)
    except Http404:
        return JsonResponse({"errors": {"__all__": ["El contexto académico no existe o no es válido."]}}, status=404)
    return JsonResponse([serializar_evento(h) for h in horarios_del_contexto(**contexto)], safe=False)


@require_POST
def mover_horario(request):
    return _actualizar_bloque_horario(request, resize=False)


@require_POST
def redimensionar_horario(request):
    return _actualizar_bloque_horario(request, resize=True)


def _actualizar_bloque_horario(request, *, resize):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.change_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para modificar horarios."]}}, status=403)
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"errors": {"__all__": ["Envíe un objeto JSON válido."]}}, status=400)
    form = MoverHorarioForm(datos)
    if not form.is_valid():
        return JsonResponse({"errors": dict(form.errors)}, status=400)
    try:
        with transaction.atomic():
            horario = Horario.objects.select_related(
                "oferta__profesor", "oferta__periodo", "oferta__asignatura", "aula__sede", "oferta__modalidad",
            ).prefetch_related("oferta__grupos__programa").get(
                pk=form.cleaned_data["horario_id"], activo=True, oferta__activo=True,
            )
            original = datos.get("original")
            if original is not None and original != {
                "dia": horario.dia, "hora_inicio": horario.hora_inicio.isoformat(), "hora_fin": horario.hora_fin.isoformat(),
            }:
                return JsonResponse({"errors": {"__all__": ["El horario cambió en otra sesión. Actualice el calendario."]}}, status=409)
            fecha = date(2000, 1, 1)
            duracion = datetime.combine(fecha, horario.hora_fin) - datetime.combine(fecha, horario.hora_inicio)
            nueva_duracion = datetime.combine(fecha, form.cleaned_data["hora_fin"]) - datetime.combine(fecha, form.cleaned_data["hora_inicio"])
            if resize and (form.cleaned_data["dia"] != horario.dia or form.cleaned_data["hora_inicio"] != horario.hora_inicio):
                raise ValidationError("El cambio de duración solo puede modificar la hora final.")
            if not resize and nueva_duracion != duracion:
                raise ValidationError({"hora_fin": "Mover un horario debe conservar su duración."})
            horario._original_calendario = original
            horario.dia = form.cleaned_data["dia"]
            horario.hora_inicio = form.cleaned_data["hora_inicio"]
            horario.hora_fin = form.cleaned_data["hora_fin"]
            horario.full_clean()
            horario.save(update_fields=["dia", "hora_inicio", "hora_fin"])
            evento = serializar_evento(horario)
    except Horario.DoesNotExist:
        return JsonResponse({"errors": {"__all__": ["El horario no existe o está inactivo."]}}, status=404)
    except ValidationError as error:
        errores = error.message_dict if hasattr(error, "message_dict") else {"__all__": error.messages}
        return JsonResponse(respuesta_error(error, locals().get("horario")), status=400)
    return JsonResponse({"ok": True, "event": evento})


@require_GET
def detalle_oferta_calendario(request, oferta_id):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.view_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para consultar horarios."]}}, status=403)
    try:
        contexto = resolver_contexto_calendario(request.GET)
        oferta = oferta_del_contexto(oferta_id, contexto)
    except ValidationError as error:
        return JsonResponse({"errors": error.message_dict}, status=400)
    except Http404:
        return JsonResponse({"errors": {"__all__": ["Oferta no disponible para el contexto seleccionado."]}}, status=404)
    resumen = obtener_resumen_docente([oferta.profesor_id], oferta.periodo)
    carga = obtener_carga_activa(oferta.profesor_id, oferta.periodo, resumen=resumen)
    pendientes = calcular_horas_pendientes(oferta.profesor_id, oferta.periodo, resumen=resumen)
    plan = PlanEstudioAsignatura.objects.filter(asignatura=oferta.asignatura, programa=contexto["programa"],
        semestre=contexto["semestre"], activo=True).select_related("area_academica").first()
    from .presentacion import horarios_con_contexto, evento_con_contexto
    ocupaciones = horarios_con_contexto(Horario.objects.filter(activo=True, oferta__activo=True,
        oferta__profesor=oferta.profesor, oferta__periodo=oferta.periodo)).order_by("dia", "hora_inicio", "pk")
    return JsonResponse({
        "oferta_id": oferta.pk, "asignatura": oferta.asignatura.nombre,
        "area_academica": plan.area_academica.nombre if plan and plan.area_academica else "Área académica no registrada",
        "codigo_asignatura": oferta.asignatura.codigo, "profesor": str(oferta.profesor),
        "programas": list(dict.fromkeys(g.programa.nombre for g in oferta.grupos.all())),
        "facultades": list(dict.fromkeys(g.programa.facultad.nombre for g in oferta.grupos.all())),
        "ocupaciones": [evento_con_contexto(h) for h in ocupaciones],
        "grupos": [{"id": g.pk, "codigo": g.codigo, "programa": g.programa.nombre} for g in oferta.grupos.all()],
        "modalidad": oferta.modalidad.nombre,
        "horas_asignadas": str(carga.horas_asignadas) if carga else None,
        "horas_planificadas": str(calcular_horas_planificadas(oferta.profesor_id, oferta.periodo, resumen=resumen)),
        "horas_pendientes": str(pendientes) if pendientes is not None else None,
        "disponibilidad": [{"dia": b.dia, "nombre_dia": b.get_dia_display(),
            "hora_inicio": b.hora_inicio.isoformat(), "hora_fin": b.hora_fin.isoformat()}
            for b in resumen[oferta.profesor_id]["disponibilidad"]],
        "aulas": [{"id": a.pk, "nombre": a.nombre, "sede": a.sede.nombre, "tipo": a.tipo, "capacidad": a.capacidad}
                  for a in aulas_del_contexto(contexto)],
    })


@require_POST
def crear_horario_oferta(request):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.add_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para crear horarios."]}}, status=403)
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"errors": {"__all__": ["Envíe un objeto JSON válido."]}}, status=400)
    form = CrearHorarioOfertaForm(datos)
    if not form.is_valid():
        return JsonResponse({"errors": dict(form.errors)}, status=400)
    try:
        with transaction.atomic():
            contexto = resolver_contexto_calendario(request.GET)
            oferta = oferta_del_contexto(form.cleaned_data["oferta_id"], contexto)
            aula_id = form.cleaned_data["aula_id"]
            aula = get_object_or_404(aulas_del_contexto(contexto), pk=aula_id) if aula_id else None
            horario = Horario(oferta=oferta, sede=contexto["sede"], aula=aula, dia=form.cleaned_data["dia"],
                hora_inicio=form.cleaned_data["hora_inicio"], hora_fin=form.cleaned_data["hora_fin"])
            horario.full_clean()
            horario.save()
            evento = serializar_evento(horario)
    except Http404:
        return JsonResponse({"errors": {"__all__": ["La oferta o el aula no existe, está inactiva o no pertenece al contexto seleccionado."]}}, status=404)
    except ValidationError as error:
        errores = error.message_dict if hasattr(error, "message_dict") else {"__all__": error.messages}
        return JsonResponse(respuesta_error(error, locals().get("horario")), status=400)
    return JsonResponse({"ok": True, "horario_id": horario.pk, "event": evento,
        "message": "Horario creado correctamente."}, status=201)


@require_GET
def aulas_horario_calendario(request, horario_id):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.view_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para consultar horarios."]}}, status=403)
    try:
        contexto = resolver_contexto_calendario(request.GET)
        horario = get_object_or_404(horarios_del_contexto(**contexto), pk=horario_id)
    except ValidationError as error:
        return JsonResponse({"errors": error.message_dict}, status=400)
    except Http404:
        return JsonResponse({"errors": {"__all__": ["El horario no pertenece al contexto seleccionado."]}}, status=404)
    return JsonResponse({"event": serializar_evento(horario), "aulas": [
        {"id": a.pk, "nombre": a.nombre, "sede": a.sede.nombre} for a in aulas_del_contexto({**contexto, "sede": horario.sede})]})


@require_POST
def asignar_aula_horario(request):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.change_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para modificar horarios."]}}, status=403)
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict): raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"errors": {"__all__": ["Envíe un objeto JSON válido."]}}, status=400)
    form = AsignarAulaHorarioForm(datos)
    if not form.is_valid(): return JsonResponse({"errors": dict(form.errors)}, status=400)
    try:
        with transaction.atomic():
            contexto = resolver_contexto_calendario(request.GET)
            horario = get_object_or_404(horarios_del_contexto(**contexto), pk=form.cleaned_data["horario_id"])
            aula = get_object_or_404(aulas_del_contexto({**contexto, "sede": horario.sede}), pk=form.cleaned_data["aula_id"])
            horario.aula = aula
            horario.save(update_fields=["aula"])
            evento = serializar_evento(horario)
    except Http404:
        return JsonResponse({"errors": {"__all__": ["El horario o el aula no pertenece al contexto seleccionado."]}}, status=404)
    except ValidationError as error:
        return JsonResponse(respuesta_error(error, locals().get("horario")), status=400)
    return JsonResponse({"ok": True, "event": evento, "message": "Aula actualizada correctamente."})


@require_POST
def eliminar_horario_calendario(request):
    """Elimina mediante el protocolo transaccional central de Horario.delete()."""
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.delete_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para eliminar horarios."]}}, status=403)
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict) or set(datos) != {"horario_id"}:
            raise ValueError
        pk = datos["horario_id"]
        if isinstance(pk, bool) or not isinstance(pk, int) or pk <= 0:
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"errors": {"horario_id": ["Envíe únicamente un horario_id entero válido."]}}, status=400)
    try:
        with transaction.atomic():
            horario = Horario.objects.get(pk=pk)
            horario.delete()
    except Horario.DoesNotExist:
        return JsonResponse({"errors": {"horario_id": ["El horario no existe."]}}, status=404)
    except ValidationError as error:
        return JsonResponse({"errors": {"__all__": error.messages}}, status=409)
    return JsonResponse({"ok": True})


@require_GET
def ocupaciones_oferta(request, oferta_id):
    if not request.user.is_authenticated:
        return JsonResponse({"errors": {"__all__": ["Debe iniciar sesión."]}}, status=401)
    if not request.user.has_perm("horarios.view_horario"):
        return JsonResponse({"errors": {"__all__": ["No tiene permiso para consultar horarios."]}}, status=403)
    from .presentacion import horarios_con_contexto, evento_con_contexto
    try:
        contexto = resolver_contexto_calendario(request.GET)
        oferta = oferta_del_contexto(oferta_id, contexto)
    except ValidationError as error:
        return JsonResponse({"errors": error.message_dict}, status=400)
    except Http404:
        return JsonResponse({"errors": {"__all__": ["Oferta no disponible en este contexto."]}}, status=404)
    visibles = set(horarios_del_contexto(**contexto).values_list("pk", flat=True))
    globales = horarios_con_contexto(Horario.objects.filter(activo=True, oferta__activo=True,
        oferta__profesor=oferta.profesor, oferta__periodo=oferta.periodo).exclude(pk__in=visibles)).order_by("pk")
    eventos = []
    for horario in globales:
        evento = evento_con_contexto(horario)
        evento.update(id=f"ocupacion-{horario.pk}", editable=False, startEditable=False, durationEditable=False, classNames=["evento-ocupacion-externa"])
        evento["extendedProps"]["ocupacion_externa"] = True
        eventos.append(evento)
    disponibilidad = DisponibilidadProfesor.objects.filter(profesor=oferta.profesor,
        periodo=oferta.periodo, activo=True).order_by("dia", "hora_inicio", "pk")
    return JsonResponse({"profesor": str(oferta.profesor), "periodo": oferta.periodo.codigo,
        "ocupaciones": eventos, "disponibilidad": [{"dia": b.dia, "hora_inicio": b.hora_inicio.isoformat(),
        "hora_fin": b.hora_fin.isoformat()} for b in disponibilidad]})
