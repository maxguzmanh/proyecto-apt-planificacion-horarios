from datetime import time
from decimal import Decimal
from threading import Barrier, Event, Thread
from unittest import skipUnless
from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections, close_old_connections
from django.db.utils import NotSupportedError
from django.test import TestCase, TransactionTestCase, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from academico.models import (Aula, Asignatura, CargaDocente, DisponibilidadProfesor, CentroTutorial,
    Facultad, ProgramaAcademico, ProgramaCentroTutorial, PeriodoAcademico, Modalidad, Profesor, Semestre, PlanEstudioAsignatura, Sede)
from .models import Horario, OfertaAcademica, OfertaGrupo, Grupo
from .services import calcular_horas_planificadas, operacion_planificacion


class DatosDocencia:
    def crear_datos(self):
        centro = CentroTutorial.objects.create(codigo="CT-VAL", nombre="Centro Prueba")
        sede = Sede.objects.create(codigo="SEDE-VAL", nombre="Sede Prueba", centro_tutorial=centro)
        facultad = Facultad.objects.create(codigo="FAC-VAL", nombre="Facultad Prueba")
        programa = ProgramaAcademico.objects.create(codigo="PROG-VAL", nombre="Programa Prueba", facultad=facultad)
        ProgramaCentroTutorial.objects.create(programa=programa, centro_tutorial=centro)
        self.periodo = PeriodoAcademico.objects.create(codigo="PER-VAL", nombre="Periodo Prueba")
        self.otro_periodo = PeriodoAcademico.objects.create(codigo="PER-OTRO", nombre="Otro Periodo")
        self.profesor = Profesor.objects.create(identificacion="DOC-VAL1", nombre="Ana", apellido="Prueba")
        self.otro_profesor = Profesor.objects.create(identificacion="DOC-VAL2", nombre="Luis", apellido="Prueba")
        self.aula = Aula.objects.create(codigo="A-VAL1", nombre="Aula Prueba 1", sede=sede)
        self.otra_aula = Aula.objects.create(codigo="A-VAL2", nombre="Aula Prueba 2", sede=sede)
        self.asignatura = Asignatura.objects.create(codigo="ASIG-VAL", nombre="Asignatura Prueba")
        self.modalidad = Modalidad.objects.create(codigo="PRE", nombre="Presencial")
        semestre = Semestre.objects.create(numero=1)
        PlanEstudioAsignatura.objects.create(programa=programa, semestre=semestre, asignatura=self.asignatura, creditos=2)
        self.grupo = Grupo.objects.create(codigo="G-VAL", programa=programa, centro_tutorial=centro, periodo=self.periodo, semestre=semestre)
        self.condiciones(self.profesor, self.periodo)
        self.condiciones(self.otro_profesor, self.periodo)
        self.oferta = self.nueva_oferta(self.profesor)
        self.otra_oferta = self.nueva_oferta(self.otro_profesor)

    def condiciones(self, profesor, periodo, horas=12):
        carga, _ = CargaDocente.objects.get_or_create(profesor=profesor, periodo=periodo, activo=True, defaults={"horas_asignadas": horas})
        for dia, _ in Horario.DIAS:
            DisponibilidadProfesor.objects.get_or_create(profesor=profesor, periodo=periodo, dia=dia,
                hora_inicio=time(6), hora_fin=time(22), defaults={"activo": True})
        return carga

    def nueva_oferta(self, profesor, periodo=None):
        return OfertaAcademica.objects.create(asignatura=self.asignatura, profesor=profesor,
            periodo=periodo or self.periodo, modalidad=self.modalidad)

    def horario(self, inicio=time(8), fin=time(10), dia="LU", oferta=None, aula=None, activo=True):
        return Horario(oferta=oferta or self.oferta, sede=(aula or self.aula).sede, aula=aula or self.aula, dia=dia,
            hora_inicio=inicio, hora_fin=fin, activo=activo)

    def disponibilidad(self, bloques):
        DisponibilidadProfesor.objects.filter(profesor=self.profesor, periodo=self.periodo).delete()
        for dia, inicio, fin in bloques:
            DisponibilidadProfesor.objects.create(profesor=self.profesor, periodo=self.periodo,
                dia=dia, hora_inicio=inicio, hora_fin=fin)

    def carga(self, horas):
        carga = CargaDocente.objects.get(profesor=self.profesor, periodo=self.periodo, activo=True)
        carga.horas_asignadas = Decimal(str(horas))
        carga.save()


class ValidacionesDocentesTests(DatosDocencia, TestCase):
    def setUp(self):
        self.crear_datos()

    def test_intervalo_completamente_contenido(self):
        self.disponibilidad([("LU", time(8), time(12))])
        self.horario(time(9), time(11)).save()
        self.assertEqual(Horario.objects.count(), 1)

    def test_inicia_antes(self):
        self.disponibilidad([("LU", time(8), time(12))])
        with self.assertRaises(ValidationError): self.horario(time(7), time(9)).save()
        self.assertFalse(Horario.objects.exists())

    def test_termina_despues(self):
        self.disponibilidad([("LU", time(8), time(12))])
        with self.assertRaises(ValidationError): self.horario(time(11), time(13)).save()

    def test_sin_disponibilidad(self):
        self.disponibilidad([])
        with self.assertRaisesMessage(ValidationError, "no tiene disponibilidad registrada"):
            self.horario().save()

    def test_dia_distinto(self):
        self.disponibilidad([("MA", time(8), time(12))])
        with self.assertRaises(ValidationError): self.horario().save()

    def test_periodo_distinto(self):
        oferta = self.nueva_oferta(self.profesor, self.otro_periodo)
        with self.assertRaises(ValidationError): self.horario(oferta=oferta).save()

    def test_bloques_consecutivos(self):
        self.disponibilidad([("LU", time(8), time(10)), ("LU", time(10), time(12))])
        self.horario(time(9), time(11)).save()

    def test_bloques_con_hueco(self):
        self.disponibilidad([("LU", time(8), time(10)), ("LU", time(11), time(13))])
        with self.assertRaises(ValidationError): self.horario(time(9), time(12)).save()

    def test_edicion_no_duplica_carga(self):
        self.carga(2)
        h = self.horario(); h.save()
        h.hora_inicio, h.hora_fin = time(10), time(12)
        h.save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 2)

    def test_edicion_fuera_disponibilidad_rollback(self):
        self.disponibilidad([("LU", time(8), time(12))])
        h = self.horario(); h.save()
        h.hora_inicio, h.hora_fin = time(11), time(13)
        with self.assertRaises(ValidationError): h.save()
        h.refresh_from_db()
        self.assertEqual(h.hora_inicio, time(8))

    def test_total_menor_carga(self):
        self.carga(3); self.horario().save()

    def test_total_igual_carga(self):
        self.carga(2); self.horario().save()

    def test_total_superior_carga(self):
        self.carga(1)
        with self.assertRaisesMessage(ValidationError, "supera la carga docente"):
            self.horario().save()

    def test_sin_carga_activa(self):
        CargaDocente.objects.filter(profesor=self.profesor).update(activo=False)
        with self.assertRaisesMessage(ValidationError, "Carga docente no registrada"):
            self.horario().save()

    def test_transversal_cuenta_una_vez(self):
        self.carga(2)
        otro = Grupo.objects.create(codigo="G-OTRO", programa=self.grupo.programa, centro_tutorial=self.grupo.centro_tutorial,
            periodo=self.periodo, semestre=self.grupo.semestre)
        for grupo in [self.grupo, otro]: OfertaGrupo.objects.create(oferta=self.oferta, grupo=grupo, cupos=10)
        self.horario().save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 2)

    def test_periodos_no_se_mezclan(self):
        self.condiciones(self.profesor, self.otro_periodo)
        otra = self.nueva_oferta(self.profesor, self.otro_periodo)
        self.horario(time(8), time(16), oferta=otra).save()
        self.carga(2); self.horario().save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 2)

    def test_horarios_inactivos_no_cuentan(self):
        self.horario(dia="MA", activo=False).save()
        self.carga(2); self.horario().save()

    def test_ofertas_inactivas_no_cuentan(self):
        otra = self.nueva_oferta(self.profesor)
        otra.activo = False; otra.save()
        self.horario(dia="MA", oferta=otra).save()
        self.carga(2); self.horario().save()

    def test_aumento_duracion_recalcula(self):
        self.carga(3)
        h = self.horario(); h.save()
        h.hora_fin = time(11); h.save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 3)
        h.hora_fin = time(12)
        with self.assertRaises(ValidationError): h.save()
        h.refresh_from_db(); self.assertEqual(h.hora_fin, time(11))

    def dos_horarios(self):
        self.horario().save()
        self.horario(time(14), time(16), dia="MA").save()

    def test_cambio_profesor_revalida_todos(self):
        self.dos_horarios()
        self.oferta.profesor = self.otro_profesor; self.oferta.save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 0)
        self.assertEqual(calcular_horas_planificadas(self.otro_profesor, self.periodo), 4)

    def test_rollback_si_un_horario_sin_disponibilidad(self):
        self.dos_horarios()
        DisponibilidadProfesor.objects.filter(profesor=self.otro_profesor, dia="MA").delete()
        self.oferta.profesor = self.otro_profesor
        with self.assertRaises(ValidationError): self.oferta.save()
        self.oferta.refresh_from_db(); self.assertEqual(self.oferta.profesor_id, self.profesor.pk)
        self.assertEqual(Horario.objects.filter(oferta=self.oferta).count(), 2)

    def test_rollback_nuevo_profesor_excede_carga(self):
        self.dos_horarios()
        carga = CargaDocente.objects.get(profesor=self.otro_profesor)
        carga.horas_asignadas = 3; carga.save()
        self.oferta.profesor = self.otro_profesor
        with self.assertRaises(ValidationError): self.oferta.save()
        self.oferta.refresh_from_db(); self.assertEqual(self.oferta.profesor_id, self.profesor.pk)

    def test_cambio_periodo_valido(self):
        self.dos_horarios(); self.condiciones(self.profesor, self.otro_periodo)
        self.oferta.periodo = self.otro_periodo; self.oferta.save()
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.otro_periodo), 4)

    def test_cambio_periodo_invalido_rollback(self):
        self.dos_horarios(); self.oferta.periodo = self.otro_periodo
        with self.assertRaises(ValidationError): self.oferta.save()
        self.oferta.refresh_from_db(); self.assertEqual(self.oferta.periodo_id, self.periodo.pk)

    def test_orden_estable_dos_profesores(self):
        with CaptureQueriesContext(connection) as consultas:
            with operacion_planificacion([self.otro_profesor.pk, self.profesor.pk]) as bloqueados:
                self.assertEqual([p.pk for p in bloqueados], sorted([self.profesor.pk, self.otro_profesor.pk]))
        consulta = next(c["sql"] for c in consultas if "FOR UPDATE" in c["sql"])
        self.assertIn('ORDER BY "academico_profesor"."id" ASC', consulta)

    def test_escrituras_masivas_no_saltan_reglas(self):
        with self.assertRaises(NotSupportedError): Horario.objects.bulk_create([self.horario()])
        with self.assertRaises(NotSupportedError): OfertaAcademica.objects.filter(pk=self.oferta.pk).update(profesor=self.otro_profesor)

    def test_admin_save_model_no_salta_validacion(self):
        self.disponibilidad([])
        request = RequestFactory().post("/admin/")
        h = self.horario()
        with self.assertRaises(ValidationError): admin.site._registry[Horario].save_model(request, h, None, False)
        self.assertFalse(Horario.objects.exists())

    def test_admin_horario_muestra_error(self):
        usuario = get_user_model().objects.create_superuser(username="admin_val", password="Prueba123!")
        self.client.force_login(usuario)
        self.disponibilidad([])
        response = self.client.post(reverse("admin:horarios_horario_add"), {"oferta": self.oferta.pk,
            "sede": self.aula.sede_id, "aula": self.aula.pk, "dia": "LU", "hora_inicio": "08:00", "hora_fin": "10:00", "activo": "on", "_save": "Guardar"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no tiene disponibilidad registrada")
        self.assertFalse(Horario.objects.exists())

    def test_admin_oferta_rechaza_cambio_profesor(self):
        usuario = get_user_model().objects.create_superuser(username="admin_oferta", password="Prueba123!")
        self.client.force_login(usuario); self.dos_horarios()
        DisponibilidadProfesor.objects.filter(profesor=self.otro_profesor, dia="MA").delete()
        response = self.client.post(reverse("admin:horarios_ofertaacademica_change", args=[self.oferta.pk]), {
            "asignatura": self.asignatura.pk, "profesor": self.otro_profesor.pk, "periodo": self.periodo.pk,
            "modalidad": self.modalidad.pk, "activo": "on", "_save": "Guardar",
            "ofertas_grupo-TOTAL_FORMS": "0", "ofertas_grupo-INITIAL_FORMS": "0", "ofertas_grupo-MIN_NUM_FORMS": "0", "ofertas_grupo-MAX_NUM_FORMS": "1000"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no tiene disponibilidad registrada")
        self.oferta.refresh_from_db(); self.assertEqual(self.oferta.profesor_id, self.profesor.pk)

    def test_creacion_tradicional_reglas_y_rollback(self):
        usuario = get_user_model().objects.create_superuser(username="form_val", password="Prueba123!")
        self.client.force_login(usuario)
        filtros = {"centro": self.grupo.centro_tutorial_id, "programa": self.grupo.programa_id,
            "periodo": self.periodo.pk, "semestre": self.grupo.semestre_id, "sede": self.aula.sede_id}
        datos = {**filtros, "asignatura": self.asignatura.pk, "profesor": self.profesor.pk, "modalidad": self.modalidad.pk,
            "grupos": [self.grupo.pk], "cupos": 10, "aula": self.aula.pk, "dia": "LU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        self.disponibilidad([])
        cantidad = OfertaAcademica.objects.count()
        response = self.client.post(reverse("nueva_asignacion") + "?" + urlencode(filtros), datos)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no tiene disponibilidad registrada")
        self.assertEqual(OfertaAcademica.objects.count(), cantidad)
        self.condiciones(self.profesor, self.periodo); self.carga(1)
        response = self.client.post(reverse("nueva_asignacion") + "?" + urlencode(filtros), datos)
        self.assertContains(response, "supera la carga docente")
        self.carga(2)
        response = self.client.post(reverse("nueva_asignacion") + "?" + urlencode(filtros), datos)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Horario.objects.count(), 1)

    def test_admin_repite_validacion_definitiva(self):
        from .forms import HorarioForm
        formulario = HorarioForm(data={"oferta": self.oferta.pk, "sede": self.aula.sede_id, "aula": self.aula.pk,
            "dia": "LU", "hora_inicio": "08:00", "hora_fin": "10:00"})
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.carga(0)
        request = RequestFactory().post("/admin/")
        with self.assertRaisesMessage(ValidationError, "supera la carga docente"):
            admin.site._registry[Horario].save_model(request, formulario.save(commit=False), formulario, False)
        self.assertFalse(Horario.objects.exists())

    def test_cambio_profesor_bloquea_anterior_y_nuevo_ordenados(self):
        self.oferta.profesor = self.otro_profesor
        with CaptureQueriesContext(connection) as consultas:
            self.oferta.save()
        sql = next(c["sql"] for c in consultas if "academico_profesor" in c["sql"] and "FOR UPDATE" in c["sql"])
        self.assertIn('ORDER BY "academico_profesor"."id" ASC', sql)
        self.assertIn(str(self.profesor.pk), sql)
        self.assertIn(str(self.otro_profesor.pk), sql)

    def test_movimiento_fullcalendar_disponibilidad_y_carga(self):
        usuario = get_user_model().objects.create_superuser(username="move_docencia", password="Prueba123!")
        self.client.force_login(usuario)
        h = self.horario(); h.save()
        import json
        datos = {"horario_id": h.pk, "dia": "MA", "hora_inicio": "08:00", "hora_fin": "10:00"}
        DisponibilidadProfesor.objects.filter(profesor=self.profesor, dia="MA").delete()
        response = self.client.post(reverse("mover_horario"), json.dumps(datos), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("disponibilidad", str(response.json()["errors"]).lower())
        h.refresh_from_db(); self.assertEqual(h.dia, "LU")
        self.condiciones(self.profesor, self.periodo); self.carga(1)
        response = self.client.post(reverse("mover_horario"), json.dumps(datos), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("supera la carga docente", str(response.json()["errors"]))
        h.refresh_from_db(); self.assertEqual(h.dia, "LU")
        self.carga(2)
        response = self.client.post(reverse("mover_horario"), json.dumps(datos), content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_edicion_tradicional_cambia_profesor_y_bloque_atomicamente(self):
        usuario = get_user_model().objects.create_superuser(username="edit_docencia", password="Prueba123!")
        self.client.force_login(usuario)
        OfertaGrupo.objects.create(oferta=self.oferta, grupo=self.grupo, cupos=10)
        h = self.horario(); h.save()
        self.horario(time(14), time(16), dia="MA").save()
        # El nuevo docente no cubre el bloque original del horario editado,
        # pero sí el bloque final y el otro horario que comparte la oferta.
        DisponibilidadProfesor.objects.filter(profesor=self.otro_profesor).delete()
        for dia, inicio, fin in [("JU", time(10), time(12)), ("MA", time(14), time(16))]:
            DisponibilidadProfesor.objects.create(profesor=self.otro_profesor, periodo=self.periodo,
                dia=dia, hora_inicio=inicio, hora_fin=fin)
        datos = {"asignatura": self.asignatura.pk, "profesor": self.otro_profesor.pk,
            "modalidad": self.modalidad.pk, "grupos": [self.grupo.pk], "cupos": 10,
            "sede": self.aula.sede_id, "aula": self.aula.pk, "dia": "JU", "hora_inicio": "10:00", "hora_fin": "12:00"}
        response = self.client.post(reverse("editar_asignacion", args=[h.pk]), datos)
        self.assertEqual(response.status_code, 302)
        self.oferta.refresh_from_db(); h.refresh_from_db()
        self.assertEqual(self.oferta.profesor_id, self.otro_profesor.pk)
        self.assertEqual(h.dia, "JU")
        self.assertEqual(calcular_horas_planificadas(self.otro_profesor, self.periodo), 4)


    def test_rollback_conflicto_detectado_despues_de_actualizar_oferta(self):
        self.dos_horarios()
        self.horario(oferta=self.otra_oferta, aula=self.otra_aula).save()
        self.oferta.profesor = self.otro_profesor
        # Disponibilidad y carga candidatas pasan; el conflicto se detecta al
        # revalidar todos los horarios tras cambiar la relación en la transacción.
        self.oferta.full_clean()
        with self.assertRaisesMessage(ValidationError, "El profesor"):
            self.oferta.save()
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.profesor_id, self.profesor.pk)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 4)
        self.assertEqual(calcular_horas_planificadas(self.otro_profesor, self.periodo), 2)



@skipUnless(connection.vendor == "postgresql", "Concurrencia requiere PostgreSQL")
class ConcurrenciaDocenteTests(DatosDocencia, TransactionTestCase):
    def setUp(self):
        self.crear_datos()

    def test_dos_operaciones_mismo_profesor_no_exceden_carga(self):
        carga = CargaDocente.objects.get(profesor=self.profesor); carga.horas_asignadas = 2; carga.save()
        segunda_oferta = self.nueva_oferta(self.profesor)
        barrera = Barrier(2); resultados = []; errores = []
        def crear(dia, aula_id, oferta_id):
            close_old_connections()
            try:
                oferta = OfertaAcademica.objects.get(pk=oferta_id)
                barrera.wait(timeout=10)
                Horario(oferta=oferta, sede_id=self.aula.sede_id, aula_id=aula_id, dia=dia, hora_inicio=time(8), hora_fin=time(10)).save()
                resultados.append("ok")
            except ValidationError: resultados.append("rechazado")
            except Exception as error: errores.append(repr(error))
            finally: connections.close_all()
        hilos = [Thread(target=crear, args=("LU", self.aula.pk, self.oferta.pk)), Thread(target=crear, args=("MA", self.otra_aula.pk, segunda_oferta.pk))]
        for hilo in hilos: hilo.start()
        for hilo in hilos: hilo.join(timeout=15)
        self.assertFalse(any(h.is_alive() for h in hilos))
        self.assertEqual(errores, [])
        self.assertCountEqual(resultados, ["ok", "rechazado"])
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 2)

    def test_profesores_distintos_no_se_bloquean_logicamente(self):
        tomado = Event(); liberar = Event(); terminado = Event(); errores = []
        def retener():
            close_old_connections()
            try:
                with operacion_planificacion([self.profesor.pk]):
                    tomado.set(); liberar.wait(timeout=10)
            except Exception as error: errores.append(repr(error))
            finally: connections.close_all()
        def otro():
            close_old_connections()
            try:
                Horario(oferta_id=self.otra_oferta.pk, sede_id=self.otra_aula.sede_id, aula_id=self.otra_aula.pk,
                    dia="LU", hora_inicio=time(8), hora_fin=time(10)).save()
                terminado.set()
            except Exception as error: errores.append(repr(error))
            finally: connections.close_all()
        primero = Thread(target=retener); primero.start()
        self.assertTrue(tomado.wait(timeout=5))
        segundo = Thread(target=otro); segundo.start()
        try: self.assertTrue(terminado.wait(timeout=5))
        finally:
            liberar.set(); primero.join(timeout=10); segundo.join(timeout=10)
        self.assertEqual(errores, [])


    def test_cambios_cruzados_de_profesor_sin_deadlock(self):
        self.horario().save()
        self.horario(dia="MA", oferta=self.otra_oferta, aula=self.otra_aula).save()
        barrera = Barrier(2); errores = []; resultados = []
        def cambiar(oferta_id, profesor_id):
            close_old_connections()
            try:
                oferta = OfertaAcademica.objects.get(pk=oferta_id)
                oferta.profesor_id = profesor_id
                barrera.wait(timeout=10)
                oferta.save()
                resultados.append(oferta_id)
            except Exception as error: errores.append(repr(error))
            finally: connections.close_all()
        hilos = [Thread(target=cambiar, args=(self.oferta.pk, self.otro_profesor.pk)),
                 Thread(target=cambiar, args=(self.otra_oferta.pk, self.profesor.pk))]
        for hilo in hilos: hilo.start()
        for hilo in hilos: hilo.join(timeout=15)
        self.assertFalse(any(h.is_alive() for h in hilos))
        self.assertEqual(errores, [])
        self.assertEqual(len(resultados), 2)
        self.oferta.refresh_from_db(); self.otra_oferta.refresh_from_db()
        self.assertEqual(self.oferta.profesor_id, self.otro_profesor.pk)
        self.assertEqual(self.otra_oferta.profesor_id, self.profesor.pk)
