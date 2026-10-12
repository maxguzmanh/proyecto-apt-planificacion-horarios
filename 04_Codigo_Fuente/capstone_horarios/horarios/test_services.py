from datetime import time
from decimal import Decimal

from django.test import TestCase

from academico.models import (
    Asignatura, Aula, CargaDocente, CentroTutorial, Facultad, Modalidad,
    PeriodoAcademico, Profesor, ProgramaAcademico, Sede, Semestre,
)
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo
from .services import calcular_horas_pendientes, calcular_horas_planificadas, obtener_carga_activa


class CalculosDocentesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profesor = Profesor.objects.create(identificacion="DOC-CALC", nombre="Ana", apellido="Prueba")
        cls.otro_profesor = Profesor.objects.create(identificacion="DOC-OTRO", nombre="Luis", apellido="Prueba")
        cls.periodo = PeriodoAcademico.objects.create(codigo="PER-CALC", nombre="Periodo Prueba")
        cls.otro_periodo = PeriodoAcademico.objects.create(codigo="PER-OTRO", nombre="Otro periodo")
        centro = CentroTutorial.objects.create(codigo="CT-CALC", nombre="Centro Prueba")
        sede = Sede.objects.create(codigo="SEDE-CALC", nombre="Sede Prueba", centro_tutorial=centro)
        cls.aula = Aula.objects.create(codigo="A-CALC", nombre="Aula Prueba", sede=sede, capacidad=20)
        facultad = Facultad.objects.create(codigo="FAC-CALC", nombre="Facultad Prueba")
        programa = ProgramaAcademico.objects.create(codigo="PROG-CALC", nombre="Programa Prueba", facultad=facultad)
        semestre = Semestre.objects.create(numero=1)
        cls.grupos = [Grupo.objects.create(
            codigo=codigo, programa=programa, centro_tutorial=centro,
            periodo=cls.periodo, semestre=semestre,
        ) for codigo in ["G-1", "G-2"]]
        cls.asignatura = Asignatura.objects.create(codigo="ASIG-CALC", nombre="Asignatura Prueba")
        cls.modalidad = Modalidad.objects.create(codigo="MOD-CALC", nombre="Modalidad Prueba")

    def horario(self, inicio=time(8), fin=time(10), dia="LU", activo=True,
                oferta_activa=True, periodo=None, profesor=None):
        oferta = OfertaAcademica(
            asignatura=self.asignatura, profesor=profesor or self.profesor,
            periodo=periodo or self.periodo, modalidad=self.modalidad, activo=oferta_activa,
        )
        oferta.full_clean()
        oferta.save()
        horario = Horario(oferta=oferta, aula=self.aula, dia=dia,
                          hora_inicio=inicio, hora_fin=fin, activo=activo)
        horario.full_clean()
        horario.save()
        return horario

    def carga(self, horas="12.00", activo=True):
        carga = CargaDocente(profesor=self.profesor, periodo=self.periodo,
                            horas_asignadas=Decimal(horas), activo=activo)
        carga.full_clean()
        carga.save()
        return carga

    def test_cero_horarios(self):
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("0"))

    def test_varios_horarios_y_fracciones(self):
        self.horario()
        self.horario(time(10), time(11, 30))
        self.horario(time(8), time(8, 30), dia="MA")
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("4"))

    def test_periodos_distintos(self):
        self.horario()
        self.horario(periodo=self.otro_periodo)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("2"))

    def test_profesores_distintos(self):
        self.horario()
        self.horario(profesor=self.otro_profesor, dia="MA")
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("2"))

    def test_horarios_inactivos(self):
        self.horario(activo=False)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("0"))

    def test_ofertas_inactivas(self):
        self.horario(oferta_activa=False)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("0"))

    def test_transversal_cuenta_una_sola_vez(self):
        horario = self.horario()
        for grupo in self.grupos:
            relacion = OfertaGrupo(oferta=horario.oferta, grupo=grupo, cupos=10)
            relacion.full_clean()
            relacion.save()
        self.assertEqual(horario.oferta.grupos.count(), 2)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("2"))

    def test_horas_pendientes(self):
        carga = self.carga()
        self.horario(time(8), time(12))
        self.horario(time(8), time(12), dia="MA")
        self.assertEqual(obtener_carga_activa(self.profesor, self.periodo), carga)
        self.assertEqual(calcular_horas_pendientes(self.profesor, self.periodo), Decimal("4"))

    def test_sin_carga_activa(self):
        self.horario()
        self.assertIsNone(calcular_horas_pendientes(self.profesor, self.periodo))
        self.carga(activo=False)
        self.assertIsNone(obtener_carga_activa(self.profesor, self.periodo))
        self.assertIsNone(calcular_horas_pendientes(self.profesor, self.periodo))

    def test_carga_de_otro_periodo_no_se_utiliza(self):
        carga = self.carga()
        carga.periodo = self.otro_periodo
        carga.full_clean()
        carga.save()
        self.assertIsNone(calcular_horas_pendientes(self.profesor, self.periodo))

    def test_carga_cero_y_saldo_negativo_no_bloquean_horario(self):
        self.carga("0.00")
        self.horario()
        self.assertEqual(calcular_horas_pendientes(self.profesor, self.periodo), Decimal("-2"))

    def test_acepta_identificadores(self):
        self.carga()
        self.horario()
        self.assertEqual(calcular_horas_planificadas(self.profesor.pk, self.periodo.pk), Decimal("2"))
        self.assertEqual(calcular_horas_pendientes(self.profesor.pk, self.periodo.pk), Decimal("10"))

    def test_no_redondea_cada_duracion(self):
        self.horario(time(8), time(8, 20))
        self.horario(time(8, 20), time(8, 40))
        self.horario(time(8, 40), time(9))
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), Decimal("1"))

    def test_conserva_segundos_y_microsegundos(self):
        self.horario(time(8), time(8, 0, 1, 500000))
        self.assertEqual(
            calcular_horas_planificadas(self.profesor, self.periodo),
            Decimal("1500000") / Decimal("3600000000"),
        )


class DatosDemoDocenciaTests(TestCase):
    def test_carga_demo_repetible_conserva_condiciones_existentes(self):
        from io import StringIO
        from django.core.management import call_command
        from academico.models import DisponibilidadProfesor

        call_command("cargar_datos_demo", stdout=StringIO())
        self.assertEqual(CargaDocente.objects.count(), 6)
        self.assertEqual(DisponibilidadProfesor.objects.count(), 42)
        carga = CargaDocente.objects.first()
        carga.horas_asignadas = Decimal("15.50")
        carga.full_clean()
        carga.save()
        bloque = DisponibilidadProfesor.objects.first()
        bloque.activo = False
        bloque.full_clean()
        bloque.save()
        conteos = (Horario.objects.count(), OfertaAcademica.objects.count(), OfertaGrupo.objects.count())
        call_command("cargar_datos_demo", stdout=StringIO())
        self.assertEqual(CargaDocente.objects.count(), 6)
        self.assertEqual(DisponibilidadProfesor.objects.count(), 42)
        carga.refresh_from_db()
        bloque.refresh_from_db()
        self.assertEqual(carga.horas_asignadas, Decimal("15.50"))
        self.assertFalse(bloque.activo)
        self.assertEqual(conteos, (Horario.objects.count(), OfertaAcademica.objects.count(), OfertaGrupo.objects.count()))
