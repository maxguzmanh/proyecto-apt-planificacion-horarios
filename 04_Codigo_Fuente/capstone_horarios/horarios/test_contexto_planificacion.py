from datetime import time
from io import StringIO
import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from academico.models import Aula, CentroTutorial, Modalidad, Sede
from .calendario import resolver_contexto_calendario
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo
from .services import obtener_panel_academico


class ContextoPlanificacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo", stdout=StringIO())
        cls.usuario = get_user_model().objects.create_superuser(username="contexto_prueba", password="Prueba123!")
        cls.horario = Horario.objects.select_related("oferta__profesor", "oferta__periodo", "oferta__asignatura", "oferta__modalidad", "aula__sede").get(oferta__asignatura__codigo="PROGWEB01")
        cls.grupo = cls.horario.oferta.grupos.select_related("programa__facultad").get()
        cls.filtros = {"centro": str(cls.grupo.centro_tutorial_id), "facultad": str(cls.grupo.programa.facultad_id),
            "programa": str(cls.grupo.programa_id),
            "sede": str(cls.horario.aula.sede_id), "periodo": str(cls.grupo.periodo_id), "semestre": str(cls.grupo.semestre_id)}

    def setUp(self):
        self.client.force_login(self.usuario)

    def crear(self, filtros=None, aula=None, dia="JU", inicio="08:00", fin="10:00"):
        return self.client.post(reverse("crear_horario_oferta") + "?" + urlencode(filtros or self.filtros),
            json.dumps({"oferta_id": self.horario.oferta_id, "aula_id": (aula or self.horario.aula).pk,
                "dia": dia, "hora_inicio": inicio, "hora_fin": fin}), content_type="application/json")

    def test_sede_obligatoria_en_vista_eventos_y_creacion(self):
        filtros = {k: v for k, v in self.filtros.items() if k != "sede"}
        response = self.client.get(reverse("planificacion"), filtros)
        self.assertFalse(response.context["filtros_completos"])
        self.assertNotContains(response, 'id="uniplan-calendar"')
        self.assertEqual(self.client.get(reverse("eventos_calendario"), filtros).status_code, 400)
        cantidad = Horario.objects.count()
        self.assertEqual(self.crear(filtros).status_code, 400)
        self.assertEqual(Horario.objects.count(), cantidad)

    def test_orden_filtros_sin_todas_sedes_ni_grupo(self):
        response = self.client.get(reverse("planificacion"), self.filtros)
        contenido = response.content.decode()
        posiciones = [contenido.index(f'id="{campo}"') for campo in ["centro", "sede", "facultad", "programa", "periodo", "semestre"]]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertNotContains(response, "Todas las sedes")
        self.assertNotContains(response, 'name="grupo"')
        self.assertNotContains(response, 'name="modalidad"')
        self.assertContains(response, 'id="sede" name="sede" class="form-select" required')
        self.assertContains(response, 'form="filtros-planificacion"')

    def test_sedes_dependen_del_centro(self):
        otro = CentroTutorial.objects.create(codigo="CT-OTRO", nombre="Otro Centro")
        sede = Sede.objects.create(codigo="OTRA-SEDE", nombre="Otra sede", centro_tutorial=otro)
        response = self.client.get(reverse("cargar_sedes"), {"centro": self.grupo.centro_tutorial_id})
        ids = {item["id"] for item in response.json()}
        self.assertNotIn(sede.pk, ids)
        self.assertEqual(ids, set(Sede.objects.filter(centro_tutorial=self.grupo.centro_tutorial, activo=True).values_list("pk", flat=True)))
        self.assertEqual(self.client.get(reverse("eventos_calendario"), dict(self.filtros, sede=sede.pk)).status_code, 404)

    def test_modal_aulas_solo_sede_y_post_manipulado_rechazado(self):
        response = self.client.get(reverse("detalle_oferta_calendario", args=[self.horario.oferta_id]), self.filtros)
        ids = {a["id"] for a in response.json()["aulas"]}
        self.assertEqual(ids, set(Aula.objects.filter(sede=self.horario.aula.sede, activo=True).values_list("pk", flat=True)))
        otra = Aula.objects.get(codigo="N-101")
        cantidad = Horario.objects.count()
        self.assertEqual(self.crear(aula=otra).status_code, 404)
        self.assertEqual(Horario.objects.count(), cantidad)

    def bloquear_en_otra_sede(self, otro_programa=False):
        grupo = Grupo.objects.get(programa__codigo="ING-IND", semestre__numero=1) if otro_programa else Grupo.objects.get(programa=self.grupo.programa, semestre=self.grupo.semestre, codigo="05PD G2")
        oferta = OfertaAcademica.objects.create(asignatura=self.horario.oferta.asignatura,
            profesor=self.horario.oferta.profesor, periodo=self.horario.oferta.periodo, modalidad=self.horario.oferta.modalidad)
        OfertaGrupo.objects.create(oferta=oferta, grupo=grupo, cupos=10)
        horario = Horario(oferta=oferta, sede=Sede.objects.get(codigo="SEDE-NORTE"), aula=Aula.objects.get(codigo="N-101"), dia="MI", hora_inicio=time(10), hora_fin=time(12))
        horario.full_clean()
        horario.save()
        return horario

    def test_conflicto_profesor_en_otra_sede(self):
        self.bloquear_en_otra_sede()
        cantidad = Horario.objects.count()
        response = self.crear(dia="MI", inicio="11:00", fin="13:00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("ya tiene una asignación", response.json()["errors"]["oferta"][0])
        self.assertEqual(Horario.objects.count(), cantidad)

    def test_conflicto_profesor_en_otro_programa(self):
        self.bloquear_en_otra_sede(otro_programa=True)
        response = self.crear(dia="MI", inicio="11:00", fin="13:00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("ya tiene una asignación", response.json()["errors"]["oferta"][0])

    def test_calendario_filtrado_no_limita_movimiento_ni_totales(self):
        bloque = self.bloquear_en_otra_sede(otro_programa=True)
        eventos = self.client.get(reverse("eventos_calendario"), self.filtros).json()
        self.assertNotIn(str(bloque.pk), [e["id"] for e in eventos])
        response = self.client.post(reverse("mover_horario"), json.dumps({
            "horario_id": self.horario.pk, "dia": "MI", "hora_inicio": "11:00", "hora_fin": "13:00",
        }), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.horario.refresh_from_db()
        self.assertEqual(self.horario.dia, "LU")
        contexto = resolver_contexto_calendario(self.filtros)
        tarjetas = obtener_panel_academico(contexto["programa"], contexto["semestre"], contexto["centro"], contexto["periodo"], sede=contexto["sede"])
        docente = next(d for t in tarjetas for d in t["profesores"] if d["profesor"].pk == self.horario.oferta.profesor_id)
        self.assertEqual(docente["horas_planificadas"], 6)
        self.assertEqual(len(docente["disponibilidad"]), 7)

    def test_periodos_por_contexto_sin_modalidad(self):
        datos = self.client.get(reverse("cargar_periodos"), self.filtros).json()
        self.assertIn(self.grupo.periodo_id, {p["id"] for p in datos})
        # URLs guardadas con modalidad dejan de recortar el contexto.
        self.assertEqual(self.client.get(reverse("cargar_periodos"), dict(self.filtros, modalidad="999999")).json(), datos)
        self.assertEqual(self.client.get(reverse("cargar_periodos"), {k: v for k, v in self.filtros.items() if k != "sede"}).json(), [])

    def test_semestres_despues_del_contexto(self):
        self.assertEqual(self.client.get(reverse("cargar_semestres"), {"programa": self.grupo.programa_id}).json(), [])
        datos = self.client.get(reverse("cargar_semestres"), self.filtros).json()
        self.assertEqual({s["numero"] for s in datos}, {1, 5})

    def test_contexto_muestra_presencial_e_hibrida(self):
        response = self.client.get(reverse("eventos_calendario"), self.filtros)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({e["extendedProps"]["modalidad"] for e in response.json()}, {"Presencial", "Híbrida"})
        oferta_hibrida = OfertaAcademica.objects.get(asignatura__codigo="ARQ01")
        datos = {"oferta_id": oferta_hibrida.pk, "aula_id": self.horario.aula_id, "dia": "JU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        response = self.client.post(reverse("crear_horario_oferta") + "?" + urlencode(self.filtros), json.dumps(datos), content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["event"]["extendedProps"]["modalidad"], "Híbrida")

    def test_virtual_exige_campus_explicito(self):
        grupo = Grupo.objects.get(programa__codigo="ING-INF", semestre__numero=1)
        filtros = dict(self.filtros, semestre=str(grupo.semestre_id), sede=str(Sede.objects.get(codigo="SEDE-VIR").pk))
        response = self.client.get(reverse("eventos_calendario"), filtros)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([e["title"] for e in response.json()], ["Competencias Digitales"])
        filtros.pop("sede")
        self.assertEqual(self.client.get(reverse("eventos_calendario"), filtros).status_code, 400)

    def test_modalidad_antigua_no_filtra_eventos(self):
        eventos = self.client.get(reverse("eventos_calendario"), self.filtros).json()
        self.assertEqual(self.client.get(reverse("eventos_calendario"), dict(self.filtros, modalidad="invalida")).json(), eventos)

    def test_ofertas_sin_horario_de_modalidades_compatibles(self):
        oferta = OfertaAcademica.objects.get(asignatura__codigo="ARQ01")
        # No depende de que la oferta ya tenga un Horario en esta sede.
        for horario in oferta.horarios.all():
            horario.delete()
        response = self.client.get(reverse("planificacion"), self.filtros)
        ofertas = [o.pk for t in response.context["asignaturas_semestre"] for d in t["profesores"] for o in d["ofertas"]]
        self.assertIn(oferta.pk, ofertas)

    def test_sedes_no_dependen_de_parametro_modalidad(self):
        datos = self.client.get(reverse("cargar_sedes"), self.filtros).json()
        self.assertIn("SEDE-VIR", {s["codigo"] for s in datos})
        self.assertEqual(self.client.get(reverse("cargar_sedes"), dict(self.filtros, modalidad="invalida")).json(), datos)

    def test_modalidad_real_preserva_compatibilidad_sede(self):
        filtros = dict(self.filtros, sede=Sede.objects.get(codigo="SEDE-VIR").pk)
        cantidad = Horario.objects.count()
        self.assertEqual(self.crear(filtros).status_code, 404)
        self.assertEqual(Horario.objects.count(), cantidad)

    def test_urls_renderizadas_sin_modalidad_antigua(self):
        response = self.client.get(reverse("planificacion"), dict(self.filtros, modalidad="999999"))
        self.assertNotContains(response, "modalidad=999999")
        self.assertNotIn("modalidad", response.context["filtros_query"])
        self.assertTrue(response.context["filtros_completos"])
