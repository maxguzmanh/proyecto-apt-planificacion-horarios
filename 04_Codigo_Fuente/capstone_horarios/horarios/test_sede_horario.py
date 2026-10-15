from datetime import time
from decimal import Decimal
import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from academico.models import Sede, Aula
from .models import Horario, OfertaGrupo
from .forms import HorarioAdminForm
from .test_validacion_docente import DatosDocencia
from .services import calcular_horas_planificadas


class SedeHorarioTests(DatosDocencia, TestCase):
    def setUp(self):
        self.crear_datos()
        OfertaGrupo.objects.create(oferta=self.oferta, grupo=self.grupo, cupos=10)
        self.otra_sede = Sede.objects.create(codigo="SEDE-OTRA", nombre="Sede Norte de Prueba", centro_tutorial=self.grupo.centro_tutorial)
        self.aula_norte = Aula.objects.create(codigo="A-NORTE", nombre="Aula Norte", sede=self.otra_sede)
        self.usuario = get_user_model().objects.create_superuser(username="sede_prueba", password="Prueba123!")
        self.client.force_login(self.usuario)
        self.filtros = {"centro": self.grupo.centro_tutorial_id, "facultad": self.grupo.programa.facultad_id,
            "programa": self.grupo.programa_id, "modalidad": self.modalidad.pk, "sede": self.aula.sede_id,
            "periodo": self.periodo.pk, "semestre": self.grupo.semestre_id}

    def pendiente(self):
        h = Horario(oferta=self.oferta, sede=self.aula.sede, dia="LU", hora_inicio=time(8), hora_fin=time(9))
        h.save()
        return h

    def asignar(self, h, aula, filtros=None):
        return self.client.post(reverse("asignar_aula_horario") + "?" + urlencode(filtros or self.filtros),
            json.dumps({"horario_id": h.pk, "aula_id": aula.pk}), content_type="application/json")

    def test_sede_obligatoria(self):
        h = Horario(oferta=self.oferta, dia="LU", hora_inicio=time(8), hora_fin=time(9))
        with self.assertRaises(ValidationError) as error: h.save()
        self.assertIn("sede", error.exception.message_dict)

    def test_pendiente_conserva_sede(self):
        h = self.pendiente(); h.refresh_from_db()
        self.assertEqual(h.sede_id, self.aula.sede_id)
        self.assertIsNone(h.aula_id)

    def test_pendiente_solo_aparece_en_su_sede(self):
        h = self.pendiente()
        propios = self.client.get(reverse("eventos_calendario"), self.filtros).json()
        ajenos = self.client.get(reverse("eventos_calendario"), dict(self.filtros, sede=self.otra_sede.pk)).json()
        self.assertEqual([e["id"] for e in propios], [str(h.pk)])
        self.assertEqual(ajenos, [])
        self.assertEqual(propios[0]["extendedProps"]["sede_id"], h.sede_id)
        self.assertEqual(propios[0]["classNames"], ["evento-pendiente"])

    def test_drop_guarda_sede_del_contexto_no_texto_cliente(self):
        datos = {"oferta_id": self.oferta.pk, "dia": "LU", "hora_inicio": "08:00", "hora_fin": "09:00", "sede": "Inventada"}
        response = self.client.post(reverse("crear_horario_oferta") + "?" + urlencode(self.filtros), json.dumps(datos), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        h = Horario.objects.get(pk=response.json()["horario_id"])
        self.assertEqual(h.sede_id, self.aula.sede_id)
        self.assertIsNone(h.aula_id)

    def test_asignar_misma_sede_y_estado_azul(self):
        h = self.pendiente(); response = self.asignar(h, self.aula)
        self.assertEqual(response.status_code, 200)
        h.refresh_from_db(); self.assertEqual(h.aula.sede_id, h.sede_id)
        self.assertEqual(response.json()["event"]["classNames"], ["evento-completo"])

    def test_modelo_rechaza_aula_de_otra_sede(self):
        h = self.pendiente(); h.aula = self.aula_norte
        with self.assertRaises(ValidationError): h.save()
        h.refresh_from_db(); self.assertIsNone(h.aula_id)

    def test_post_manipulado_otra_aula_y_otra_sede(self):
        h = self.pendiente()
        self.assertEqual(self.asignar(h, self.aula_norte).status_code, 404)
        self.assertEqual(self.asignar(h, self.aula_norte, dict(self.filtros, sede=self.otra_sede.pk)).status_code, 404)
        h.refresh_from_db(); self.assertEqual(h.sede_id, self.aula.sede_id); self.assertIsNone(h.aula_id)

    def test_selector_aulas_usa_sede_persistida(self):
        h = self.pendiente()
        response = self.client.get(reverse("aulas_horario_calendario", args=[h.pk]), self.filtros)
        self.assertEqual({a["id"] for a in response.json()["aulas"]}, {self.aula.pk, self.otra_aula.pk})
        self.assertEqual(self.client.get(reverse("aulas_horario_calendario", args=[h.pk]), dict(self.filtros, sede=self.otra_sede.pk)).status_code, 404)

    def test_cambiar_sede_con_aula_incompatible_rechazado(self):
        h = self.horario(); h.save(); h.sede = self.otra_sede
        with self.assertRaises(ValidationError): h.save()
        h.refresh_from_db(); self.assertEqual(h.sede_id, self.aula.sede_id)

    def test_conflicto_profesor_global_entre_sedes(self):
        self.pendiente()
        h = Horario(oferta=self.oferta, sede=self.otra_sede, dia="LU", hora_inicio=time(8), hora_fin=time(9))
        with self.assertRaisesMessage(ValidationError, "El profesor"): h.save()

    def test_conflicto_grupo_global_entre_sedes(self):
        self.pendiente(); OfertaGrupo.objects.create(oferta=self.otra_oferta, grupo=self.grupo, cupos=10)
        h = Horario(oferta=self.otra_oferta, sede=self.otra_sede, dia="LU", hora_inicio=time(8), hora_fin=time(9))
        with self.assertRaisesMessage(ValidationError, "El grupo"): h.save()

    def test_carga_global_y_disponibilidad_otra_sede(self):
        self.carga(1); self.pendiente()
        h = Horario(oferta=self.oferta, sede=self.otra_sede, dia="MA", hora_inicio=time(8), hora_fin=time(9))
        with self.assertRaisesMessage(ValidationError, "supera la carga"): h.save()
        self.disponibilidad([("LU", time(6), time(22))])
        with self.assertRaisesMessage(ValidationError, "no tiene disponibilidad registrada"): h.save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("1"))

    def test_formulario_admin_filtra_aulas_por_sede(self):
        form = HorarioAdminForm(data={"sede": self.aula.sede_id})
        self.assertEqual(set(form.fields["aula"].queryset.values_list("pk", flat=True)), {self.aula.pk, self.otra_aula.pk})
        self.assertTrue(form.fields["sede"].required)

    def test_movimiento_y_resize_no_cambian_sede(self):
        h = self.pendiente()
        for endpoint, datos in [("mover_horario", {"dia": "MA", "hora_inicio": "08:00", "hora_fin": "09:00"}),
                                ("redimensionar_horario", {"dia": "MA", "hora_inicio": "08:00", "hora_fin": "10:00"})]:
            response = self.client.post(reverse(endpoint), json.dumps({"horario_id": h.pk, **datos}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
            h.refresh_from_db(); self.assertEqual(h.sede_id, self.aula.sede_id)


class MigracionSedeTests(TransactionTestCase):
    reset_sequences = True
    anterior = ("horarios", "0002_alter_horario_aula")
    nueva = ("horarios", "0003_horario_sede")

    def setUp(self):
        executor = MigrationExecutor(connection); executor.migrate([self.anterior])
        self.apps = executor.loader.project_state([self.anterior]).apps
        Centro = self.apps.get_model("academico", "CentroTutorial")
        SedeHistorica = self.apps.get_model("academico", "Sede")
        centro = Centro.objects.create(codigo="CT-DEMO", nombre="Centro Demo")
        self.sede = SedeHistorica.objects.create(codigo="SEDE-ACA", nombre="Sede Académica", centro_tutorial=centro)
        otra = SedeHistorica.objects.create(codigo="SEDE-NORTE", nombre="Sede Norte", centro_tutorial=centro)
        AulaHistorica = self.apps.get_model("academico", "Aula")
        self.aulas = [AulaHistorica.objects.create(codigo=f"A-{i}", nombre=f"Aula {i}", sede=sede) for i, sede in enumerate([self.sede, otra])]
        profesor = self.apps.get_model("academico", "Profesor").objects.create(identificacion="DOC-DEMO-001", nombre="Laura", apellido="Méndez")
        periodo = self.apps.get_model("academico", "PeriodoAcademico").objects.create(codigo="01-2026", nombre="01-2026")
        asignatura = self.apps.get_model("academico", "Asignatura").objects.create(codigo="ARQ01", nombre="Arquitectura de Software")
        modalidad = self.apps.get_model("academico", "Modalidad").objects.create(codigo="PRE", nombre="Presencial")
        self.oferta = self.apps.get_model("horarios", "OfertaAcademica").objects.create(profesor=profesor, periodo=periodo, asignatura=asignatura, modalidad=modalidad)
        self.Historico = self.apps.get_model("horarios", "Horario")
        for i in range(10):
            self.Historico.objects.create(oferta=self.oferta, aula=self.aulas[i % 2], dia="LU", hora_inicio=time(8), hora_fin=time(9), activo=i % 2 == 0)

    def tearDown(self):
        # Solo limpieza de la base de pruebas, para restaurar el esquema final.
        self.Historico.objects.filter(aula__isnull=True).delete()
        MigrationExecutor(connection).migrate([self.nueva])
        super().tearDown()

    def test_backfill_conserva_diez_registros_y_aulas(self):
        antes = list(self.Historico.objects.order_by("pk").values())
        executor = MigrationExecutor(connection); executor.migrate([self.nueva])
        Actual = executor.loader.project_state([self.nueva]).apps.get_model("horarios", "Horario")
        despues = list(Actual.objects.order_by("pk").values())
        self.assertEqual(len(despues), 10)
        for fila in despues:
            aula = next(a for a in self.aulas if a.pk == fila["aula_id"])
            self.assertEqual(fila.pop("sede_id"), aula.sede_id)
        self.assertEqual(antes, despues)
        self.assertFalse(Actual._meta.get_field("sede").null)

    def test_pendiente_confirmado_del_usuario(self):
        self.Historico.objects.create(pk=11, oferta=self.oferta, aula=None, dia="LU", hora_inicio=time(7), hora_fin=time(8))
        executor = MigrationExecutor(connection); executor.migrate([self.nueva])
        Actual = executor.loader.project_state([self.nueva]).apps.get_model("horarios", "Horario")
        h = Actual.objects.get(pk=11)
        self.assertEqual(h.sede_id, self.sede.pk)
        self.assertIsNone(h.aula_id)

    def test_pendiente_desconocido_no_inventa_sede(self):
        self.Historico.objects.create(oferta=self.oferta, aula=None, dia="MA", hora_inicio=time(8), hora_fin=time(9))
        with self.assertRaisesMessage(RuntimeError, "No se puede deducir la sede"):
            MigrationExecutor(connection).migrate([self.nueva])
        self.assertEqual(self.Historico.objects.count(), 11)
