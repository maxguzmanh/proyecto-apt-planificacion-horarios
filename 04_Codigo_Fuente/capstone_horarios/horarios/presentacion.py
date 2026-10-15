"""Contexto informativo de horarios: no implementa validaciones de negocio."""
from django.db.models import Prefetch
from .models import Horario, Grupo
from .calendario import serializar_evento


def horarios_con_contexto(queryset):
    return queryset.select_related("sede", "aula", "oferta__asignatura", "oferta__profesor", "oferta__periodo", "oferta__modalidad").prefetch_related(
        Prefetch("oferta__grupos", queryset=Grupo.objects.select_related("centro_tutorial", "programa__facultad", "semestre")))


def evento_con_contexto(horario):
    evento = serializar_evento(horario)
    grupos = list(horario.oferta.grupos.all())
    def unicos(valores): return list(dict.fromkeys(valores))
    evento["extendedProps"].update({
        "centros": unicos(g.centro_tutorial.nombre for g in grupos),
        "facultades": unicos(g.programa.facultad.nombre for g in grupos),
        "programas": unicos(g.programa.nombre for g in grupos),
        "semestres": unicos(g.semestre.get_numero_display() for g in grupos),
        "periodo": horario.oferta.periodo.codigo,
    })
    return evento


def respuesta_error(error, candidato=None):
    errores = error.message_dict if hasattr(error, "message_dict") else {"__all__": error.messages}
    respuesta = {"errors": errores}
    # Solo enriquecer un conflicto YA rechazado por Horario.clean().
    if candidato is not None and any(m.startswith("El profesor ") and "ya tiene" in m for m in errores.get("oferta", [])):
        existente = horarios_con_contexto(Horario.objects.filter(
            oferta__profesor_id=candidato.oferta.profesor_id, oferta__periodo_id=candidato.oferta.periodo_id,
            activo=True, dia=candidato.dia, hora_inicio__lt=candidato.hora_fin, hora_fin__gt=candidato.hora_inicio,
        ).exclude(pk=candidato.pk)).order_by("pk").first()
        if existente:
            mensaje = f"{existente.oferta.profesor} ya tiene una asignación programada el {existente.get_dia_display().lower()} de {existente.hora_inicio:%H:%M} a {existente.hora_fin:%H:%M}."
            respuesta["errors"] = {**errores, "oferta": [mensaje]}
            respuesta["conflicto_profesor"] = evento_con_contexto(existente)
    return respuesta
