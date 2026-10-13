"""Contexto y proyección visual de bloques semanales. No almacena fechas."""
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Prefetch, F, Q
from django.shortcuts import get_object_or_404

from academico.models import CentroTutorial, Facultad, PeriodoAcademico, ProgramaAcademico, ProgramaCentroTutorial, Sede, Semestre, PlanEstudioAsignatura, Aula, Modalidad
from .models import Grupo, Horario, OfertaAcademica

SEMANA_REFERENCIA = date(2000, 1, 3)  # Lunes; la fecha no tiene significado académico.


def ofertas_de_programa(centro, programa):
    return OfertaAcademica.objects.filter(
        activo=True, periodo__activo=True, modalidad__activo=True,
        grupos__activo=True, grupos__centro_tutorial=centro,
        grupos__programa=programa, grupos__periodo_id=F("periodo_id"),
    )


def resolver_contexto_calendario(parametros):
    ids = {}
    for campo in ["centro", "facultad", "programa", "modalidad", "sede", "periodo", "semestre"]:
        try:
            ids[campo] = int(parametros.get(campo, ""))
            if ids[campo] <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValidationError({campo: "Seleccione un identificador válido para este filtro obligatorio."})
    centro = get_object_or_404(CentroTutorial, pk=ids["centro"], activo=True)
    facultad = get_object_or_404(Facultad, pk=ids["facultad"], activo=True)
    programa = get_object_or_404(ProgramaAcademico, pk=ids["programa"], facultad=facultad, activo=True)
    get_object_or_404(ProgramaCentroTutorial, programa=programa, centro_tutorial=centro, activo=True)
    ofertas = ofertas_de_programa(centro, programa)
    modalidad = get_object_or_404(Modalidad, pk=ids["modalidad"], activo=True,
        pk__in=ofertas.values("modalidad_id"))
    sede = get_object_or_404(Sede, pk=ids["sede"], centro_tutorial=centro, activo=True)
    ofertas = ofertas.filter(modalidad=modalidad)
    periodo = get_object_or_404(PeriodoAcademico, pk=ids["periodo"], activo=True,
        pk__in=ofertas.values("periodo_id"))
    semestre = get_object_or_404(Semestre.objects.distinct(), pk=ids["semestre"],
        grupos__centro_tutorial=centro, grupos__programa=programa, grupos__periodo=periodo,
        grupos__activo=True)
    return dict(centro=centro, facultad=facultad, programa=programa, modalidad=modalidad,
                periodo=periodo, semestre=semestre, sede=sede)


def horarios_del_contexto(centro, facultad, programa, modalidad, periodo, semestre, sede):
    horarios = Horario.objects.filter(
        activo=True, oferta__activo=True, oferta__periodo=periodo, oferta__modalidad=modalidad,
        oferta__grupos__centro_tutorial=centro, oferta__grupos__programa=programa,
        oferta__grupos__semestre=semestre, oferta__grupos__periodo=periodo, oferta__grupos__activo=True,
    )
    horarios = horarios.filter(sede=sede)
    return horarios.select_related(
        "oferta__asignatura", "oferta__profesor", "oferta__periodo", "oferta__modalidad", "aula__sede", "sede",
    ).prefetch_related(Prefetch("oferta__grupos", queryset=Grupo.objects.select_related("programa"))).distinct().order_by("dia", "hora_inicio", "pk")


def serializar_evento(horario):
    grupos = list(horario.oferta.grupos.all())
    offset = [codigo for codigo, _ in Horario.DIAS].index(horario.dia)
    fecha = SEMANA_REFERENCIA + timedelta(days=offset)
    modalidad = horario.oferta.modalidad
    clase = "evento-completo" if horario.aula_id else "evento-pendiente"
    return {
        "id": str(horario.pk), "title": horario.oferta.asignatura.nombre,
        "start": datetime.combine(fecha, horario.hora_inicio).isoformat(),
        "end": datetime.combine(fecha, horario.hora_fin).isoformat(),
        "allDay": False, "classNames": [clase],
        "extendedProps": {
            "horario_id": horario.pk,
            "asignatura": horario.oferta.asignatura.nombre,
            "codigo_asignatura": horario.oferta.asignatura.codigo,
            "profesor": str(horario.oferta.profesor),
            "grupos": [{"id": g.pk, "codigo": g.codigo, "programa": g.programa.nombre} for g in grupos],
            "aula": horario.aula.nombre if horario.aula_id else "Aula pendiente",
            "aula_id": horario.aula_id, "aula_pendiente": horario.aula_id is None,
            "sede_id": horario.sede_id, "sede": horario.sede.nombre, "modalidad": modalidad.nombre,
            "dia": horario.dia, "hora_inicio": horario.hora_inicio.isoformat(),
            "hora_fin": horario.hora_fin.isoformat(),
        },
    }


def oferta_del_contexto(oferta_id, contexto, *, bloquear=False):
    """Comprueba la oferta real y sus grupos; nunca crea relaciones académicas."""
    ofertas = OfertaAcademica.objects.select_related(
        "asignatura", "profesor", "periodo", "modalidad",
    ).prefetch_related("grupos__programa")
    if bloquear:
        ofertas = ofertas.select_for_update(of=("self",))
    oferta = get_object_or_404(ofertas, pk=oferta_id, activo=True,
        profesor__activo=True, asignatura__activo=True, periodo=contexto["periodo"], modalidad=contexto["modalidad"])
    grupos = list(oferta.grupos.all())
    compatibles = [g for g in grupos if g.activo and
        g.centro_tutorial_id == contexto["centro"].pk and
        g.programa_id == contexto["programa"].pk and
        g.periodo_id == contexto["periodo"].pk and
        g.semestre_id == contexto["semestre"].pk]
    if not compatibles or not PlanEstudioAsignatura.objects.filter(
        programa=contexto["programa"], semestre=contexto["semestre"],
        asignatura=oferta.asignatura, activo=True,
    ).exists():
        from django.http import Http404
        raise Http404("Oferta no disponible para el contexto seleccionado.")
    return oferta


def aulas_del_contexto(contexto):
    aulas = Aula.objects.filter(activo=True, sede__activo=True,
        sede__centro_tutorial=contexto["centro"], sede=contexto["sede"]).select_related("sede").order_by("sede__nombre", "nombre")
    return aulas
