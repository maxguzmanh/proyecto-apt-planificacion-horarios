from datetime import time
from io import StringIO

from django.apps import apps
from django.core.management import call_command, CommandError
from django.test import TestCase

from academico.models import CargaDocente, DisponibilidadProfesor, PeriodoAcademico, Profesor
from .models import Horario
from .services import calcular_horas_planificadas


class DemoDocenciaIdempotenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo", stdout=StringIO())
        cls.periodo = PeriodoAcademico.objects.get(codigo="01-2026")

    def ejecutar(self):
        call_command("cargar_datos_demo", solo_docencia=True, stdout=StringIO())

    def estado_academico(self):
        return {m._meta.label: list(m.objects.order_by("pk").values()) for m in apps.get_models()
            if m._meta.app_label in ("academico", "horarios") and m not in (CargaDocente, DisponibilidadProfesor)}

    def test_repetible_y_no_modifica_entidades_academicas(self):
        horario = Horario.objects.get(oferta__asignatura__codigo="PROGWEB01")
        horario.hora_inicio = time(8, 15)
        horario.hora_fin = time(9, 45)
        horario.full_clean()
        horario.save()
        anterior = self.estado_academico()
        self.ejecutar()
        cargas = list(CargaDocente.objects.order_by("pk").values())
        bloques = list(DisponibilidadProfesor.objects.order_by("pk").values())
        self.ejecutar()
        self.assertEqual(cargas, list(CargaDocente.objects.order_by("pk").values()))
        self.assertEqual(bloques, list(DisponibilidadProfesor.objects.order_by("pk").values()))
        self.assertEqual(anterior, self.estado_academico())

    def test_todos_cubiertos_sin_sobrecarga(self):
        self.ejecutar()
        for profesor in Profesor.objects.filter(identificacion__startswith="DOC-DEMO-"):
            with self.subTest(profesor=str(profesor)):
                cargas = CargaDocente.objects.filter(profesor=profesor, periodo=self.periodo, activo=True)
                self.assertEqual(cargas.count(), 1)
                self.assertGreaterEqual(cargas.get().horas_asignadas, calcular_horas_planificadas(profesor, self.periodo))
                bloques = list(DisponibilidadProfesor.objects.filter(profesor=profesor, periodo=self.periodo, activo=True))
                self.assertTrue(bloques)
                for horario in Horario.objects.filter(oferta__profesor=profesor, oferta__periodo=self.periodo):
                    self.assertTrue(any(b.dia == horario.dia and b.hora_inicio <= horario.hora_inicio and b.hora_fin >= horario.hora_fin for b in bloques))
                for i, bloque in enumerate(bloques):
                    self.assertFalse(any(otro.dia == bloque.dia and otro.hora_inicio < bloque.hora_fin and otro.hora_fin > bloque.hora_inicio for otro in bloques[i+1:]))

    def test_reactiva_y_normaliza_condiciones_demo(self):
        profesor = Profesor.objects.get(identificacion="DOC-DEMO-001")
        CargaDocente.objects.filter(profesor=profesor).update(activo=False)
        DisponibilidadProfesor.objects.filter(profesor=profesor).update(activo=False)
        self.ejecutar()
        carga = CargaDocente.objects.get(profesor=profesor, periodo=self.periodo, activo=True)
        self.assertEqual(carga.horas_asignadas, 12)
        self.assertEqual(DisponibilidadProfesor.objects.filter(profesor=profesor, periodo=self.periodo, activo=True).count(), 2)
        cantidad = CargaDocente.objects.count()
        self.ejecutar()
        self.assertEqual(CargaDocente.objects.count(), cantidad)

    def test_no_toca_otro_periodo_o_profesor(self):
        otro = Profesor.objects.create(identificacion="DOC-AJENO", nombre="Docente", apellido="Ajeno")
        periodo = PeriodoAcademico.objects.create(codigo="OTRO", nombre="Otro periodo")
        carga = CargaDocente.objects.create(profesor=otro, periodo=self.periodo, horas_asignadas=3)
        bloque = DisponibilidadProfesor.objects.create(profesor=otro, periodo=self.periodo, dia="LU", hora_inicio=time(8), hora_fin=time(9))
        carga_periodo = CargaDocente.objects.create(profesor=Profesor.objects.first(), periodo=periodo, horas_asignadas=2)
        self.ejecutar()
        carga.refresh_from_db(); bloque.refresh_from_db(); carga_periodo.refresh_from_db()
        self.assertEqual(carga.horas_asignadas, 3)
        self.assertTrue(bloque.activo)
        self.assertEqual(carga_periodo.horas_asignadas, 2)

    def test_error_de_identidad_revierte_toda_la_operacion(self):
        profesor = Profesor.objects.get(identificacion="DOC-DEMO-006")
        profesor.nombre = "Nombre diferente"
        profesor.save()
        anterior = list(CargaDocente.objects.order_by("pk").values())
        with self.assertRaises(CommandError):
            self.ejecutar()
        self.assertEqual(anterior, list(CargaDocente.objects.order_by("pk").values()))
