from datetime import time
from io import StringIO
import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from academico.models import Aula, CargaDocente, DisponibilidadProfesor, Profesor, Sede
from .calendario import horarios_del_contexto, resolver_contexto_calendario, serializar_evento
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo


class CalendarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo", stdout=StringIO())
        cls.usuario = get_user_model().objects.create_superuser(username="calendario_prueba", password="Prueba123!")
        cls.grupo = Grupo.objects.select_related("programa__facultad").get(
            programa__codigo="ING-INF", semestre__numero=5, codigo="05PD G1",
        )
        cls.horario = Horario.objects.select_related("oferta__profesor", "oferta__asignatura", "aula").get(oferta__asignatura__codigo="PROGWEB01")
        cls.filtros = {"centro": str(cls.grupo.centro_tutorial_id), "facultad": str(cls.grupo.programa.facultad_id),
            "programa": str(cls.grupo.programa_id), "periodo": str(cls.grupo.periodo_id), "semestre": str(cls.grupo.semestre_id), "modalidad": str(cls.horario.oferta.modalidad_id), "sede": str(cls.horario.aula.sede_id)}

    def setUp(self):
        self.client.force_login(self.usuario)

    def mover(self, dia="JU", inicio="08:00:00", fin="10:00:00", **extra):
        return self.client.post(reverse("mover_horario"), json.dumps({
            "horario_id": self.horario.pk, "dia": dia, "hora_inicio": inicio, "hora_fin": fin, **extra,
        }), content_type="application/json")

    def comprobar_sin_cambios(self):
        self.horario.refresh_from_db()
        self.assertEqual((self.horario.dia, self.horario.hora_inicio, self.horario.hora_fin), ("LU", time(8), time(10)))

    def test_eventos_requieren_autenticacion(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("eventos_calendario"), self.filtros).status_code, 401)

    def test_eventos_requieren_permiso(self):
        usuario = get_user_model().objects.create_user(username="sin_permiso_eventos")
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("eventos_calendario"), self.filtros).status_code, 403)

    def test_eventos_respetan_contexto_y_grupo(self):
        response = self.client.get(reverse("eventos_calendario"), dict(self.filtros, grupo=self.grupo.pk))
        self.assertEqual(response.status_code, 200)
        ids = {int(e["id"]) for e in response.json()}
        esperados = set(Horario.objects.filter(oferta__grupos__programa=self.grupo.programa, oferta__grupos__semestre=self.grupo.semestre,
            oferta__modalidad_id=self.filtros["modalidad"], aula__sede_id=self.filtros["sede"]).values_list("pk", flat=True))
        self.assertEqual(ids, esperados)
        self.assertEqual(len(response.json()), len(ids))

    def test_eventos_respetan_sede(self):
        sede = Sede.objects.get(codigo="SEDE-NORTE")
        response = self.client.get(reverse("eventos_calendario"), dict(self.filtros, sede=sede.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_serializacion_y_proyeccion(self):
        datos = self.client.get(reverse("eventos_calendario"), self.filtros).json()
        evento = next(e for e in datos if e["id"] == str(self.horario.pk))
        self.assertEqual(evento["start"], "2000-01-03T08:00:00")
        self.assertEqual(evento["end"], "2000-01-03T10:00:00")
        props = evento["extendedProps"]
        self.assertEqual(props["asignatura"], "Programación Web")
        self.assertEqual(props["profesor"], "Laura Méndez")
        self.assertEqual(props["aula"], "Sala 101")
        self.assertEqual(props["modalidad"], "Presencial")
        self.assertEqual(props["dia"], "LU")
        self.assertEqual(props["hora_inicio"], "08:00:00")
        self.assertEqual(props["grupos"][0]["codigo"], "05PD G1")

    def test_mover_sin_carga_ni_disponibilidad_rechazado(self):
        CargaDocente.objects.all().delete()
        DisponibilidadProfesor.objects.all().delete()
        cantidad = Horario.objects.count()
        response = self.mover()
        self.assertEqual(response.status_code, 400)
        self.assertIn("disponibilidad", str(response.json()["errors"]).lower())
        self.comprobar_sin_cambios()
        self.assertEqual(Horario.objects.count(), cantidad)

    def test_conflicto_profesor_no_modifica_registro(self):
        blocker = Horario.objects.get(oferta__asignatura__codigo="ARQ01")
        blocker.aula = Aula.objects.get(codigo="A-201")
        blocker.save()
        response = self.mover("VI", "14:00:00", "16:00:00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("El profesor", response.json()["errors"]["oferta"][0])
        self.comprobar_sin_cambios()

    def test_conflicto_aula_no_modifica_registro(self):
        grupo = Grupo.objects.get(programa=self.grupo.programa, semestre=self.grupo.semestre, codigo="05PD G2")
        oferta = OfertaAcademica.objects.create(asignatura=self.horario.oferta.asignatura,
            profesor=Profesor.objects.get(identificacion="DOC-DEMO-002"), periodo=self.grupo.periodo,
            modalidad=self.horario.oferta.modalidad)
        OfertaGrupo.objects.create(oferta=oferta, grupo=grupo, cupos=10)
        Horario.objects.create(oferta=oferta, sede=self.horario.sede, aula=self.horario.aula, dia="DO", hora_inicio=time(12), hora_fin=time(14))
        response = self.mover("DO", "12:00:00", "14:00:00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("El aula", response.json()["errors"]["aula"][0])
        self.comprobar_sin_cambios()

    def test_conflicto_grupo_no_modifica_registro(self):
        response = self.mover("MI", "10:00:00", "12:00:00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("El grupo", response.json()["errors"]["oferta"][0])
        self.comprobar_sin_cambios()

    def test_sin_permiso_no_puede_mover(self):
        usuario = get_user_model().objects.create_user(username="sin_permiso_mover")
        self.client.force_login(usuario)
        self.assertEqual(self.mover().status_code, 403)
        self.comprobar_sin_cambios()

    def test_mover_requiere_autenticacion(self):
        self.client.logout()
        self.assertEqual(self.mover().status_code, 401)
        self.comprobar_sin_cambios()

    def test_edicion_excluye_el_propio_horario(self):
        self.assertEqual(self.mover("LU", "08:00:00", "10:00:00").status_code, 200)
        self.assertEqual(self.mover("LU", "08:30:00", "10:30:00").status_code, 200)
        self.horario.refresh_from_db()
        self.assertEqual(self.horario.hora_inicio, time(8, 30))

    def test_solo_post_y_csrf(self):
        self.assertEqual(self.client.get(reverse("mover_horario")).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        data = {"horario_id": self.horario.pk, "dia": "JU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        self.assertEqual(client.post(reverse("mover_horario"), json.dumps(data), content_type="application/json").status_code, 403)
        client.get(reverse("planificacion"), self.filtros)
        response = client.post(reverse("mover_horario"), json.dumps(data), content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_json_y_valores_invalidos(self):
        for payload in ["no json", "[]", json.dumps({"horario_id": self.horario.pk, "dia": "XX", "hora_inicio": "error", "hora_fin": "10:00"})]:
            with self.subTest(payload=payload):
                response = self.client.post(reverse("mover_horario"), payload, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.comprobar_sin_cambios()

    def test_no_permite_resize(self):
        self.assertEqual(self.mover(fin="11:00:00").status_code, 400)
        self.comprobar_sin_cambios()

    def test_version_desactualizada(self):
        response = self.mover(original={"dia": "MA", "hora_inicio": "08:00:00", "hora_fin": "10:00:00"})
        self.assertEqual(response.status_code, 409)
        self.comprobar_sin_cambios()

    def test_contexto_invalido(self):
        self.assertEqual(self.client.get(reverse("eventos_calendario")).status_code, 400)
        self.assertEqual(self.client.get(reverse("eventos_calendario"), dict(self.filtros, semestre="x")).status_code, 400)
        otro_grupo = Grupo.objects.get(programa__codigo="ADM-EMP", semestre__numero=1)
        self.assertEqual(self.client.get(reverse("eventos_calendario"), dict(self.filtros, programa=otro_grupo.programa_id)).status_code, 404)

    def test_inactivos_no_se_devuelven(self):
        self.horario.activo = False
        self.horario.save()
        ids = [e["id"] for e in self.client.get(reverse("eventos_calendario"), self.filtros).json()]
        self.assertNotIn(str(self.horario.pk), ids)
        self.assertEqual(self.mover().status_code, 404)

    def test_transversal_es_un_evento_y_consultas_constantes(self):
        grupo = Grupo.objects.get(programa__codigo="ING-INF", semestre__numero=1)
        contexto = resolver_contexto_calendario(dict(self.filtros, semestre=str(grupo.semestre_id), sede=str(Sede.objects.get(codigo="SEDE-NORTE").pk)))
        with CaptureQueriesContext(connection) as consultas:
            eventos = [serializar_evento(h) for h in horarios_del_contexto(**contexto)]
        self.assertEqual(len(consultas), 2)
        self.assertEqual(len(eventos), len({e["id"] for e in eventos}))
        evento = next(e for e in eventos if e["title"] == "Competencias Comunicativas")
        self.assertEqual(len(evento["extendedProps"]["grupos"]), 4)

    def test_plantilla_fullcalendar_sin_grilla_anterior(self):
        response = self.client.get(reverse("planificacion"), self.filtros)
        self.assertContains(response, 'id="uniplan-calendar"')
        self.assertContains(response, "fullcalendar@6.1.21")
        self.assertContains(response, reverse("eventos_calendario"))
        self.assertContains(response, reverse("mover_horario"))
        self.assertNotContains(response, 'class="weekly-calendar"')
