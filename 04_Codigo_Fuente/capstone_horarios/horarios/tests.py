from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from academico.models import (
    Asignatura, Aula, CentroTutorial, Facultad, Modalidad,
    PeriodoAcademico, Profesor, ProgramaAcademico, Sede, Semestre,
)
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo


class ValidacionHorarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = CentroTutorial.objects.create(codigo="CT-TEST", nombre="Centro Prueba")
        sede = Sede.objects.create(codigo="SEDE-TEST", nombre="Sede Prueba", centro_tutorial=cls.centro)
        facultad = Facultad.objects.create(codigo="FAC-TEST", nombre="Facultad Prueba")
        cls.programa = ProgramaAcademico.objects.create(
            codigo="PROG-TEST", nombre="Programa Prueba", facultad=facultad,
        )
        cls.periodo = PeriodoAcademico.objects.create(codigo="TEST-1", nombre="Periodo Prueba 1")
        cls.semestre = Semestre.objects.create(numero=1)
        cls.modalidad = Modalidad.objects.create(codigo="MOD-TEST", nombre="Modalidad Prueba")
        cls.asignatura = Asignatura.objects.create(codigo="ASIG-TEST", nombre="Asignatura Prueba")
        cls.profesor_1 = Profesor.objects.create(identificacion="DOC-1", nombre="Ana", apellido="Prueba")
        cls.profesor_2 = Profesor.objects.create(identificacion="DOC-2", nombre="Luis", apellido="Prueba")
        cls.aula_1 = Aula.objects.create(codigo="A-1", nombre="Aula Prueba 1", sede=sede, capacidad=20)
        cls.aula_2 = Aula.objects.create(codigo="A-2", nombre="Aula Prueba 2", sede=sede, capacidad=20)
        cls.aula_virtual = Aula.objects.create(
            codigo="V-1", nombre="Aula Virtual Prueba", sede=sede, tipo=Aula.TIPO_VIRTUAL,
        )
        cls.grupo_1 = Grupo.objects.create(
            codigo="G-1", programa=cls.programa, centro_tutorial=cls.centro,
            periodo=cls.periodo, semestre=cls.semestre,
        )
        cls.grupo_2 = Grupo.objects.create(
            codigo="G-2", programa=cls.programa, centro_tutorial=cls.centro,
            periodo=cls.periodo, semestre=cls.semestre,
        )

    def crear_oferta(self, profesor, grupo):
        oferta = OfertaAcademica(
            asignatura=self.asignatura, profesor=profesor,
            periodo=grupo.periodo, modalidad=self.modalidad,
        )
        oferta.full_clean()
        oferta.save()
        relacion = OfertaGrupo(oferta=oferta, grupo=grupo, cupos=10)
        relacion.full_clean()
        relacion.save()
        return oferta

    def nuevo_horario(self, profesor, grupo, aula, inicio=time(8), fin=time(10), dia="LU"):
        return Horario(
            oferta=self.crear_oferta(profesor, grupo), aula=aula,
            dia=dia, hora_inicio=inicio, hora_fin=fin,
        )

    def guardar_horario(self, horario):
        # Las vistas actuales validan explicitamente antes de guardar.
        horario.full_clean()
        horario.save()
        return horario

    def guardar_horario_base(self, aula=None):
        return self.guardar_horario(self.nuevo_horario(
            self.profesor_1, self.grupo_1, aula or self.aula_1,
        ))

    def comprobar_conflicto(self, horario, campo, texto):
        cantidad = Horario.objects.count()
        with self.assertRaises(ValidationError) as error:
            self.guardar_horario(horario)
        self.assertEqual(set(error.exception.message_dict), {campo})
        self.assertIn(texto, error.exception.message_dict[campo][0])
        self.assertIsNone(horario.pk)
        self.assertEqual(Horario.objects.count(), cantidad)

    def test_profesor_no_admite_superposiciones_en_mismo_periodo(self):
        self.guardar_horario_base()
        for inicio, fin in [
            (time(9), time(11)), (time(7), time(9)),
            (time(8), time(10)), (time(8, 30), time(9, 30)),
            (time(7), time(11)),
        ]:
            with self.subTest(inicio=inicio, fin=fin):
                horario = self.nuevo_horario(
                    self.profesor_1, self.grupo_2, self.aula_2, inicio, fin,
                )
                self.comprobar_conflicto(horario, "oferta", "El profesor")

    def test_aula_fisica_no_admite_horarios_simultaneos(self):
        self.guardar_horario_base()
        horario = self.nuevo_horario(
            self.profesor_2, self.grupo_2, self.aula_1, time(9), time(11),
        )
        self.comprobar_conflicto(horario, "aula", "El aula")

    def test_grupo_no_admite_asignaciones_superpuestas(self):
        self.guardar_horario_base()
        horario = self.nuevo_horario(
            self.profesor_2, self.grupo_1, self.aula_2, time(9), time(11),
        )
        self.comprobar_conflicto(horario, "oferta", "El grupo")

    def test_horario_valido_se_guarda(self):
        horario = self.guardar_horario_base()
        guardado = Horario.objects.get(pk=horario.pk)
        self.assertEqual(Horario.objects.count(), 1)
        self.assertEqual(guardado.oferta.profesor_id, self.profesor_1.pk)
        self.assertEqual(guardado.aula_id, self.aula_1.pk)
        self.assertEqual(guardado.dia, "LU")
        self.assertEqual(guardado.hora_inicio, time(8))
        self.assertEqual(guardado.hora_fin, time(10))
        self.assertEqual(list(guardado.oferta.grupos.all()), [self.grupo_1])

    def test_edicion_no_produce_conflicto_con_el_propio_horario(self):
        horario = self.guardar_horario_base()
        pk_original = horario.pk
        self.guardar_horario(horario)
        horario.hora_inicio = time(8, 30)
        horario.hora_fin = time(10, 30)
        self.guardar_horario(horario)
        horario.refresh_from_db()
        self.assertEqual(horario.pk, pk_original)
        self.assertEqual(Horario.objects.count(), 1)
        self.assertEqual(horario.hora_inicio, time(8, 30))
        self.assertEqual(horario.hora_fin, time(10, 30))

    def test_aula_virtual_admite_horarios_simultaneos_sin_otros_conflictos(self):
        self.guardar_horario_base(aula=self.aula_virtual)
        horario = self.guardar_horario(self.nuevo_horario(
            self.profesor_2, self.grupo_2, self.aula_virtual, time(9), time(11),
        ))
        self.assertEqual(Horario.objects.filter(aula=self.aula_virtual).count(), 2)
        self.assertIsNotNone(horario.pk)

    def test_aula_virtual_mantiene_validacion_de_profesor_y_grupo(self):
        self.guardar_horario_base(aula=self.aula_virtual)
        for profesor, grupo, texto in [
            (self.profesor_1, self.grupo_2, "El profesor"),
            (self.profesor_2, self.grupo_1, "El grupo"),
        ]:
            with self.subTest(conflicto=texto):
                horario = self.nuevo_horario(
                    profesor, grupo, self.aula_virtual, time(9), time(11),
                )
                self.comprobar_conflicto(horario, "oferta", texto)

    def test_horarios_consecutivos_no_son_superposiciones(self):
        self.guardar_horario_base()
        for inicio, fin in [(time(6), time(8)), (time(10), time(12))]:
            with self.subTest(inicio=inicio, fin=fin):
                self.guardar_horario(self.nuevo_horario(
                    self.profesor_1, self.grupo_1, self.aula_1, inicio, fin,
                ))
        self.assertEqual(Horario.objects.count(), 3)

    def test_misma_hora_en_otro_dia_no_genera_conflicto(self):
        self.guardar_horario_base()
        self.guardar_horario(self.nuevo_horario(
            self.profesor_1, self.grupo_1, self.aula_1, dia="MA",
        ))
        self.assertEqual(Horario.objects.count(), 2)

    def test_mismo_profesor_y_aula_en_otro_periodo_no_generan_conflicto(self):
        self.guardar_horario_base()
        periodo = PeriodoAcademico.objects.create(codigo="TEST-2", nombre="Periodo Prueba 2")
        grupo = Grupo.objects.create(
            codigo="G-1", programa=self.programa, centro_tutorial=self.centro,
            periodo=periodo, semestre=self.semestre,
        )
        self.guardar_horario(self.nuevo_horario(self.profesor_1, grupo, self.aula_1))
        self.assertEqual(Horario.objects.count(), 2)
