"""Contexto y proyección visual de bloques semanales. No almacena fechas."""
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from academico.models import CentroTutorial, Facultad, PeriodoAcademico, ProgramaAcademico, ProgramaCentroTutorial, Sede, Semestre
from .models import Grupo, Horario

SEMANA_REFERENCIA = date(2000, 1, 3)  # Lunes; la fecha no tiene significado académico.


def resolver_contexto_calendario(parametros):
    ids = {}
    for campo in ["centro", "facultad", "programa", "periodo", "semestre", "sede", "grupo"]:
        valor = parametros.get(campo, "").strip()
        if not valor and campo in ("sede", "grupo"):
            ids[campo] = None
            continue
        try:
            ids[campo] = int(valor)
            if ids[campo] <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValidationError({campo: "Seleccione un identificador válido para este filtro."})
    centro = get_object_or_404(CentroTutorial, pk=ids["centro"], activo=True)
    facultad = get_object_or_404(Facultad, pk=ids["facultad"], activo=True)
    programa = get_object_or_404(ProgramaAcademico, pk=ids["programa"], facultad=facultad, activo=True)
    get_object_or_404(ProgramaCentroTutorial, programa=programa, centro_tutorial=centro, activo=True)
    periodo = get_object_or_404(PeriodoAcademico, pk=ids["periodo"], activo=True)
    semestre = get_object_or_404(Semestre, pk=ids["semestre"])
    sede = get_object_or_404(Sede, pk=ids["sede"], centro_tutorial=centro, activo=True) if ids["sede"] else None
    grupo = get_object_or_404(Grupo, pk=ids["grupo"], programa=programa, centro_tutorial=centro,
                              periodo=periodo, semestre=semestre, activo=True) if ids["grupo"] else None
    return dict(centro=centro, facultad=facultad, programa=programa, periodo=periodo,
                semestre=semestre, sede=sede, grupo=grupo)


def horarios_del_contexto(centro, facultad, programa, periodo, semestre, sede=None, grupo=None):
    horarios = Horario.objects.filter(
        activo=True, oferta__activo=True, oferta__periodo=periodo,
        oferta__grupos__centro_tutorial=centro, oferta__grupos__programa=programa,
        oferta__grupos__semestre=semestre, oferta__grupos__periodo=periodo, oferta__grupos__activo=True,
    )
    if sede:
        horarios = horarios.filter(aula__sede=sede)
    if grupo:
        horarios = horarios.filter(oferta__grupos=grupo)
    return horarios.select_related(
        "oferta__asignatura", "oferta__profesor", "oferta__periodo", "oferta__modalidad", "aula__sede",
    ).prefetch_related(Prefetch("oferta__grupos", queryset=Grupo.objects.select_related("programa"))).distinct().order_by("dia", "hora_inicio", "pk")


def serializar_evento(horario):
    grupos = list(horario.oferta.grupos.all())
    offset = [codigo for codigo, _ in Horario.DIAS].index(horario.dia)
    fecha = SEMANA_REFERENCIA + timedelta(days=offset)
    modalidad = horario.oferta.modalidad
    clase = "evento-transversal" if len(grupos) > 1 else {
        "VIR": "evento-virtual", "HIB": "evento-hibrida",
    }.get(modalidad.codigo.strip().upper(), "evento-presencial")
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
            "aula": horario.aula.nombre, "modalidad": modalidad.nombre,
            "dia": horario.dia, "hora_inicio": horario.hora_inicio.isoformat(),
            "hora_fin": horario.hora_fin.isoformat(),
        },
    }
