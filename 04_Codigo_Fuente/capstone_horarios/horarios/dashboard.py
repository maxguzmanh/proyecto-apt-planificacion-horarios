"""Resumen operativo de lectura; no almacena métricas ni modifica planificación."""
from decimal import Decimal
from urllib.parse import urlencode
from django.db.models import Count, Q, Exists, OuterRef, Prefetch
from django.urls import reverse
from academico.models import ProgramaAcademico,Profesor,Aula
from .models import Horario,OfertaAcademica,Grupo
from .services import obtener_resumen_docente,calcular_horas_planificadas,calcular_horas_pendientes


def enlace_planificacion(oferta, sede=None):
    grupos=[g for g in oferta.grupos.all() if g.activo and g.periodo_id==oferta.periodo_id]
    if not grupos: return reverse("planificacion")
    g=grupos[0]
    params={"centro":g.centro_tutorial_id,"facultad":g.programa.facultad_id,"programa":g.programa_id,
        "modalidad":oferta.modalidad_id,"periodo":oferta.periodo_id,"semestre":g.semestre_id}
    if sede: params["sede"]=sede.pk
    return reverse("planificacion")+"?"+urlencode(params)


def resumen_dashboard(periodo):
    horarios=Horario.objects.filter(activo=True,oferta__activo=True)
    ofertas=OfertaAcademica.objects.filter(activo=True).annotate(tiene_horario=Exists(Horario.objects.filter(oferta_id=OuterRef("pk"),activo=True)))
    globales=horarios.aggregate(total=Count("pk"),pendientes=Count("pk",filter=Q(aula__isnull=True)))
    datos={"total_programas":ProgramaAcademico.objects.filter(activo=True).count(),"total_profesores":Profesor.objects.filter(activo=True).count(),"total_aulas":Aula.objects.filter(activo=True).count(),"total_horarios":globales["total"],"total_pendientes":globales["pendientes"],"total_ofertas_sin_horario":ofertas.filter(tiene_horario=False).count(),"pendientes":[],"ofertas_pendientes":[],"docentes_atencion":[],"total_atencion":0,"estados":[]}
    if periodo is None: return datos
    hp=horarios.filter(oferta__periodo=periodo);op=ofertas.filter(periodo=periodo)
    estado=hp.aggregate(completos=Count("pk",filter=Q(aula__isnull=False)),pendientes=Count("pk",filter=Q(aula__isnull=True)))
    profesores=list(Profesor.objects.filter(activo=True).order_by("apellido","nombre","pk"))
    resumen=obtener_resumen_docente(profesores,periodo)
    con_carga=sin_carga=sin_disponibilidad=0
    atencion=[]
    for p in profesores:
        r=resumen[p.pk];c=r["carga"];planificadas=calcular_horas_planificadas(p,periodo,resumen=resumen);pendientes=calcular_horas_pendientes(p,periodo,resumen=resumen)
        razones=[];problema=False
        if c is None: sin_carga+=1;razones.append("Sin carga registrada");problema=planificadas>0
        else:
            con_carga+=1
            if pendientes<0: razones.append("Carga excedida");problema=True
            elif pendientes==0: razones.append("Carga completa")
            elif planificadas>=c.horas_asignadas*Decimal("0.8"): razones.append("Carga cercana al límite")
        if not r["disponibilidad"]: sin_disponibilidad+=1;razones.append("Sin disponibilidad registrada");problema=problema or planificadas>0
        if razones: atencion.append({"profesor":p,"carga":c,"planificadas":planificadas,"pendientes":pendientes,"razones":razones,"problema":problema})
    atencion.sort(key=lambda d:(not d["problema"],d["carga"] is not None,str(d["profesor"])))
    datos["docentes_atencion"]=atencion[:6];datos["total_atencion"]=len(atencion)
    datos["estados"]=[{"nombre":"Horarios completos","valor":estado["completos"],"tipo":"correcto"},{"nombre":"Aula pendiente","valor":estado["pendientes"],"tipo":"pendiente"},{"nombre":"Ofertas sin horario","valor":op.filter(tiene_horario=False).count(),"tipo":"informacion"},{"nombre":"Profesores con carga","valor":con_carga,"tipo":"correcto"},{"nombre":"Profesores sin carga","valor":sin_carga,"tipo":"pendiente"},{"nombre":"Profesores sin disponibilidad","valor":sin_disponibilidad,"tipo":"pendiente"}]
    grupos=Prefetch("oferta__grupos",queryset=Grupo.objects.select_related("programa__facultad").order_by("pk"))
    for h in hp.filter(aula__isnull=True).select_related("oferta__asignatura","oferta__profesor","oferta__modalidad","sede").prefetch_related(grupos).order_by("dia","hora_inicio","pk")[:5]:
        datos["pendientes"].append({"horario":h,"url":enlace_planificacion(h.oferta,h.sede)})
    for o in op.filter(tiene_horario=False).select_related("asignatura","profesor","modalidad").prefetch_related(Prefetch("grupos",queryset=Grupo.objects.select_related("programa__facultad").order_by("pk"))).order_by("asignatura__nombre","pk")[:5]:
        datos["ofertas_pendientes"].append({"oferta":o,"programas":sorted({g.programa.nombre for g in o.grupos.all()}),"url":enlace_planificacion(o)})
    return datos
