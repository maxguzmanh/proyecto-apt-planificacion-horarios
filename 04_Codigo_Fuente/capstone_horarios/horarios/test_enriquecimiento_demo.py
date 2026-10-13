from io import StringIO
from decimal import Decimal
from django.apps import apps
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from academico.models import Profesor,PeriodoAcademico,CargaDocente,DisponibilidadProfesor,PlanEstudioAsignatura
from .models import Horario,OfertaAcademica,OfertaGrupo,Grupo
from .services import calcular_horas_planificadas,microsegundos_horario,intervalo_cubierto,obtener_panel_academico
from .management.demo import OPCIONES,PROGRAMAS

class EnriquecimientoDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo",stdout=StringIO())
        cls.antes=list(Horario.objects.order_by("pk").values())
        call_command("cargar_datos_demo",enriquecer=True,stdout=StringIO())
        cls.periodo=PeriodoAcademico.objects.get(codigo="01-2026")
    def estado(self):
        return {m._meta.label:list(m.objects.order_by("pk").values()) for m in apps.get_models() if m._meta.app_label in ("academico","horarios")}
    def test_idempotencia(self):
        antes=self.estado();call_command("cargar_datos_demo",enriquecer=True,stdout=StringIO());self.assertEqual(antes,self.estado())
    def test_horarios_intactos(self): self.assertEqual(self.antes,list(Horario.objects.order_by("pk").values()))
    def test_coherencia_docente(self):
        for p in Profesor.objects.filter(identificacion__startswith="DOC-DEMO-"):
            c=CargaDocente.objects.get(profesor=p,periodo=self.periodo,activo=True)
            total=sum((Decimal(microsegundos_horario(b.hora_inicio,b.hora_fin))/Decimal("3600000000") for b in DisponibilidadProfesor.objects.filter(profesor=p,periodo=self.periodo,activo=True)),Decimal(0))
            self.assertLessEqual(calcular_horas_planificadas(p,self.periodo),c.horas_asignadas);self.assertLessEqual(c.horas_asignadas,total)
    def test_cobertura(self):
        for h in Horario.objects.all():
            bloques=DisponibilidadProfesor.objects.filter(profesor=h.oferta.profesor,periodo=h.oferta.periodo,dia=h.dia,activo=True)
            self.assertTrue(intervalo_cubierto(h.hora_inicio,h.hora_fin,bloques));h.full_clean()
    def test_todos_planes_con_oferta(self):
        for plan in PlanEstudioAsignatura.objects.filter(activo=True,programa__codigo__in=PROGRAMAS,asignatura__codigo__in=OPCIONES):
            self.assertTrue(OfertaAcademica.objects.filter(activo=True,periodo=self.periodo,asignatura=plan.asignatura,grupos__programa=plan.programa,grupos__semestre=plan.semestre).exists())
    def test_multiples_opciones(self):
        for codigo,n in [("BD01",2),("DIGI001",3)]:
            self.assertGreaterEqual(OfertaAcademica.objects.filter(asignatura__codigo=codigo,activo=True).values("profesor_id").distinct().count(),n)
    def test_alternativas_no_crean_horarios(self):
        self.assertEqual(Horario.objects.count(),len(self.antes));self.assertTrue(OfertaAcademica.objects.filter(horarios__isnull=True).exists())
    def test_panel_multiples_tarjetas(self):
        g=Grupo.objects.select_related("programa","centro_tutorial","semestre").get(programa__codigo="ING-INF",semestre__numero=5,codigo="05PD G1")
        panel=obtener_panel_academico(g.programa,g.semestre,g.centro_tutorial,self.periodo)
        tarjeta=next(t for t in panel if t["plan"].asignatura.codigo=="BD01")
        self.assertEqual(len(tarjeta["profesores"]),2)
    def test_relaciones_compatibles(self):
        for og in OfertaGrupo.objects.filter(oferta__profesor__identificacion__startswith="DOC-DEMO-",oferta__periodo=self.periodo):
            self.assertEqual(og.grupo.periodo_id,self.periodo.pk)
            self.assertTrue(PlanEstudioAsignatura.objects.filter(programa=og.grupo.programa,semestre=og.grupo.semestre,asignatura=og.oferta.asignatura,activo=True).exists())
    def test_preserva_datos_manuales(self):
        p=Profesor.objects.create(identificacion="DOC-MANUAL",nombre="Prueba",apellido="Manual")
        c=CargaDocente.objects.create(profesor=p,periodo=self.periodo,horas_asignadas=9)
        call_command("cargar_datos_demo",enriquecer=True,stdout=StringIO());c.refresh_from_db();self.assertEqual(c.horas_asignadas,9)
    def test_codigos_en_filtros(self):
        u=get_user_model().objects.create_user(username="filtro_demo");self.client.force_login(u)
        g=Grupo.objects.get(programa__codigo="ING-INF",semestre__numero=1)
        sedes=self.client.get(reverse("cargar_sedes"),{"centro":g.centro_tutorial_id}).json()
        self.assertTrue(any(s["codigo"]=="SEDE-VIR" for s in sedes))
        modos=self.client.get(reverse("cargar_modalidades"),{"centro":g.centro_tutorial_id,"programa":g.programa_id}).json()
        self.assertTrue(any(s["codigo"]=="VIR" for s in modos))

    def test_renderizado_multiples_tarjetas(self):
        from academico.models import Sede,Modalidad
        u=get_user_model().objects.create_superuser(username="panel_enriquecido",password="demo")
        self.client.force_login(u)
        g=Grupo.objects.select_related("programa__facultad").get(programa__codigo="ING-INF",semestre__numero=5,codigo="05PD G1")
        r=self.client.get(reverse("planificacion"),{"centro":g.centro_tutorial_id,"facultad":g.programa.facultad_id,"programa":g.programa_id,"modalidad":Modalidad.objects.get(codigo="PRE").pk,"sede":Sede.objects.get(codigo="SEDE-ACA").pk,"periodo":self.periodo.pk,"semestre":g.semestre_id})
        self.assertEqual(r.status_code,200)
        self.assertContains(r,"Profesores disponibles");self.assertContains(r,"Laura Méndez");self.assertContains(r,"Diego Herrera")
        for o in OfertaAcademica.objects.filter(asignatura__codigo="BD01",grupos=g,activo=True): self.assertContains(r,f'data-oferta-id="{o.pk}"')
