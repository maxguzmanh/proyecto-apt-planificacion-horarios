from datetime import time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from academico.models import Profesor,CargaDocente,DisponibilidadProfesor,PeriodoAcademico
from .models import Horario,OfertaGrupo
from .test_validacion_docente import DatosDocencia

class DashboardTests(DatosDocencia,TestCase):
    def setUp(self):
        self.crear_datos()
        OfertaGrupo.objects.create(oferta=self.oferta,grupo=self.grupo,cupos=10)
        OfertaGrupo.objects.create(oferta=self.otra_oferta,grupo=self.grupo,cupos=10)
        self.pendiente=Horario.objects.create(oferta=self.oferta,sede=self.aula.sede,dia="LU",hora_inicio=time(8),hora_fin=time(9))
        self.completo=Horario.objects.create(oferta=self.oferta,sede=self.aula.sede,aula=self.aula,dia="LU",hora_inicio=time(9),hora_fin=time(10))
        self.user=get_user_model().objects.create_user(username="planificador_dashboard")
        self.permisos("horarios.view_horario","horarios.change_horario")
        self.client.force_login(self.user)
    def permisos(self,*nombres):
        for n in nombres:
            app,codigo=n.split(".");self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app,codename=codigo))
    def get(self,**params): return self.client.get(reverse("inicio"),{"periodo":self.periodo.pk,**params})
    def test_autenticacion(self):
        self.client.logout();r=self.get();self.assertEqual(r.status_code,302);self.assertIn("login",r.url)
    def test_autorizado(self):
        r=self.get();self.assertEqual(r.status_code,200);self.assertContains(r,"Resumen operativo de la planificación académica.")
    def test_no_autorizado(self):
        self.user.user_permissions.clear();self.assertEqual(self.get().status_code,403)
    def test_profesor_solo_consulta_no_accede(self):
        self.user.user_permissions.clear();self.permisos("horarios.view_horario");self.assertEqual(self.get().status_code,403)
    def test_staff_sin_permisos_no_accede(self):
        self.user.user_permissions.clear();self.user.is_staff=True;self.user.save();self.assertEqual(self.get().status_code,403)
    def test_metricas_reales(self):
        c=self.get().context
        self.assertEqual(c["total_programas"],1);self.assertEqual(c["total_profesores"],2);self.assertEqual(c["total_aulas"],2);self.assertEqual(c["total_horarios"],2)
        self.assertEqual(c["total_pendientes"],1);self.assertEqual(c["total_ofertas_sin_horario"],1)
    def test_pendiente_detalle_y_enlace(self):
        r=self.get();self.assertContains(r,"Sede Prueba");self.assertContains(r,"Ver en planificación")
        self.assertIn(f"sede={self.aula.sede_id}",r.context["pendientes"][0]["url"])
    def test_oferta_con_horario_inactivo_se_considera_pendiente(self):
        self.pendiente.activo=False;self.pendiente.save();self.completo.activo=False;self.completo.save()
        self.assertEqual(self.get().context["total_ofertas_sin_horario"],2)
    def test_acciones_respetan_permisos(self):
        r=self.get();self.assertEqual([a["nombre"] for a in r.context["acciones"]],["Ir a Planificación"])
        self.permisos("academico.view_profesor","academico.view_aula")
        self.assertEqual({a["nombre"] for a in self.get().context["acciones"]},{"Ir a Planificación","Profesores","Aulas"})
    def test_dashboard_usa_iconos_y_paneles_alineados(self):
        r=self.get();self.assertGreaterEqual(r.content.decode().count('class="dashboard-icon '),10)
        self.assertContains(r,"dashboard-kpi-heading",count=4)
    def test_sin_pendientes(self):
        self.pendiente.aula=self.aula;self.pendiente.save()
        self.assertContains(self.get(),"Todos los horarios tienen aula asignada.")
    def test_estado_docente_ausencias_reales(self):
        CargaDocente.objects.filter(profesor=self.otro_profesor).delete()
        DisponibilidadProfesor.objects.filter(profesor=self.otro_profesor).delete()
        c=self.get().context;estados={e["nombre"]:e["valor"] for e in c["estados"]}
        self.assertEqual(estados["Profesores sin carga"],1);self.assertEqual(estados["Profesores sin disponibilidad"],1)
        self.assertIsNone(c["docentes_atencion"][0]["pendientes"])
    def test_carga_completa_y_cerca_limite(self):
        carga=CargaDocente.objects.get(profesor=self.profesor,periodo=self.periodo);carga.horas_asignadas=2.5;carga.save()
        self.assertContains(self.get(),"Carga cercana al límite")
        carga.horas_asignadas=2;carga.save();self.assertContains(self.get(),"Carga completa")
    def test_sobrecarga_es_problema_real(self):
        carga=CargaDocente.objects.get(profesor=self.profesor,periodo=self.periodo);carga.horas_asignadas=1;carga.save()
        self.assertContains(self.get(),"dashboard-item-danger");self.assertContains(self.get(),"Carga excedida")
    def test_periodo_no_mezcla_cargas(self):
        r=self.get(periodo=self.otro_periodo.pk);self.assertEqual(len(r.context["pendientes"]),0)
        self.assertEqual({e["nombre"]:e["valor"] for e in r.context["estados"]}["Profesores sin carga"],2)
    def test_periodo_invalido(self): self.assertEqual(self.get(periodo=99999).status_code,404)
    def test_sin_periodos_activos(self):
        PeriodoAcademico.objects.all().update(activo=False)
        r=self.client.get(reverse("inicio"));self.assertEqual(r.status_code,200);self.assertContains(r,"No hay un periodo activo")
    def test_sin_n_mas_uno(self):
        with CaptureQueriesContext(connection) as inicial:self.get()
        for n in range(4):
            p=Profesor.objects.create(identificacion=f"DOC-DASH-{n}",nombre="Docente",apellido=f"Prueba {n}")
            self.condiciones(p,self.periodo);o=self.nueva_oferta(p);OfertaGrupo.objects.create(oferta=o,grupo=self.grupo,cupos=10)
        with CaptureQueriesContext(connection) as despues:self.get()
        self.assertEqual(len(inicial),len(despues))
    def test_listados_limitados(self):
        for n in range(8):Profesor.objects.create(identificacion=f"DOC-FALTA-{n}",nombre="Ficticio",apellido=str(n))
        c=self.get().context;self.assertLessEqual(len(c["docentes_atencion"]),6);self.assertLessEqual(len(c["pendientes"]),5);self.assertLessEqual(len(c["ofertas_pendientes"]),5)
