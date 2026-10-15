"""Cálculos, reglas docentes y guardado transaccional de planificación."""
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Prefetch
from django.db import models, transaction
from django.core.exceptions import ValidationError
from contextlib import contextmanager
from contextvars import ContextVar

from academico.models import CargaDocente, DisponibilidadProfesor, PlanEstudioAsignatura, Profesor, Aula
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo


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


def obtener_panel_academico(programa, semestre, centro, periodo, *, sede=None, grupo=None):
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
    # Ofertas sin horario también son planificables. Sede limita compatibilidad,
    # pero no recorta carga/disponibilidad, que siguen siendo profesor + periodo.
    if sede:
        from .calendario import ofertas_compatibles_con_sede
        ofertas = ofertas_compatibles_con_sede(ofertas, sede)
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


_horario_en_edicion = ContextVar("horario_en_edicion", default=None)


@contextmanager
def operacion_planificacion(profesor_ids, *, excluir_horario=None, using="default"):
    """El mismo protocolo en todos los flujos: Profesor por PK ascendente."""
    ids = sorted({pk for pk in profesor_ids if pk is not None})
    with transaction.atomic(using=using):
        bloqueados = list(Profesor.objects.using(using).select_for_update().filter(pk__in=ids).order_by("pk"))
        token = _horario_en_edicion.set(excluir_horario)
        try:
            yield bloqueados
        finally:
            _horario_en_edicion.reset(token)


def microsegundos_horario(inicio, fin):
    fecha = date(2000, 1, 1)
    delta = datetime.combine(fecha, fin) - datetime.combine(fecha, inicio)
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def intervalo_cubierto(inicio, fin, bloques):
    hasta = inicio
    for bloque in sorted(bloques, key=lambda b: b.hora_inicio):
        if bloque.hora_fin <= hasta:
            continue
        if bloque.hora_inicio > hasta:
            return False
        hasta = max(hasta, bloque.hora_fin)
        if hasta >= fin:
            return True
    return False


def validar_docencia(horario, *, horarios_oferta=None):
    """Única implementación de disponibilidad/carga, global por profesor y periodo.

    horarios_oferta permite evaluar una oferta candidata antes de persistirla.
    Las comparaciones se hacen en microsegundos; solo se redondean los mensajes.
    """
    if not horario.activo or not horario.oferta.activo:
        return
    oferta = horario.oferta
    profesor, periodo = oferta.profesor, oferta.periodo
    bloques = list(DisponibilidadProfesor.objects.filter(
        profesor=profesor, periodo=periodo, dia=horario.dia, activo=True,
    ))
    if not bloques:
        dia = dict(Horario.DIAS).get(horario.dia, horario.dia).lower()
        otros = DisponibilidadProfesor.objects.filter(profesor=profesor, periodo=periodo, activo=True).order_by("dia", "hora_inicio")
        disponibles = "; ".join(f"{b.get_dia_display()} {b.hora_inicio:%H:%M}–{b.hora_fin:%H:%M}" for b in otros)
        detalle = f" Disponibilidad del periodo: {disponibles}." if disponibles else " No hay bloques activos registrados en este periodo."
        raise ValidationError({"oferta": f"{profesor} no tiene disponibilidad registrada para el {dia}." + detalle})
    if not intervalo_cubierto(horario.hora_inicio, horario.hora_fin, bloques):
        dia = dict(Horario.DIAS).get(horario.dia, horario.dia)
        franjas = "; ".join(f"{b.hora_inicio:%H:%M}–{b.hora_fin:%H:%M}" for b in bloques)
        raise ValidationError({"oferta": f"El horario seleccionado está fuera de la disponibilidad de {profesor}. Horario solicitado: {horario.hora_inicio:%H:%M}–{horario.hora_fin:%H:%M}. Disponibilidad del {dia.lower()}: {franjas}."})
    carga = obtener_carga_activa(profesor, periodo)
    if carga is None:
        raise ValidationError({"oferta": f"Carga docente no registrada para {profesor} en el periodo {periodo}."})
    actuales = Horario.objects.filter(activo=True, oferta__activo=True,
        oferta__profesor=profesor, oferta__periodo=periodo)
    actuales = actuales.exclude(pk=_horario_en_edicion.get())
    if horarios_oferta is None:
        actuales = actuales.exclude(pk=horario.pk)
        propuestos = [horario]
    else:
        actuales = actuales.exclude(oferta_id=oferta.pk)
        propuestos = horarios_oferta
    total = sum(microsegundos_horario(inicio, fin) for inicio, fin in actuales.values_list("hora_inicio", "hora_fin"))
    total += sum(microsegundos_horario(h.hora_inicio, h.hora_fin) for h in propuestos if h.activo)
    if Decimal(total) > carga.horas_asignadas * Decimal("3600000000"):
        horas = Decimal(total) / Decimal("3600000000")
        raise ValidationError({"oferta": f"La asignación supera la carga docente de {profesor}. Carga: {carga.horas_asignadas:g} h · Planificadas resultantes: {horas:.2f} h."})


def validar_oferta_docencia(oferta):
    if not oferta.pk or not oferta.activo:
        return
    horarios = list(Horario.objects.filter(oferta_id=oferta.pk, activo=True).exclude(pk=_horario_en_edicion.get()))
    for horario in horarios:
        horario.oferta = oferta
    for horario in horarios:
        try:
            validar_docencia(horario, horarios_oferta=horarios)
        except ValidationError as error:
            raise ValidationError(error.messages) from error


def revalidar_oferta(oferta):
    if not oferta.activo:
        return
    for horario in Horario.objects.filter(oferta=oferta, activo=True).exclude(pk=_horario_en_edicion.get()).select_related(
        "oferta__profesor", "oferta__periodo", "aula",
    ):
        horario.full_clean()


def _profesores_horario(horario, using="default"):
    ids = set()
    if horario.pk:
        anterior = Horario.objects.using(using).filter(pk=horario.pk).values_list("oferta__profesor_id", flat=True).first()
        if anterior:
            ids.add(anterior)
    if horario.oferta_id:
        nuevo = OfertaAcademica.objects.using(using).filter(pk=horario.oferta_id).values_list("profesor_id", flat=True).first()
        if nuevo:
            ids.add(nuevo)
    return ids


def guardar_horario(horario, *args, **kwargs):
    using = kwargs.get("using") or horario._state.db or "default"
    ids = _profesores_horario(horario, using)
    with operacion_planificacion(ids, using=using):
        if horario.oferta_id:
            oferta = OfertaAcademica.objects.using(using).select_for_update(of=("self",)).select_related("profesor", "periodo").get(pk=horario.oferta_id)
            if oferta.profesor_id not in ids:
                raise ValidationError("La oferta cambió durante la operación. Recargue la página.")
            horario.oferta = oferta
        if horario.pk:
            anterior = Horario.objects.using(using).select_for_update().filter(pk=horario.pk).values(
                "oferta__profesor_id", "oferta_id", "aula_id", "sede_id", "activo", "dia", "hora_inicio", "hora_fin",
            ).first()
            if anterior and anterior["oferta__profesor_id"] not in ids:
                raise ValidationError("El horario cambió durante la operación. Recargue la página.")
            original = getattr(horario, "_original_calendario", None)
            if anterior and original is not None and original != {
                "dia": anterior["dia"], "hora_inicio": anterior["hora_inicio"].isoformat(), "hora_fin": anterior["hora_fin"].isoformat(),
            }:
                raise ValidationError("El horario cambió en otra sesión. Actualice el calendario.")
        # Una actualización parcial valida los valores actuales de las demás
        # columnas, no una copia desactualizada tomada antes de esperar el bloqueo.
        campos = kwargs.get("update_fields")
        if horario.pk and anterior and campos is not None:
            for campo in ["oferta", "aula", "sede", "activo", "dia", "hora_inicio", "hora_fin"]:
                atributo = campo + "_id" if campo in ("oferta", "aula", "sede") else campo
                if campo not in campos and atributo not in campos:
                    setattr(horario, atributo, anterior[atributo])
            if horario.oferta_id != oferta.pk:
                horario.oferta = OfertaAcademica.objects.using(using).select_for_update(of=("self",)).select_related("profesor", "periodo").get(pk=horario.oferta_id)
                if horario.oferta.profesor_id not in ids:
                    raise ValidationError("La oferta cambió durante la operación. Recargue la página.")
        aulas_bloqueadas = list(Aula.objects.using(using).select_for_update().filter(pk=horario.aula_id).order_by("pk"))
        if aulas_bloqueadas:
            horario.aula = aulas_bloqueadas[0]
            sede_contexto = horario.sede_id
            if sede_contexto is not None and (not horario.aula.activo or horario.aula.sede_id != sede_contexto or not horario.aula.sede.activo):
                raise ValidationError({"aula": "El aula no está activa o no pertenece a la sede del horario."})
        grupos = Grupo.objects.using(using).filter(ofertas_academicas__pk=horario.oferta_id).values_list("pk", flat=True)
        list(Grupo.objects.using(using).select_for_update().filter(pk__in=grupos).order_by("pk"))
        horario.full_clean()
        return models.Model.save(horario, *args, **kwargs)


def bloquear_recursos_oferta(oferta, *, grupo_ids_extra=(), using="default"):
    aulas = Horario.objects.using(using).filter(oferta=oferta, activo=True).values_list("aula_id", flat=True)
    list(Aula.objects.using(using).select_for_update().filter(pk__in=aulas).order_by("pk"))
    grupos = set(Grupo.objects.using(using).filter(ofertas_academicas=oferta).values_list("pk", flat=True))
    grupos.update(pk for pk in grupo_ids_extra if pk)
    list(Grupo.objects.using(using).select_for_update().filter(pk__in=grupos).order_by("pk"))


def guardar_oferta(oferta, *args, **kwargs):
    using = kwargs.get("using") or oferta._state.db or "default"
    anterior = OfertaAcademica.objects.using(using).filter(pk=oferta.pk).values_list("profesor_id", flat=True).first() if oferta.pk else None
    ids = {oferta.profesor_id, anterior}
    with operacion_planificacion(ids, excluir_horario=_horario_en_edicion.get(), using=using):
        if oferta.pk:
            actual = OfertaAcademica.objects.using(using).select_for_update().filter(pk=oferta.pk).values_list("profesor_id", flat=True).first()
            if actual not in ids:
                raise ValidationError("La oferta cambió durante la operación. Recargue la página.")
        if oferta.pk:
            bloquear_recursos_oferta(oferta, using=using)
        oferta.full_clean()
        resultado = models.Model.save(oferta, *args, **kwargs)
        revalidar_oferta(oferta)
        return resultado


def guardar_oferta_grupo(relacion, *args, **kwargs):
    oferta = OfertaAcademica.objects.get(pk=relacion.oferta_id)
    anterior = OfertaGrupo.objects.filter(pk=relacion.pk).values("oferta__profesor_id", "grupo_id").first() if relacion.pk else None
    ids = {oferta.profesor_id}
    if anterior:
        ids.add(anterior["oferta__profesor_id"])
    with operacion_planificacion(ids, excluir_horario=_horario_en_edicion.get()):
        oferta = OfertaAcademica.objects.select_for_update().get(pk=relacion.oferta_id)
        if oferta.profesor_id not in ids:
            raise ValidationError("La oferta cambió durante la operación. Recargue la página.")
        relacion.oferta = oferta
        bloquear_recursos_oferta(oferta, grupo_ids_extra=[relacion.grupo_id, anterior["grupo_id"] if anterior else None])
        relacion.full_clean()
        resultado = models.Model.save(relacion, *args, **kwargs)
        revalidar_oferta(oferta)
        return resultado


def eliminar_planificacion(objeto, *args, **kwargs):
    if isinstance(objeto, Horario):
        campo = "oferta__profesor_id"
    else:
        campo = "profesor_id"
    ids = list(type(objeto).objects.filter(pk=objeto.pk).values_list(campo, flat=True))
    with operacion_planificacion(ids):
        actual = type(objeto).objects.filter(pk=objeto.pk).values_list(campo, flat=True).first()
        if actual is not None and actual not in ids:
            raise ValidationError("La planificación cambió durante la operación. Recargue la página.")
        return models.Model.delete(objeto, *args, **kwargs)
