from datetime import time
import json
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse

from academico.models import Aula, CargaDocente, DisponibilidadProfesor, Sede
from .models import Horario, OfertaGrupo
from .services import calcular_horas_planificadas
from .test_validacion_docente import DatosDocencia


class AulaPendienteResizeTests(DatosDocencia, TestCase):
    def setUp(self):
        self.crear_datos()
        OfertaGrupo.objects.create(oferta=self.oferta, grupo=self.grupo, cupos=10)
        self.usuario = get_user_model().objects.create_superuser(username="aula_prueba", password="Prueba123!")
        self.client.force_login(self.usuario)
        self.filtros = {"centro": self.grupo.centro_tutorial_id, "facultad": self.grupo.programa.facultad_id,
            "programa": self.grupo.programa_id, "modalidad": self.modalidad.pk, "sede": self.aula.sede_id,
            "periodo": self.periodo.pk, "semestre": self.grupo.semestre_id}

    def nuevo(self, inicio=time(8), fin=time(9), dia="LU", oferta=None, aula=None):
        h = Horario(oferta=oferta or self.oferta, sede=self.aula.sede, aula=aula, dia=dia, hora_inicio=inicio, hora_fin=fin)
        h.save()
        return h

    def crear(self, **cambios):
        datos = {"oferta_id": self.oferta.pk, "dia": "LU", "hora_inicio": "08:00", "hora_fin": "09:00"}
        datos.update(cambios)
        return self.client.post(reverse("crear_horario_oferta") + "?" + urlencode(self.filtros), json.dumps(datos), content_type="application/json")

    def asignar(self, h, aula):
        return self.client.post(reverse("asignar_aula_horario") + "?" + urlencode(self.filtros),
            json.dumps({"horario_id": h.pk, "aula_id": aula.pk}), content_type="application/json")

    def cambiar(self, h, fin="10:00", inicio="08:00", dia="LU", resize=True):
        return self.client.post(reverse("redimensionar_horario" if resize else "mover_horario"),
            json.dumps({"horario_id": h.pk, "dia": dia, "hora_inicio": inicio, "hora_fin": fin}), content_type="application/json")

    def test_horario_valido_sin_aula(self):
        h = self.nuevo()
        self.assertIsNone(h.aula_id)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 1)

    def test_sin_aula_reserva_profesor(self):
        self.nuevo()
        with self.assertRaisesMessage(ValidationError, "El profesor"):
            self.nuevo(oferta=self.nueva_oferta(self.profesor))

    def test_sin_aula_reserva_grupo(self):
        self.nuevo()
        OfertaGrupo.objects.create(oferta=self.otra_oferta, grupo=self.grupo, cupos=10)
        with self.assertRaisesMessage(ValidationError, "El grupo"):
            self.nuevo(oferta=self.otra_oferta)

    def test_sin_aula_disponibilidad_obligatoria(self):
        self.disponibilidad([])
        with self.assertRaises(ValidationError): self.nuevo()

    def test_sin_aula_carga_obligatoria(self):
        CargaDocente.objects.filter(profesor=self.profesor).delete()
        with self.assertRaises(ValidationError): self.nuevo()

    def test_sin_aula_no_comprueba_ocupacion_fisica(self):
        self.nuevo(aula=self.aula, oferta=self.otra_oferta)
        self.nuevo()
        self.assertEqual(Horario.objects.count(), 2)

    def test_asignar_aula_valida(self):
        h = self.nuevo()
        response = self.asignar(h, self.aula)
        self.assertEqual(response.status_code, 200)
        h.refresh_from_db(); self.assertEqual(h.aula_id, self.aula.pk)
        self.assertEqual(response.json()["event"]["classNames"], ["evento-completo"])

    def test_asignar_aula_ocupada_rechazado(self):
        h = self.nuevo()
        self.nuevo(oferta=self.otra_oferta, aula=self.aula)
        response = self.asignar(h, self.aula)
        self.assertEqual(response.status_code, 400)
        h.refresh_from_db(); self.assertIsNone(h.aula_id)

    def test_aula_otra_sede_rechazada(self):
        h = self.nuevo()
        sede = Sede.objects.create(codigo="OTRA", nombre="Otra Sede", centro_tutorial=self.grupo.centro_tutorial)
        aula = Aula.objects.create(codigo="OTRA", nombre="Otra Aula", sede=sede)
        self.assertEqual(self.asignar(h, aula).status_code, 404)
        h.refresh_from_db(); self.assertIsNone(h.aula_id)

    def test_cambio_aula_fallido_conserva_anterior(self):
        h = self.nuevo(aula=self.aula)
        self.nuevo(oferta=self.otra_oferta, aula=self.otra_aula)
        self.assertEqual(self.asignar(h, self.otra_aula).status_code, 400)
        h.refresh_from_db(); self.assertEqual(h.aula_id, self.aula.pk)

    def test_drop_crea_una_hora_sin_aula(self):
        response = self.crear()
        self.assertEqual(response.status_code, 201)
        h = Horario.objects.get(pk=response.json()["horario_id"])
        self.assertIsNone(h.aula_id)
        self.assertEqual((h.hora_inicio, h.hora_fin), (time(8), time(9)))
        self.assertEqual(response.json()["event"]["classNames"], ["evento-pendiente"])
        self.assertEqual(response.json()["event"]["extendedProps"]["aula"], "Aula pendiente")

    def test_drop_fuera_disponibilidad(self):
        self.disponibilidad([("LU", time(8), time(12))])
        self.assertEqual(self.crear(hora_inicio="12:00", hora_fin="13:00").status_code, 400)
        self.assertFalse(Horario.objects.exists())

    def test_drop_exceso_carga(self):
        self.carga(0)
        self.assertEqual(self.crear().status_code, 400)

    def test_drop_conflicto_profesor(self):
        self.nuevo()
        self.assertEqual(self.crear().status_code, 400)

    def test_drop_conflicto_grupo(self):
        OfertaGrupo.objects.create(oferta=self.otra_oferta, grupo=self.grupo, cupos=10)
        self.nuevo(oferta=self.otra_oferta)
        response = self.crear()
        self.assertEqual(response.status_code, 400)
        self.assertIn("El grupo", str(response.json()["errors"]))

    def test_resize_una_a_dos_horas(self):
        h = self.nuevo()
        self.assertEqual(self.cambiar(h).status_code, 200)
        h.refresh_from_db(); self.assertEqual(h.hora_fin, time(10))

    def test_resize_menor_una_hora(self):
        h = self.nuevo()
        self.assertEqual(self.cambiar(h, fin="08:30").status_code, 400)
        h.refresh_from_db(); self.assertEqual(h.hora_fin, time(9))

    def test_resize_una_hora_exacta(self):
        h = self.nuevo(fin=time(10))
        self.assertEqual(self.cambiar(h, fin="09:00").status_code, 200)

    def test_resize_fuera_disponibilidad(self):
        self.disponibilidad([("LU", time(8), time(10))])
        h = self.nuevo()
        self.assertEqual(self.cambiar(h, fin="11:00").status_code, 400)

    def test_resize_exceso_carga(self):
        self.carga(1); h = self.nuevo()
        self.assertEqual(self.cambiar(h).status_code, 400)

    def test_resize_aula_ocupada(self):
        h = self.nuevo(aula=self.aula)
        self.nuevo(time(9), time(10), oferta=self.otra_oferta, aula=self.aula)
        response = self.cambiar(h)
        self.assertEqual(response.status_code, 400)
        self.assertIn("El aula", str(response.json()["errors"]))

    def test_resize_rechazado_no_modifica_db(self):
        h = self.nuevo()
        anterior = list(Horario.objects.order_by("pk").values())
        self.carga(1)
        self.assertEqual(self.cambiar(h).status_code, 400)
        self.assertEqual(anterior, list(Horario.objects.order_by("pk").values()))

    def test_resize_no_duplica_carga(self):
        self.carga(3)
        h = self.nuevo()
        self.nuevo(dia="MA")
        self.assertEqual(self.cambiar(h).status_code, 200)
        self.assertEqual(calcular_horas_planificadas(self.profesor, self.periodo), 3)

    def test_movimiento_sin_aula(self):
        h = self.nuevo()
        self.assertEqual(self.cambiar(h, dia="MA", fin="09:00", resize=False).status_code, 200)
        h.refresh_from_db(); self.assertEqual(h.dia, "MA"); self.assertIsNone(h.aula_id)

    def test_movimiento_con_aula_valida_conflictos(self):
        h = self.nuevo(aula=self.aula)
        self.nuevo(dia="MA", oferta=self.otra_oferta, aula=self.aula)
        self.assertEqual(self.cambiar(h, dia="MA", fin="09:00", resize=False).status_code, 400)
        h.refresh_from_db(); self.assertEqual(h.dia, "LU"); self.assertEqual(h.aula_id, self.aula.pk)

    def test_movimiento_rechazado_conserva_datos(self):
        h = self.nuevo()
        DisponibilidadProfesor.objects.filter(profesor=self.profesor, dia="MA").delete()
        self.assertEqual(self.cambiar(h, dia="MA", fin="09:00", resize=False).status_code, 400)
        h.refresh_from_db(); self.assertEqual(h.dia, "LU"); self.assertIsNone(h.aula_id)

    def test_mensaje_sin_disponibilidad_del_dia(self):
        self.disponibilidad([("VI", time(13), time(17))])
        response = self.crear(dia="MA")
        mensaje = str(response.json()["errors"])
        self.assertIn("no tiene disponibilidad registrada para el martes", mensaje)
        self.assertIn("Viernes 13:00–17:00", mensaje)

    def test_mensaje_fuera_de_franja(self):
        self.disponibilidad([("VI", time(13), time(17))])
        response = self.crear(dia="VI", hora_inicio="17:00", hora_fin="18:00")
        mensaje = str(response.json()["errors"])
        self.assertIn("fuera de la disponibilidad", mensaje)
        self.assertIn("Horario solicitado: 17:00–18:00", mensaje)
        self.assertIn("Disponibilidad del viernes: 13:00–17:00", mensaje)

    def test_usuario_sin_add_no_crea(self):
        usuario = get_user_model().objects.create_user(username="lector_aula")
        self.client.force_login(usuario)
        self.assertEqual(self.crear().status_code, 403)

    def test_usuario_sin_change_no_modifica(self):
        h = self.nuevo()
        usuario = get_user_model().objects.create_user(username="sin_change_aula")
        self.client.force_login(usuario)
        self.assertEqual(self.cambiar(h).status_code, 403)
        self.assertEqual(self.cambiar(h, fin="09:00", resize=False).status_code, 403)
        self.assertEqual(self.asignar(h, self.aula).status_code, 403)

    def test_minimo_tambien_en_creacion(self):
        self.assertEqual(self.crear(hora_fin="08:30").status_code, 400)

    def test_resize_no_cambia_inicio_ni_dia(self):
        h = self.nuevo()
        self.assertEqual(self.cambiar(h, inicio="09:00", fin="11:00").status_code, 400)
        self.assertEqual(self.cambiar(h, dia="MA").status_code, 400)

    def test_aulas_reales_del_contexto_y_eventos_pendientes(self):
        h = self.nuevo()
        response = self.client.get(reverse("aulas_horario_calendario", args=[h.pk]), self.filtros)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({a["id"] for a in response.json()["aulas"]}, {self.aula.pk, self.otra_aula.pk})
        eventos = self.client.get(reverse("eventos_calendario"), self.filtros).json()
        self.assertEqual([e["id"] for e in eventos], [str(h.pk)])

    def test_post_csrf_resize_y_aula(self):
        h = self.nuevo(); cliente = Client(enforce_csrf_checks=True); cliente.force_login(self.usuario)
        resize = {"horario_id": h.pk, "dia": "LU", "hora_inicio": "08:00", "hora_fin": "10:00"}
        url_aula = reverse("asignar_aula_horario") + "?" + urlencode(self.filtros)
        for url, datos in [(reverse("redimensionar_horario"), resize), (url_aula, {"horario_id": h.pk, "aula_id": self.aula.pk})]:
            self.assertEqual(cliente.post(url, json.dumps(datos), content_type="application/json").status_code, 403)
            self.assertEqual(self.client.get(url).status_code, 405)
        cliente.get(reverse("planificacion"), self.filtros)
        response = cliente.post(reverse("redimensionar_horario"), json.dumps(resize), content_type="application/json", HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_actualizacion_parcial_no_usa_horas_desactualizadas(self):
        h = self.nuevo()
        copia = Horario.objects.get(pk=h.pk)
        h.hora_inicio = time(10); h.hora_fin = time(11); h.save()
        self.nuevo(time(10), time(11), oferta=self.otra_oferta, aula=self.aula)
        copia.aula = self.aula
        with self.assertRaisesMessage(ValidationError, "El aula"):
            copia.save(update_fields=["aula"])
        h.refresh_from_db(); self.assertIsNone(h.aula_id)

    def test_edicion_tradicional_y_exportacion_sin_aula(self):
        h = self.nuevo()
        response = self.client.get(reverse("editar_asignacion", args=[h.pk]), {"sede": self.aula.sede_id})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("exportar_excel"), {**self.filtros, "nivel": "periodo"})
        self.assertEqual(response.status_code, 200)
        from io import BytesIO
        from openpyxl import load_workbook
        libro = load_workbook(BytesIO(response.content), read_only=True)
        filas = list(libro.active.values)
        self.assertTrue(any("Aula pendiente" in fila for fila in filas))
        libro.close()


    def test_sede_aula_se_revalida_bajo_bloqueo(self):
        h = self.nuevo()
        h.aula = self.aula
        h._sede_contexto_id = self.aula.sede_id
        otra = Sede.objects.create(codigo="SEDE-CAMBIO", nombre="Sede de Prueba", centro_tutorial=self.grupo.centro_tutorial)
        Aula.objects.filter(pk=self.aula.pk).update(sede=otra)
        with self.assertRaisesMessage(ValidationError, "sede del horario"):
            h.save(update_fields=["aula"])
        h.refresh_from_db()
        self.assertIsNone(h.aula_id)
