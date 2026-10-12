from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .choices import DiaSemana
from .forms import CargaDocenteForm, DisponibilidadProfesorForm
from .models import CargaDocente, DisponibilidadProfesor, PeriodoAcademico, Profesor


class DocenciaFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profesor = Profesor.objects.create(identificacion="DOC-TEST", nombre="Ana", apellido="Prueba")
        cls.periodo = PeriodoAcademico.objects.create(codigo="PER-TEST", nombre="Periodo Prueba")

    def bloque(self, inicio=time(8), fin=time(10), activo=True, **kwargs):
        return DisponibilidadProfesor(
            profesor=self.profesor, periodo=self.periodo, dia="LU",
            hora_inicio=inicio, hora_fin=fin, activo=activo, **kwargs,
        )

    def guardar(self, objeto):
        objeto.full_clean()
        objeto.save()
        return objeto

    def carga(self, horas="12.00", activo=True):
        return CargaDocente(
            profesor=self.profesor, periodo=self.periodo,
            horas_asignadas=Decimal(horas), activo=activo,
        )


class DisponibilidadProfesorTests(DocenciaFixture):
    def test_hora_final_igual(self):
        with self.assertRaises(ValidationError):
            self.bloque(fin=time(8)).full_clean()

    def test_hora_final_anterior(self):
        with self.assertRaises(ValidationError):
            self.bloque(fin=time(7)).full_clean()

    def test_duplicado_exacto(self):
        self.guardar(self.bloque())
        with self.assertRaises(ValidationError):
            self.bloque().full_clean()

    def test_duplicado_exacto_inactivo(self):
        self.guardar(self.bloque(activo=False))
        with self.assertRaises(ValidationError):
            self.bloque().full_clean()

    def test_solapamiento_parcial(self):
        self.guardar(self.bloque())
        for inicio, fin in [(time(7), time(9)), (time(9), time(11))]:
            with self.subTest(inicio=inicio):
                with self.assertRaises(ValidationError):
                    self.bloque(inicio, fin).full_clean()

    def test_solapamiento_total(self):
        self.guardar(self.bloque())
        for inicio, fin in [(time(7), time(11)), (time(8, 30), time(9, 30))]:
            with self.subTest(inicio=inicio):
                with self.assertRaises(ValidationError):
                    self.bloque(inicio, fin).full_clean()

    def test_bloques_separados(self):
        self.guardar(self.bloque())
        self.guardar(self.bloque(time(11), time(12)))
        self.assertEqual(DisponibilidadProfesor.objects.count(), 2)

    def test_bloques_consecutivos(self):
        self.guardar(self.bloque())
        self.guardar(self.bloque(time(10), time(12)))
        self.assertEqual(DisponibilidadProfesor.objects.count(), 2)

    def test_edicion_sin_falso_conflicto(self):
        bloque = self.guardar(self.bloque())
        self.guardar(bloque)
        bloque.hora_fin = time(11)
        self.guardar(bloque)
        bloque.refresh_from_db()
        self.assertEqual(bloque.hora_fin, time(11))
        self.assertEqual(DisponibilidadProfesor.objects.count(), 1)

    def test_bloque_inactivo_no_conflicta(self):
        self.guardar(self.bloque())
        self.guardar(self.bloque(time(9), time(11), activo=False))
        self.guardar(self.bloque(time(10), time(12)))
        self.assertEqual(DisponibilidadProfesor.objects.count(), 3)

    def test_reactivacion_conflictiva(self):
        self.guardar(self.bloque())
        bloque = self.guardar(self.bloque(time(9), time(11), activo=False))
        bloque.activo = True
        with self.assertRaises(ValidationError):
            bloque.full_clean()
        bloque.refresh_from_db()
        self.assertFalse(bloque.activo)

    def test_reactivacion_sin_conflicto(self):
        bloque = self.guardar(self.bloque(activo=False))
        bloque.activo = True
        self.guardar(bloque)
        self.assertTrue(DisponibilidadProfesor.objects.get(pk=bloque.pk).activo)

    def test_otro_profesor_periodo_o_dia_no_conflicta(self):
        self.guardar(self.bloque())
        profesor = Profesor.objects.create(identificacion="DOC-OTRO", nombre="Luis", apellido="Prueba")
        periodo = PeriodoAcademico.objects.create(codigo="PER-OTRO", nombre="Otro periodo")
        for campo, valor in [("profesor", profesor), ("periodo", periodo), ("dia", "MA")]:
            with self.subTest(campo=campo):
                bloque = self.bloque()
                setattr(bloque, campo, valor)
                self.guardar(bloque)
        self.assertEqual(DisponibilidadProfesor.objects.count(), 4)

    def test_dia_invalido(self):
        bloque = self.bloque()
        bloque.dia = "XX"
        with self.assertRaises(ValidationError):
            bloque.full_clean()

    def test_restricciones_en_base_de_datos(self):
        self.guardar(self.bloque())
        casos = [self.bloque(), self.bloque(fin=time(7))]
        invalido = self.bloque(time(11), time(12))
        invalido.dia = "XX"
        casos.append(invalido)
        for bloque in casos:
            with self.subTest(dia=bloque.dia, fin=bloque.hora_fin):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        bloque.save()

    def test_foreignkeys_protegidas(self):
        self.guardar(self.bloque())
        for objeto in [self.profesor, self.periodo]:
            with self.subTest(modelo=type(objeto).__name__):
                with self.assertRaises(ProtectedError):
                    objeto.delete()


class CargaDocenteTests(DocenciaFixture):
    def test_carga_negativa(self):
        with self.assertRaises(ValidationError):
            self.carga("-1.00").full_clean()

    def test_carga_cero_valida(self):
        carga = self.guardar(self.carga("0.00"))
        carga.refresh_from_db()
        self.assertEqual(carga.horas_asignadas, Decimal("0.00"))

    def test_carga_fraccionaria(self):
        carga = self.guardar(self.carga("12.50"))
        carga.refresh_from_db()
        self.assertEqual(carga.horas_asignadas, Decimal("12.50"))

    def test_segunda_carga_activa(self):
        self.guardar(self.carga())
        with self.assertRaises(ValidationError):
            self.carga("10.00").full_clean()

    def test_varias_cargas_inactivas(self):
        self.guardar(self.carga())
        self.guardar(self.carga("8.00", activo=False))
        self.guardar(self.carga("10.00", activo=False))
        self.assertEqual(CargaDocente.objects.count(), 3)

    def test_edicion_sin_falso_conflicto(self):
        carga = self.guardar(self.carga())
        self.guardar(carga)
        carga.horas_asignadas = Decimal("14.00")
        self.guardar(carga)
        carga.refresh_from_db()
        self.assertEqual(carga.horas_asignadas, Decimal("14.00"))
        self.assertEqual(CargaDocente.objects.count(), 1)

    def test_reactivacion_sin_otra_activa(self):
        carga = self.guardar(self.carga(activo=False))
        carga.activo = True
        self.guardar(carga)
        self.assertTrue(CargaDocente.objects.get(pk=carga.pk).activo)

    def test_reactivacion_conflictiva(self):
        self.guardar(self.carga())
        carga = self.guardar(self.carga("8.00", activo=False))
        carga.activo = True
        with self.assertRaises(ValidationError):
            carga.full_clean()
        carga.refresh_from_db()
        self.assertFalse(carga.activo)

    def test_restricciones_en_base_de_datos(self):
        self.guardar(self.carga())
        for carga in [self.carga("10.00"), self.carga("-1.00", activo=False)]:
            with self.subTest(horas=carga.horas_asignadas):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        carga.save()

    def test_otro_periodo_permite_carga_activa(self):
        self.guardar(self.carga())
        carga = self.carga()
        carga.periodo = PeriodoAcademico.objects.create(codigo="PER-OTRO", nombre="Otro periodo")
        self.guardar(carga)
        self.assertEqual(CargaDocente.objects.filter(activo=True).count(), 2)

    def test_foreignkeys_protegidas(self):
        self.guardar(self.carga())
        for objeto in [self.profesor, self.periodo]:
            with self.subTest(modelo=type(objeto).__name__):
                with self.assertRaises(ProtectedError):
                    objeto.delete()


class MantenedoresDocenciaTests(DocenciaFixture):
    def setUp(self):
        usuario = get_user_model().objects.create_superuser(username="admin_docencia", password="Prueba123!")
        self.client.force_login(usuario)

    def test_crud_disponibilidad(self):
        datos = {"profesor": self.profesor.pk, "periodo": self.periodo.pk,
                 "dia": "LU", "hora_inicio": "08:00", "hora_fin": "10:00", "activo": "on"}
        self.assertEqual(self.client.get(reverse("disponibilidad_crear")).status_code, 200)
        self.assertRedirects(self.client.post(reverse("disponibilidad_crear"), datos), reverse("disponibilidades_profesores"))
        bloque = DisponibilidadProfesor.objects.get()
        response = self.client.get(reverse("disponibilidades_profesores"))
        self.assertContains(response, "08:00")
        self.assertContains(response, "Ana Prueba")
        datos["hora_fin"] = "11:00"
        url = reverse("disponibilidad_editar", args=[bloque.pk])
        self.assertContains(self.client.get(url), 'value="08:00"')
        self.assertRedirects(self.client.post(url, datos), reverse("disponibilidades_profesores"))
        bloque.refresh_from_db()
        self.assertEqual(bloque.hora_fin, time(11))
        url = reverse("disponibilidad_eliminar", args=[bloque.pk])
        self.assertContains(self.client.get(url), "08:00")
        self.assertRedirects(self.client.post(url), reverse("disponibilidades_profesores"))
        self.assertFalse(DisponibilidadProfesor.objects.exists())

    def test_crud_carga_docente(self):
        datos = {"profesor": self.profesor.pk, "periodo": self.periodo.pk,
                 "horas_asignadas": "12.50", "activo": "on"}
        self.assertEqual(self.client.get(reverse("carga_docente_crear")).status_code, 200)
        self.assertRedirects(self.client.post(reverse("carga_docente_crear"), datos), reverse("cargas_docentes"))
        carga = CargaDocente.objects.get()
        self.assertContains(self.client.get(reverse("cargas_docentes")), "12.50")
        datos["horas_asignadas"] = "14.00"
        url = reverse("carga_docente_editar", args=[carga.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertRedirects(self.client.post(url, datos), reverse("cargas_docentes"))
        carga.refresh_from_db()
        self.assertEqual(carga.horas_asignadas, Decimal("14.00"))
        url = reverse("carga_docente_eliminar", args=[carga.pk])
        self.assertContains(self.client.get(url), "14.00")
        self.assertRedirects(self.client.post(url), reverse("cargas_docentes"))
        self.assertFalse(CargaDocente.objects.exists())

    def test_formularios_muestran_errores_de_modelo(self):
        self.guardar(self.bloque())
        self.guardar(self.carga())
        disponibilidad = DisponibilidadProfesorForm(data={
            "profesor": self.profesor.pk, "periodo": self.periodo.pk,
            "dia": "LU", "hora_inicio": "09:00", "hora_fin": "11:00", "activo": True,
        })
        carga = CargaDocenteForm(data={
            "profesor": self.profesor.pk, "periodo": self.periodo.pk,
            "horas_asignadas": "10.00", "activo": True,
        })
        self.assertFalse(disponibilidad.is_valid())
        self.assertFalse(carga.is_valid())
        self.assertTrue(disponibilidad.non_field_errors())
        self.assertTrue(carga.non_field_errors())

    def test_permisos_y_accesos(self):
        response = self.client.get(reverse("mantenedores"))
        self.assertContains(response, reverse("disponibilidades_profesores"))
        self.assertContains(response, reverse("cargas_docentes"))
        usuario = get_user_model().objects.create_user(username="sin_permiso_docencia")
        self.client.force_login(usuario)
        bloque = self.guardar(self.bloque())
        carga = self.guardar(self.carga())
        for listado, prefijo, objeto in [
            ("disponibilidades_profesores", "disponibilidad", bloque),
            ("cargas_docentes", "carga_docente", carga),
        ]:
            rutas = [reverse(listado), reverse(prefijo + "_crear"),
                     reverse(prefijo + "_editar", args=[objeto.pk]),
                     reverse(prefijo + "_eliminar", args=[objeto.pk])]
            for url in rutas:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
                    self.assertEqual(self.client.post(url).status_code, 403)

    def test_choices_compartidos(self):
        from horarios.models import Horario
        self.assertEqual(Horario.DIAS, DiaSemana.choices)
        self.assertEqual(DisponibilidadProfesor._meta.get_field("dia").choices, DiaSemana.choices)
