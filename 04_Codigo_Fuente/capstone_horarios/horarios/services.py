"""Cálculos semanales; no imponen disponibilidad ni carga a los horarios."""
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Prefetch

from academico.models import CargaDocente, DisponibilidadProfesor, PlanEstudioAsignatura
from .models import Grupo, Horario, OfertaAcademica


def calcular_horas_planificadas(profesor, periodo, *, resumen=None):
    """Acepta instancias o PK. Suma cada Horario una vez, sin unir sus grupos.

    Conserva segundos y microsegundos; no redondea duraciones individuales.
    """
    if resumen is not None:
        return resumen[getattr(profesor, "pk", profesor)]["horas_planificadas"]
    horarios = Horario.objects.filter(
        activo=True, oferta__activo=True,
        oferta__profesor=profesor, oferta__periodo=periodo,
    ).values_list("hora_inicio", "hora_fin")
    total_microsegundos = 0
    fecha = date(2000, 1, 1)
    for inicio, fin in horarios:
        duracion = datetime.combine(fecha, fin) - datetime.combine(fecha, inicio)
        total_microsegundos += (
            (duracion.days * 86400 + duracion.seconds) * 1000000 + duracion.microseconds
        )
    return Decimal(total_microsegundos) / Decimal("3600000000")


def obtener_carga_activa(profesor, periodo, *, resumen=None):
    """Devuelve la carga activa, o None si no está registrada."""
    if resumen is not None:
        return resumen[getattr(profesor, "pk", profesor)]["carga"]
    return CargaDocente.objects.filter(profesor=profesor, periodo=periodo, activo=True).first()


def calcular_horas_pendientes(profesor, periodo, *, resumen=None):
    """None indica ausencia de carga; conserva saldos negativos existentes."""
    carga = obtener_carga_activa(profesor, periodo, resumen=resumen)
    if carga is None:
        return None
    return carga.horas_asignadas - calcular_horas_planificadas(profesor, periodo, resumen=resumen)


def obtener_resumen_docente(profesores, periodo):
    """Carga tres consultas para todos los profesores de un único periodo.

    El resultado es local a esta consulta y no se almacena como caché persistente.
    """
    ids = {getattr(profesor, "pk", profesor) for profesor in profesores}
    resumen = {pk: {"horas_planificadas": Decimal("0"), "carga": None, "disponibilidad": []} for pk in ids}
    if not ids:
        return resumen
    microsegundos = dict.fromkeys(ids, 0)
    fecha = date(2000, 1, 1)
    horarios = Horario.objects.filter(
        activo=True, oferta__activo=True, oferta__profesor_id__in=ids, oferta__periodo=periodo,
    ).values_list("oferta__profesor_id", "hora_inicio", "hora_fin")
    for profesor_id, inicio, fin in horarios:
        duracion = datetime.combine(fecha, fin) - datetime.combine(fecha, inicio)
        microsegundos[profesor_id] += (
            (duracion.days * 86400 + duracion.seconds) * 1000000 + duracion.microseconds
        )
    for pk, total in microsegundos.items():
        resumen[pk]["horas_planificadas"] = Decimal(total) / Decimal("3600000000")
    for carga in CargaDocente.objects.filter(profesor_id__in=ids, periodo=periodo, activo=True):
        resumen[carga.profesor_id]["carga"] = carga
    bloques = DisponibilidadProfesor.objects.filter(
        profesor_id__in=ids, periodo=periodo, activo=True,
    ).order_by("profesor_id", "hora_inicio")
    orden_dias = {dia: numero for numero, (dia, _) in enumerate(Horario.DIAS)}
    for bloque in sorted(bloques, key=lambda b: (b.profesor_id, orden_dias[b.dia], b.hora_inicio)):
        resumen[bloque.profesor_id]["disponibilidad"].append(bloque)
    return resumen


def obtener_panel_academico(programa, semestre, centro, periodo, *, sede=None, grupo=None, modalidad=None):
    """Obtiene ofertas incluso sin horario; los totales docentes son globales al periodo."""
    planes = list(PlanEstudioAsignatura.objects.filter(
        programa=programa, semestre=semestre, activo=True, asignatura__activo=True,
    ).select_related("asignatura", "area_academica").order_by("asignatura__nombre"))
    if not planes:
        return []
    grupos = Grupo.objects.filter(
        programa=programa, semestre=semestre, centro_tutorial=centro, periodo=periodo, activo=True,
    ).order_by("codigo")
    if grupo:
        grupos = grupos.filter(pk=grupo.pk)
    ofertas = OfertaAcademica.objects.filter(
        activo=True, periodo=periodo, asignatura_id__in=[p.asignatura_id for p in planes],
        grupos__in=grupos,
    )
    if modalidad:
        ofertas = ofertas.filter(modalidad=modalidad)
    # La oferta no pertenece a una sede: se elige el aula al crear cada Horario.
    # Conservar ofertas sin horario para permitir planificar en la sede elegida.
    if sede and modalidad is None:
        ofertas = ofertas.filter(horarios__activo=True, horarios__aula__sede=sede)
    ofertas = list(ofertas.select_related("profesor", "modalidad").prefetch_related(
        Prefetch("grupos", queryset=grupos, to_attr="grupos_contexto"),
    ).distinct().order_by("asignatura_id", "profesor__apellido", "profesor__nombre"))
    resumen = obtener_resumen_docente([o.profesor_id for o in ofertas], periodo)
    por_asignatura = {}
    for oferta in ofertas:
        tarjeta = por_asignatura.setdefault(oferta.asignatura_id, {"grupos": {}, "modalidades": {}, "profesores": {}})
        tarjeta["grupos"].update({g.pk: g for g in oferta.grupos_contexto})
        tarjeta["modalidades"][oferta.modalidad_id] = oferta.modalidad
        docente = tarjeta["profesores"].setdefault(oferta.profesor_id, {
            "profesor": oferta.profesor,
            "carga": obtener_carga_activa(oferta.profesor_id, periodo, resumen=resumen),
            "horas_planificadas": calcular_horas_planificadas(oferta.profesor_id, periodo, resumen=resumen),
            "horas_pendientes": calcular_horas_pendientes(oferta.profesor_id, periodo, resumen=resumen),
            "disponibilidad": resumen[oferta.profesor_id]["disponibilidad"],
            "ofertas": [],
        })
        docente["ofertas"].append(oferta)
    resultado = []
    for plan in planes:
        tarjeta = por_asignatura.get(plan.asignatura_id, {"grupos": {}, "modalidades": {}, "profesores": {}})
        resultado.append({"plan": plan, **{campo: list(valores.values()) for campo, valores in tarjeta.items()}})
    return resultado
