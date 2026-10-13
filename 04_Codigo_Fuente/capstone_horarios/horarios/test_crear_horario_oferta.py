from datetime import time
from decimal import Decimal
from io import StringIO
import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from academico.models import Asignatura, Aula, CargaDocente, DisponibilidadProfesor, PlanEstudioAsignatura, Profesor, Sede
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo
from .services import calcular_horas_planificadas, calcular_horas_pendientes


class CrearHorarioOfertaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo", stdout=StringIO())
        cls.usuario = get_user_model().objects.create_superuser(username="crear_oferta_prueba", password="Prueba123!")
        cls.grupo = Grupo.objects.select_related("programa__facultad").get(programa__codigo="ING-INF", semestre__numero=5, codigo="05PD G1")
        cls.oferta = OfertaAcademica.objects.select_related("profesor", "periodo", "modalidad", "asignatura").get(asignatura__codigo="PROGWEB01")
        cls.aula = Aula.objects.get(codigo="A-101")
        cls.filtros = {"centro": cls.grupo.centro_tutorial_id, "facultad": cls.grupo.programa.facultad_id,
            "programa": cls.grupo.programa_id, "periodo": cls.grupo.periodo_id, "semestre": cls.grupo.semestre_id, "modalidad": cls.oferta.modalidad_id, "sede": cls.aula.sede_id}

    def setUp(self):
        self.client.force_login(self.usuario)

    def crear(self, **cambios):
        datos = {"oferta_id": self.oferta.pk, "aula_id": self.aula.pk, "dia": "JU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        datos.update(cambios)
        return self.client.post(reverse("crear_horario_oferta") + "?" + urlencode(self.filtros), json.dumps(datos), content_type="application/json")

    def detalle(self, filtros=None):
        return self.client.get(reverse("detalle_oferta_calendario", args=[self.oferta.pk]), filtros or self.filtros)

    def assert_rechazado(self, response, cantidad, status=400):
        self.assertEqual(response.status_code, status)
        self.assertIn("errors", response.json())
        self.assertEqual(Horario.objects.count(), cantidad)

    def test_creacion_valida(self):
        cantidad = Horario.objects.count()
        response = self.crear()
        self.assertEqual(response.status_code, 201)
        datos = response.json()
        horario = Horario.objects.get(pk=datos["horario_id"])
        self.assertEqual(horario.oferta_id, self.oferta.pk)
        self.assertEqual(horario.aula_id, self.aula.pk)
        self.assertEqual((horario.dia, horario.hora_inicio, horario.hora_fin), ("JU", time(8), time(10)))
        self.assertEqual(Horario.objects.count(), cantidad + 1)
        self.assertEqual(datos["event"]["id"], str(horario.pk))
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["event"]["extendedProps"]["profesor"], "Laura Méndez")

    def test_exige_autenticacion(self):
        self.client.logout()
        self.assert_rechazado(self.crear(), Horario.objects.count(), 401)

    def test_exige_permiso_add(self):
        usuario = get_user_model().objects.create_user(username="lector_creacion")
        usuario.user_permissions.add(Permission.objects.get(codename="view_horario"))
        self.client.force_login(usuario)
        self.assert_rechazado(self.crear(), Horario.objects.count(), 403)
        self.assertNotContains(self.client.get(reverse("planificacion"), self.filtros), ' offer-drag-card')

    def test_oferta_inexistente(self):
        self.assert_rechazado(self.crear(oferta_id=999999), Horario.objects.count(), 404)

    def test_aula_inexistente(self):
        self.assert_rechazado(self.crear(aula_id=999999), Horario.objects.count(), 404)

    def test_hora_final_igual(self):
        self.assert_rechazado(self.crear(hora_fin="08:00"), Horario.objects.count())

    def test_hora_final_anterior(self):
        self.assert_rechazado(self.crear(hora_fin="07:00"), Horario.objects.count())

    def test_conflicto_profesor(self):
        response = self.crear(dia="VI", hora_inicio="14:00", hora_fin="16:00")
        self.assert_rechazado(response, Horario.objects.count())
        self.assertIn("ya tiene una asignación", response.json()["errors"]["oferta"][0])

    def test_conflicto_aula(self):
        grupo = Grupo.objects.get(programa=self.grupo.programa, semestre=self.grupo.semestre, codigo="05PD G2")
        oferta = OfertaAcademica.objects.create(asignatura=self.oferta.asignatura,
            profesor=Profesor.objects.get(identificacion="DOC-DEMO-002"), periodo=self.oferta.periodo, modalidad=self.oferta.modalidad)
        OfertaGrupo.objects.create(oferta=oferta, grupo=grupo, cupos=10)
        Horario.objects.create(oferta=oferta, sede=self.aula.sede, aula=self.aula, dia="DO", hora_inicio=time(12), hora_fin=time(14))
        cantidad = Horario.objects.count()
        response = self.crear(dia="DO", hora_inicio="12:00", hora_fin="14:00")
        self.assert_rechazado(response, cantidad)
        self.assertIn("El aula", response.json()["errors"]["aula"][0])

    def test_conflicto_grupo(self):
        response = self.crear(dia="MI", hora_inicio="10:00", hora_fin="12:00")
        self.assert_rechazado(response, Horario.objects.count())
        self.assertIn("El grupo", response.json()["errors"]["oferta"][0])

    def test_error_no_crea_relaciones(self):
        cantidades = (Horario.objects.count(), OfertaAcademica.objects.count(), OfertaGrupo.objects.count(), Grupo.objects.count(), Profesor.objects.count())
        response = self.crear(dia="LU")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(cantidades, (Horario.objects.count(), OfertaAcademica.objects.count(), OfertaGrupo.objects.count(), Grupo.objects.count(), Profesor.objects.count()))

    def test_transversal_conserva_grupos(self):
        oferta = OfertaAcademica.objects.get(asignatura__codigo="COMP001")
        grupos = set(oferta.grupos.values_list("pk", flat=True))
        filtros = dict(self.filtros, semestre=Grupo.objects.get(programa__codigo="ING-INF", semestre__numero=1).semestre_id)
        datos = {"oferta_id": oferta.pk, "aula_id": self.aula.pk, "dia": "MI", "hora_inicio": "14:00", "hora_fin": "16:00"}
        response = self.client.post(reverse("crear_horario_oferta") + "?" + urlencode(filtros), json.dumps(datos), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(oferta.grupos.values_list("pk", flat=True)), grupos)
        self.assertEqual({g["id"] for g in response.json()["event"]["extendedProps"]["grupos"]}, grupos)
        self.assertEqual(calcular_horas_planificadas(oferta.profesor, oferta.periodo), Decimal("4"))

    def test_panel_identifica_ofertas_arrastrables(self):
        response = self.client.get(reverse("planificacion"), self.filtros)
        self.assertContains(response, f'data-oferta-id="{self.oferta.pk}"')
        self.assertContains(response, "Arrastrar al calendario o")
        self.assertNotContains(response, 'id="crear-horario-modal"')
        self.assertContains(response, "calendario.js")

    def test_asignatura_sin_oferta_no_arrastrable(self):
        asignatura = Asignatura.objects.create(codigo="SIN-OFERTA-DRAG", nombre="Asignatura sin oferta")
        PlanEstudioAsignatura.objects.create(programa=self.grupo.programa, semestre=self.grupo.semestre, asignatura=asignatura, creditos=2)
        response = self.client.get(reverse("planificacion"), self.filtros)
        contenido = response.content.decode()
        posicion = contenido.index("SIN-OFERTA-DRAG")
        tarjeta = contenido[posicion:contenido.index("</details>", posicion)]
        self.assertIn("Sin profesor asignado", tarjeta)
        self.assertNotIn("offer-drag-card", tarjeta)

    def test_multiples_ofertas_se_muestran_por_separado(self):
        otra = OfertaAcademica.objects.create(asignatura=self.oferta.asignatura,
            profesor=Profesor.objects.get(identificacion="DOC-DEMO-002"), periodo=self.oferta.periodo, modalidad=self.oferta.modalidad)
        OfertaGrupo.objects.create(oferta=otra, grupo=self.grupo, cupos=10)
        tercera = OfertaAcademica.objects.create(asignatura=self.oferta.asignatura,
            profesor=self.oferta.profesor, periodo=self.oferta.periodo, modalidad=self.oferta.modalidad)
        OfertaGrupo.objects.create(oferta=tercera, grupo=self.grupo, cupos=10)
        response = self.client.get(reverse("planificacion"), self.filtros)
        for oferta in [self.oferta, otra, tercera]:
            self.assertContains(response, f'data-oferta-id="{oferta.pk}"', count=1)

    def test_actualiza_horas_planificadas(self):
        antes = calcular_horas_planificadas(self.oferta.profesor, self.oferta.periodo)
        self.assertEqual(self.crear().status_code, 201)
        self.assertEqual(calcular_horas_planificadas(self.oferta.profesor, self.oferta.periodo), antes + Decimal("2"))
        self.assertEqual(Decimal(self.detalle().json()["horas_planificadas"]), antes + Decimal("2"))

    def test_actualiza_horas_pendientes(self):
        antes = calcular_horas_pendientes(self.oferta.profesor, self.oferta.periodo)
        self.assertEqual(self.crear().status_code, 201)
        self.assertEqual(calcular_horas_pendientes(self.oferta.profesor, self.oferta.periodo), antes - Decimal("2"))
        self.assertEqual(Decimal(self.detalle().json()["horas_pendientes"]), antes - Decimal("2"))

    def test_ausencia_carga_rechazada(self):
        CargaDocente.objects.all().delete()
        self.assertEqual(self.crear().status_code, 400)
        detalle = self.detalle().json()
        self.assertIsNone(detalle["horas_asignadas"])
        self.assertIsNone(detalle["horas_pendientes"])

    def test_ausencia_disponibilidad_rechazada(self):
        DisponibilidadProfesor.objects.all().delete()
        self.assertEqual(self.crear().status_code, 400)
        self.assertEqual(self.detalle().json()["disponibilidad"], [])

    def test_post_csrf_y_hora_final_obligatoria(self):
        self.assertEqual(self.client.get(reverse("crear_horario_oferta")).status_code, 405)
        self.assert_rechazado(self.crear(hora_fin=""), Horario.objects.count())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        url = reverse("crear_horario_oferta") + "?" + urlencode(self.filtros)
        datos = {"oferta_id": self.oferta.pk, "aula_id": self.aula.pk, "dia": "JU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        self.assertEqual(client.post(url, json.dumps(datos), content_type="application/json").status_code, 403)
        client.get(reverse("planificacion"), self.filtros)
        response = client.post(url, json.dumps(datos), content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 201)

    def test_aula_respeta_sede_y_estado(self):
        sede = Sede.objects.get(codigo="SEDE-NORTE")
        detalle = self.detalle(dict(self.filtros, sede=sede.pk)).json()
        self.assertEqual({a["id"] for a in detalle["aulas"]}, set(Aula.objects.filter(sede=sede, activo=True).values_list("pk", flat=True)))
        datos = {"oferta_id": self.oferta.pk, "aula_id": self.aula.pk, "dia": "JU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        url = reverse("crear_horario_oferta") + "?" + urlencode(dict(self.filtros, sede=sede.pk))
        self.assert_rechazado(self.client.post(url, json.dumps(datos), content_type="application/json"), Horario.objects.count(), 404)
        self.aula.activo = False
        self.aula.save()
        self.assert_rechazado(self.crear(), Horario.objects.count(), 404)

    def test_oferta_inactiva_o_fuera_contexto(self):
        otra = OfertaAcademica.objects.get(asignatura__codigo="COMP001")
        self.assert_rechazado(self.crear(oferta_id=otra.pk), Horario.objects.count(), 404)
        self.oferta.activo = False
        self.oferta.save()
        self.assert_rechazado(self.crear(), Horario.objects.count(), 404)

    def test_nombres_enviados_no_cambian_oferta_real(self):
        response = self.crear(profesor="Inventado", asignatura="Inventada", grupos=[999])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["event"]["title"], "Programación Web")
        self.assertEqual(response.json()["event"]["extendedProps"]["profesor"], "Laura Méndez")

    def test_json_invalido_no_crea(self):
        url = reverse("crear_horario_oferta") + "?" + urlencode(self.filtros)
        for datos in ["no-json", "[]", "{}"]:
            with self.subTest(datos=datos):
                cantidad = Horario.objects.count()
                self.assert_rechazado(self.client.post(url, datos, content_type="application/json"), cantidad)


    def test_tarjeta_completa_y_confirmacion_de_movimiento(self):
        response = self.client.get(reverse("planificacion"), self.filtros)
        self.assertContains(response, 'class="subject-offer-option teacher-compact-card offer-drag-card"')
        self.assertNotContains(response, "offer-drag-handle")
        self.assertContains(response, "doble clic o Enter para ver detalle.")
        self.assertContains(response, "calendar-context-menu")
        self.assertContains(response, 'id="mover-horario-modal"')
        self.assertContains(response, "¿Está seguro de realizar los cambios?")
        self.assertContains(response, "Confirmar cambios")

    def test_creador_sin_permiso_change_no_tiene_modal_movimiento(self):
        usuario = get_user_model().objects.create_user(username="creador_sin_change")
        usuario.user_permissions.add(Permission.objects.get(codename="view_horario"), Permission.objects.get(codename="add_horario"))
        self.client.force_login(usuario)
        response = self.client.get(reverse("planificacion"), self.filtros)
        self.assertNotContains(response, 'id="crear-horario-modal"')
        self.assertNotContains(response, 'id="mover-horario-modal"')
        self.assertContains(response, " offer-drag-card")
