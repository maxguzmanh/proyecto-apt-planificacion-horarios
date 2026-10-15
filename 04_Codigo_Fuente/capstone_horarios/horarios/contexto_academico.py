"""Consultas académicas compartidas por planificación y exportación."""
from academico.models import Facultad, ProgramaAcademico, Semestre


def facultades_del_centro(centro):
    return Facultad.objects.filter(activo=True, programas_academicos__activo=True,
        programas_academicos__centros_tutoriales__centro_tutorial=centro,
        programas_academicos__centros_tutoriales__activo=True).distinct().order_by("nombre")


def programas_del_centro(centro, facultad):
    programas = ProgramaAcademico.objects.filter(facultad=facultad, activo=True)
    if centro:
        programas = programas.filter(centros_tutoriales__centro_tutorial=centro,
            centros_tutoriales__activo=True)
    return programas.distinct().order_by("nombre")


def semestres_del_programa(centro, programa, periodo):
    return Semestre.objects.filter(grupos__centro_tutorial=centro,
        grupos__programa=programa, grupos__periodo=periodo, grupos__activo=True).distinct().order_by("numero")
