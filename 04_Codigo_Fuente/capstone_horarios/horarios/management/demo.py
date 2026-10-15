"""Enriquecimiento explícito del catálogo DEMO: nunca escribe Horario."""
from datetime import time
from decimal import Decimal, ROUND_CEILING
from django.core.management.base import CommandError
from academico.models import Profesor,PeriodoAcademico,CentroTutorial,PlanEstudioAsignatura,Modalidad,CargaDocente,DisponibilidadProfesor
from horarios.models import Horario,Grupo,OfertaAcademica,OfertaGrupo
from horarios.services import calcular_horas_planificadas,microsegundos_horario

OPCIONES={"PROGWEB01":[1,6],"BD01":[2,1],"SO01":[3],"ARQ01":[1],"COMP001":[4],"DIGI001":[5,4,7],"LOG001":[6],"EST001":[7],"GEST001":[6,7],"CONT001":[3],"INV001":[7]}
PROGRAMAS=["ING-INF","ING-IND","TEC-SIS","ADM-EMP","CONT-PUB"]
CARGAS={1:12,2:10,3:12,4:8,5:10,6:12,7:16}


def enriquecer(comando):
    centro=CentroTutorial.objects.get(codigo="CT-DEMO",activo=True)
    periodo=PeriodoAcademico.objects.get(codigo="01-2026",activo=True)
    for n in range(1,7):
        if not Profesor.objects.filter(identificacion=f"DOC-DEMO-{n:03d}",activo=True).exists():
            raise CommandError("Primero debe existir el catálogo demo de los seis profesores originales.")
    Profesor.objects.get_or_create(identificacion="DOC-DEMO-007",defaults={"nombre":"Natalia","apellido":"Vega","activo":True})
    profesores={int(p.identificacion[-3:]):p for p in Profesor.objects.select_for_update().filter(identificacion__in=[f"DOC-DEMO-{n:03d}" for n in CARGAS]).order_by("pk")}
    # Se conserva cada bloque existente. Solo se agregan huecos sin solapamiento.
    for n,p in profesores.items():
        planificadas=calcular_horas_planificadas(p,periodo)
        asignadas=max(Decimal(CARGAS[n]),(planificadas/4).to_integral_value(rounding=ROUND_CEILING)*4)
        carga=CargaDocente.objects.filter(profesor=p,periodo=periodo,activo=True).first()
        if carga is None: carga=CargaDocente(profesor=p,periodo=periodo)
        carga.horas_asignadas=asignadas;carga.full_clean();carga.save()
        def completar(dia,inicio,fin):
            bloques=list(DisponibilidadProfesor.objects.filter(profesor=p,periodo=periodo,dia=dia,activo=True).order_by("hora_inicio"))
            desde=inicio
            for b in bloques:
                if b.hora_fin<=desde: continue
                if b.hora_inicio>=fin: break
                if b.hora_inicio>desde: agregar(dia,desde,min(b.hora_inicio,fin))
                desde=max(desde,b.hora_fin)
                if desde>=fin: return
            if desde<fin: agregar(dia,desde,fin)
        def agregar(dia,inicio,fin):
            b,_=DisponibilidadProfesor.objects.get_or_create(profesor=p,periodo=periodo,dia=dia,hora_inicio=inicio,hora_fin=fin,defaults={"activo":False})
            if not b.activo: b.activo=True;b.full_clean();b.save()
        for h in Horario.objects.filter(oferta__profesor=p,oferta__periodo=periodo): completar(h.dia,h.hora_inicio,h.hora_fin)
        def total():
            return sum((Decimal(microsegundos_horario(b.hora_inicio,b.hora_fin))/Decimal("3600000000") for b in DisponibilidadProfesor.objects.filter(profesor=p,periodo=periodo,activo=True)),Decimal(0))
        for dia in ["LU","MA","MI","JU","VI"]:
            if total()>=asignadas+2: break
            completar(dia,time(9),time(13))
        if total()<asignadas: raise CommandError(f"No se pudo cubrir la carga demo de {p}.")
    planes=PlanEstudioAsignatura.objects.filter(activo=True,programa__codigo__in=PROGRAMAS,programa__activo=True,asignatura__activo=True,asignatura__codigo__in=OPCIONES).select_related("programa","semestre","asignatura").order_by("pk")
    for plan in planes:
        grupo=Grupo.objects.filter(programa=plan.programa,semestre=plan.semestre,centro_tutorial=centro,periodo=periodo,activo=True).order_by("pk").first()
        if grupo is None:
            grupo,_=Grupo.objects.get_or_create(codigo=f"DEMO-{plan.semestre.numero:02d} G1",programa=plan.programa,semestre=plan.semestre,centro_tutorial=centro,periodo=periodo,defaults={"activo":True})
        modalidad=Modalidad.objects.get(codigo={"DIGI001":"VIR","ARQ01":"HIB"}.get(plan.asignatura.codigo,"PRE"),activo=True)
        for n in OPCIONES[plan.asignatura.codigo]:
            p=profesores[n]
            candidatas=OfertaAcademica.objects.filter(asignatura=plan.asignatura,profesor=p,periodo=periodo,modalidad=modalidad,activo=True).order_by("pk")
            # No agregar grupos nuevos a una oferta ya programada.
            oferta=candidatas.filter(grupos=grupo).first() or candidatas.filter(horarios__isnull=True).first()
            if oferta is None: oferta=OfertaAcademica.objects.create(asignatura=plan.asignatura,profesor=p,periodo=periodo,modalidad=modalidad)
            OfertaGrupo.objects.get_or_create(oferta=oferta,grupo=grupo,defaults={"cupos":30})
    comando.stdout.write("Enriquecimiento FICTICIO/DEMO completado. Horarios existentes intactos.")
