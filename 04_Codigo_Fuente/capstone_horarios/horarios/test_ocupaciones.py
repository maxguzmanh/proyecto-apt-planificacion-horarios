import json
from datetime import time
from urllib.parse import urlencode
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from academico.models import CentroTutorial,Sede,ProgramaAcademico,Facultad,DisponibilidadProfesor
from .models import Horario,OfertaGrupo,Grupo
from .test_validacion_docente import DatosDocencia
from .presentacion import respuesta_error,horarios_con_contexto,evento_con_contexto

class OcupacionesTests(DatosDocencia,TestCase):
    def setUp(self):
        self.crear_datos()
        OfertaGrupo.objects.create(oferta=self.oferta,grupo=self.grupo,cupos=10)
        self.user=get_user_model().objects.create_superuser(username="contexto_demo",password="demo")
        self.client.force_login(self.user)
        self.filtros={"centro":self.grupo.centro_tutorial_id,"facultad":self.grupo.programa.facultad_id,"programa":self.grupo.programa_id,"modalidad":self.modalidad.pk,"sede":self.aula.sede_id,"periodo":self.periodo.pk,"semestre":self.grupo.semestre_id}
        centro=CentroTutorial.objects.create(codigo="CT-EXT",nombre="Centro Externo")
        self.sede=Sede.objects.create(codigo="SEDE-EXT",nombre="Sede Externa",centro_tutorial=centro)
        fac=Facultad.objects.create(codigo="FAC-EXT",nombre="Facultad Externa")
        programa=ProgramaAcademico.objects.create(codigo="PROG-EXT",nombre="Programa Externo",facultad=fac)
        grupo=Grupo.objects.create(codigo="G-EXT",programa=programa,centro_tutorial=centro,semestre=self.grupo.semestre,periodo=self.periodo)
        self.externa=self.nueva_oferta(self.profesor)
        OfertaGrupo.objects.create(oferta=self.externa,grupo=grupo,cupos=10)
        self.h=Horario.objects.create(oferta=self.externa,sede=self.sede,dia="LU",hora_inicio=time(8),hora_fin=time(9))
        self.url=reverse("ocupaciones_oferta",args=[self.oferta.pk])
    def get(self,**extras): return self.client.get(self.url,{**self.filtros,**extras})
    def test_otra_sede(self): self.assertEqual(self.get().json()[0]["extendedProps"]["sede"],"Sede Externa")
    def test_otro_programa(self): self.assertEqual(self.get().json()[0]["extendedProps"]["programas"],["Programa Externo"])
    def test_otro_centro(self): self.assertEqual(self.get().json()[0]["extendedProps"]["centros"],["Centro Externo"])
    def test_serializacion(self):
        p=self.get().json()[0]["extendedProps"]
        self.assertEqual(p["aula"],"Aula pendiente"); self.assertEqual(p["grupos"][0]["codigo"],"G-EXT")
        for key in ["facultades","modalidad","periodo","semestres","hora_inicio","hora_fin"]: self.assertTrue(p[key])
    def test_no_duplica_visible(self):
        Horario.objects.create(oferta=self.oferta,sede=self.aula.sede,dia="LU",hora_inicio=time(9),hora_fin=time(10))
        self.assertEqual(len(self.get().json()),1)
    def test_login(self): self.client.logout(); self.assertEqual(self.get().status_code,401)
    def test_permiso(self):
        u=get_user_model().objects.create_user(username="sin_permiso");self.client.force_login(u);self.assertEqual(self.get().status_code,403)
    def test_profesor_desde_oferta(self): self.assertEqual(len(self.get(profesor_id=self.otro_profesor.pk).json()),1)
    def test_solo_periodo_actual(self):
        self.condiciones(self.profesor,self.otro_periodo)
        o=self.nueva_oferta(self.profesor,self.otro_periodo)
        Horario.objects.create(oferta=o,sede=self.sede,dia="LU",hora_inicio=time(8),hora_fin=time(9))
        self.assertEqual(len(self.get().json()),1)
    def test_solo_activos(self):
        self.h.activo=False;self.h.save();self.assertEqual(self.get().json(),[])
    def test_json_conflicto_neutral_y_contexto(self):
        r=self.client.post(reverse("crear_horario_oferta")+"?"+urlencode(self.filtros),json.dumps({"oferta_id":self.oferta.pk,"dia":"LU","hora_inicio":"08:00","hora_fin":"09:00"}),content_type="application/json")
        self.assertEqual(r.status_code,400);data=r.json()
        self.assertTrue(data["errors"]["oferta"][0].startswith("Ana Prueba ya tiene"))
        self.assertNotIn("El profesor",data["errors"]["oferta"][0])
        self.assertEqual(data["conflicto_profesor"]["extendedProps"]["sede"],"Sede Externa")
        self.assertNotIn("disponibilidad",str(data["errors"]))
    def test_disponibilidad_no_elimina_ocupacion(self):
        h=Horario(oferta=self.oferta,sede=self.aula.sede,dia="LU",hora_inicio=time(8),hora_fin=time(9))
        with self.assertRaises(ValidationError) as error: h.full_clean()
        self.assertIn("ya tiene",str(error.exception));self.assertNotIn("fuera de la disponibilidad",str(error.exception))
    def test_no_n_mas_uno(self):
        with self.assertNumQueries(2):
            rows=list(horarios_con_contexto(Horario.objects.all()))
            eventos=[evento_con_contexto(h) for h in rows]
        self.assertEqual(len(eventos),1)
    def test_referencias_solo_lectura(self):
        e=self.get().json()[0];self.assertFalse(e["editable"]);self.assertFalse(e["durationEditable"])
        self.assertTrue(e["extendedProps"]["ocupacion_externa"])
    def test_contexto_incompleto(self): self.assertEqual(self.client.get(self.url).status_code,400)
