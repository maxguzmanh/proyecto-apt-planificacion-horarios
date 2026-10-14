import json
from datetime import time
from urllib.parse import urlencode
from django.test import TestCase
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from academico.models import Sede,Modalidad,DisponibilidadProfesor
from .models import Horario,OfertaGrupo
from .test_validacion_docente import DatosDocencia
from . import test_ocupaciones as base_ocupaciones

class DisponibilidadVisualTests(DatosDocencia,TestCase):
    setUp=base_ocupaciones.OcupacionesTests.setUp
    get=base_ocupaciones.OcupacionesTests.get
    def test_disponibilidad_profesor_real_y_periodo(self):
        self.condiciones(self.profesor,self.otro_periodo)
        d=self.get(profesor_id=self.otro_profesor.pk).json()
        self.assertEqual(d["profesor"],str(self.profesor));self.assertEqual(d["periodo"],self.periodo.codigo);self.assertEqual(len(d["disponibilidad"]),7)
    def test_multiples_bloques_y_dias_ausentes(self):
        self.disponibilidad([("LU",time(8),time(12)),("LU",time(14),time(18))])
        d=self.get().json()["disponibilidad"]
        self.assertEqual(len(d),2);self.assertEqual({b["dia"] for b in d},{"LU"})
    def test_excluye_inactivos(self):
        DisponibilidadProfesor.objects.filter(profesor=self.profesor,dia="JU").update(activo=False)
        self.assertNotIn("JU",[b["dia"] for b in self.get().json()["disponibilidad"]])
    def test_sin_disponibilidad(self):
        self.disponibilidad([]);self.assertEqual(self.get().json()["disponibilidad"],[])
    def test_consultas_constantes(self):
        with CaptureQueriesContext(connection) as antes: self.get()
        for inicio in [10,12,14]: Horario.objects.create(oferta=self.externa,sede=self.sede,dia="LU",hora_inicio=time(inicio),hora_fin=time(inicio+1))
        with CaptureQueriesContext(connection) as despues: self.get()
        self.assertEqual(len(antes),len(despues))
    def test_sin_escrituras(self):
        antes=list(Horario.objects.order_by("pk").values());self.get();self.assertEqual(antes,list(Horario.objects.order_by("pk").values()))

class ModalidadSedeVisualTests(DatosDocencia,TestCase):
    setUp=base_ocupaciones.OcupacionesTests.setUp
    def modalidades(self):
        self.virtual=Modalidad.objects.create(codigo="VIR",nombre="Virtual")
        self.hibrida=Modalidad.objects.create(codigo="HIB",nombre="Híbrida")
        self.campus=Sede.objects.create(codigo="SEDE-VIR",nombre="Nombre no usado para identificar",centro_tutorial=self.grupo.centro_tutorial)
        self.ofertas_modalidad={}
        for m in [self.virtual,self.hibrida]:
            o=self.nueva_oferta(self.profesor);o.modalidad=m;o.save();OfertaGrupo.objects.create(oferta=o,grupo=self.grupo,cupos=10)
            self.ofertas_modalidad[m.codigo]=o
    def sedes(self,m):return self.client.get(reverse("cargar_sedes"),{"centro":self.grupo.centro_tutorial_id,"modalidad":m.pk}).json()
    def test_parametro_virtual_no_filtra_sedes(self):
        self.modalidades();self.assertEqual({s["id"] for s in self.sedes(self.virtual)},{self.aula.sede_id,self.campus.pk})
    def test_parametro_presencial_no_filtra_sedes(self):
        self.modalidades();self.assertEqual({s["id"] for s in self.sedes(self.modalidad)},{self.aula.sede_id,self.campus.pk})
    def test_hibrida_ambas(self):
        self.modalidades();self.assertEqual({s["id"] for s in self.sedes(self.hibrida)},{self.aula.sede_id,self.campus.pk})
    def test_campus_inactivo_no_aparece(self):
        self.modalidades();self.campus.activo=False;self.campus.save();self.assertEqual([s["id"] for s in self.sedes(self.virtual)],[self.aula.sede_id])
    def test_virtual_sede_fisica_rechazada(self):
        self.modalidades();antes=Horario.objects.count()
        r=self.client.post(reverse("crear_horario_oferta")+"?"+urlencode(self.filtros),json.dumps({"oferta_id":self.ofertas_modalidad["VIR"].pk,"dia":"LU","hora_inicio":"10:00","hora_fin":"11:00"}),content_type="application/json")
        self.assertEqual(r.status_code,404);self.assertEqual(Horario.objects.count(),antes)
    def test_contexto_campus_no_incluye_horarios_fisicos(self):
        self.modalidades();r=self.client.get(reverse("eventos_calendario"),{**self.filtros,"sede":self.campus.pk});self.assertEqual(r.status_code,200);self.assertEqual(r.json(),[])
    def test_post_manipulado_no_crea(self):
        self.modalidades();antes=Horario.objects.count()
        r=self.client.post(reverse("crear_horario_oferta")+"?"+urlencode({**self.filtros,"sede":self.campus.pk}),json.dumps({"oferta_id":self.oferta.pk,"dia":"LU","hora_inicio":"10:00","hora_fin":"11:00"}),content_type="application/json")
        self.assertEqual(r.status_code,404);self.assertEqual(Horario.objects.count(),antes)
