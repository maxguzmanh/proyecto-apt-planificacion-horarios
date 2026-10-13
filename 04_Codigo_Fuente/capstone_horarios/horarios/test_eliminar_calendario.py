import json
from datetime import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, Client
from django.urls import reverse
from .test_validacion_docente import DatosDocencia
from .models import Horario, OfertaGrupo
from .services import calcular_horas_planificadas, calcular_horas_pendientes

class EliminarCalendarioTests(DatosDocencia, TestCase):
    def setUp(self):
        self.crear_datos()
        self.user = get_user_model().objects.create_user(username="eliminador")
        self.user.user_permissions.add(Permission.objects.get(codename="delete_horario", content_type__app_label="horarios"))
        self.client.force_login(self.user)
        self.url = reverse("eliminar_horario_calendario")
        self.h = self.crear()
    def crear(self, inicio=8, aula=True):
        return Horario.objects.create(oferta=self.oferta, sede=self.aula.sede, aula=self.aula if aula else None, dia="LU", hora_inicio=time(inicio), hora_fin=time(inicio+1))
    def borrar(self, pk=None, client=None):
        return (client or self.client).post(self.url, json.dumps({"horario_id": pk or self.h.pk}), content_type="application/json")
    def test_eliminacion_valida(self):
        self.assertEqual(self.borrar().status_code,200)
        self.assertFalse(Horario.objects.filter(pk=self.h.pk).exists())
    def test_pendiente(self):
        h=self.crear(9,False); self.assertEqual(self.borrar(h.pk).status_code,200)
        self.assertFalse(Horario.objects.filter(pk=h.pk).exists())
    def test_conserva_otros(self):
        h=self.crear(9); antes=(h.sede_id,h.aula_id,h.oferta_id,h.dia,h.hora_inicio,h.hora_fin)
        self.borrar(); h.refresh_from_db()
        self.assertEqual(antes,(h.sede_id,h.aula_id,h.oferta_id,h.dia,h.hora_inicio,h.hora_fin))
    def test_autenticacion(self):
        self.client.logout(); self.assertEqual(self.borrar().status_code,401)
        self.assertTrue(Horario.objects.filter(pk=self.h.pk).exists())
    def test_permiso(self):
        self.user.user_permissions.clear(); self.assertEqual(self.borrar().status_code,403)
        self.assertTrue(Horario.objects.filter(pk=self.h.pk).exists())
    def test_change_no_autoriza_delete(self):
        self.user.user_permissions.clear()
        self.user.user_permissions.add(Permission.objects.get(codename="change_horario",content_type__app_label="horarios"))
        self.assertEqual(self.borrar().status_code,403)
    def test_get(self):
        self.assertEqual(self.client.get(self.url).status_code,405)
        self.assertTrue(Horario.objects.filter(pk=self.h.pk).exists())
    def test_inexistente(self): self.assertEqual(self.borrar(999999).status_code,404)
    def test_resta_horas(self):
        antes=calcular_horas_planificadas(self.profesor,self.periodo); self.borrar()
        self.assertEqual(calcular_horas_planificadas(self.profesor,self.periodo),antes-1)
    def test_incrementa_pendientes(self):
        antes=calcular_horas_pendientes(self.profesor,self.periodo); self.borrar()
        self.assertEqual(calcular_horas_pendientes(self.profesor,self.periodo),antes+1)
    def test_transversal(self):
        from .models import Grupo
        g=Grupo.objects.create(codigo="G-DEMO-2", programa=self.grupo.programa,centro_tutorial=self.grupo.centro_tutorial,periodo=self.periodo,semestre=self.grupo.semestre)
        OfertaGrupo.objects.create(oferta=self.oferta,grupo=self.grupo,cupos=10)
        OfertaGrupo.objects.create(oferta=self.oferta,grupo=g,cupos=10)
        self.assertEqual(calcular_horas_planificadas(self.profesor,self.periodo),1)
        self.borrar(); self.assertEqual(calcular_horas_planificadas(self.profesor,self.periodo),0)
        self.assertEqual(OfertaGrupo.objects.filter(oferta=self.oferta).count(),2)
    def test_csrf(self):
        c=Client(enforce_csrf_checks=True); c.force_login(self.user)
        self.assertEqual(self.borrar(client=c).status_code,403)
        self.assertTrue(Horario.objects.filter(pk=self.h.pk).exists())
    def test_payload_invalido(self):
        for datos in ({}, {"horario_id":True}, {"horario_id":self.h.pk,"sede":1}, {"horario_id":"1"}):
            self.assertEqual(self.client.post(self.url,json.dumps(datos),content_type="application/json").status_code,400)
    def test_reutiliza_bloqueo(self):
        from . import services
        with patch("horarios.services.operacion_planificacion", wraps=services.operacion_planificacion) as bloqueo:
            self.assertEqual(self.borrar().status_code,200)
            self.assertEqual(bloqueo.call_args.args[0],[self.profesor.pk])
