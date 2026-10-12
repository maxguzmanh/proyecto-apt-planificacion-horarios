"""Cálculos semanales; no imponen disponibilidad ni carga a los horarios."""
from datetime import date, datetime
from decimal import Decimal

from academico.models import CargaDocente
from .models import Horario


def calcular_horas_planificadas(profesor, periodo):
    """Acepta instancias o PK. Suma cada Horario una vez, sin unir sus grupos.

    Conserva segundos y microsegundos; no redondea duraciones individuales.
    """
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


def obtener_carga_activa(profesor, periodo):
    """Devuelve la carga activa, o None si no está registrada."""
    return CargaDocente.objects.filter(profesor=profesor, periodo=periodo, activo=True).first()


def calcular_horas_pendientes(profesor, periodo):
    """None indica ausencia de carga; conserva saldos negativos existentes."""
    carga = obtener_carga_activa(profesor, periodo)
    if carga is None:
        return None
    return carga.horas_asignadas - calcular_horas_planificadas(profesor, periodo)
