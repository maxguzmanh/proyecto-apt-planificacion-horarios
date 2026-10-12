from datetime import time
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from academico.models import (
    Asignatura, CargaDocente, DisponibilidadProfesor, Modalidad, PlanEstudioAsignatura,
    Profesor, Semestre, Sede,
)
from .models import Grupo, Horario, OfertaAcademica, OfertaGrupo
from .services import obtener_panel_academico, obtener_resumen_docente


class PanelAcademicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo", stdout=StringIO())
        cls.usuario = get_user_model().objects.create_superuser(username="panel_prueba", password="Prueba123!")
        cls.grupo = Grupo.objects.select_related("programa__facultad", "periodo", "centro_tutorial", "semestre").get(
            programa__codigo="ING-INF", semestre__numero=5, codigo="05PD G1",
        )
        cls.profesor = Profesor.objects.get(identificacion="DOC-DEMO-001")

    def setUp(self):
        self.client.force_login(self.usuario)

    def panel(self, **kwargs):
        g = self.grupo
        return obtener_panel_academico(g.programa, g.semestre, g.centro_tutorial, g.periodo, **kwargs)

    def respuesta(self):
        g = self.grupo
        return self.client.get(reverse("planificacion"), {
            "centro": g.centro_tutorial_id, "facultad": g.programa.facultad_id,
            "programa": g.programa_id, "periodo": g.periodo_id, "semestre": g.semestre_id, "modalidad": Modalidad.objects.get(codigo="PRE").pk,
            "sede": Sede.objects.get(codigo="SEDE-ACA").pk,
        })

    def test_renderizado_completo_con_profesor(self):
        response = self.respuesta()
        self.assertEqual(response.status_code, 200)
        for texto in ["PROGWEB01", "Programación Web", "Laura Méndez", "Informática",
                      "05PD G1", "Presencial", "Horas planificadas", "Disponibilidad"]:
            self.assertContains(response, texto)
        self.assertContains(response, 'form="filtros-planificacion"')
        self.assertTrue(response.context["asignaturas_semestre"])

    def test_asignatura_sin_oferta(self):
        asignatura = Asignatura.objects.create(codigo="SIN-OFERTA", nombre="Asignatura sin oferta")
        PlanEstudioAsignatura.objects.create(programa=self.grupo.programa,
            semestre=self.grupo.semestre, asignatura=asignatura, creditos=4)
        response = self.respuesta()
        self.assertContains(response, "Sin profesor asignado")
        tarjeta = next(t for t in response.context["asignaturas_semestre"] if t["plan"].asignatura_id == asignatura.pk)
        self.assertEqual(tarjeta["profesores"], [])

    def test_sin_carga_y_sin_disponibilidad(self):
        CargaDocente.objects.filter(profesor=self.profesor).delete()
        DisponibilidadProfesor.objects.filter(profesor=self.profesor).delete()
        response = self.respuesta()
        self.assertContains(response, "Carga docente no registrada")
        self.assertContains(response, "Disponibilidad no registrada")
        docente = next(d for t in self.panel() for d in t["profesores"] if d["profesor"].pk == self.profesor.pk)
        self.assertIsNone(docente["carga"])
        self.assertIsNone(docente["horas_pendientes"])
        self.assertEqual(docente["horas_planificadas"], Decimal("4"))

    def test_carga_disponibilidad_y_totales_reales(self):
        carga = CargaDocente.objects.get(profesor=self.profesor, periodo=self.grupo.periodo, activo=True)
        carga.horas_asignadas = Decimal("12.50")
        carga.save()
        response = self.respuesta()
        self.assertContains(response, "12.50 h")
        self.assertContains(response, "8.50 h")
        self.assertContains(response, "08:00–20:00")
        docentes = [d for t in response.context["asignaturas_semestre"] for d in t["profesores"] if d["profesor"].pk == self.profesor.pk]
        for docente in docentes:
            self.assertEqual(docente["horas_planificadas"], Decimal("4"))
            self.assertEqual(docente["horas_pendientes"], Decimal("8.50"))

    def test_oferta_sin_horario_muestra_profesor(self):
        asignatura = Asignatura.objects.create(codigo="SIN-HORARIO", nombre="Oferta sin horario")
        PlanEstudioAsignatura.objects.create(programa=self.grupo.programa,
            semestre=self.grupo.semestre, asignatura=asignatura, creditos=2)
        oferta = OfertaAcademica.objects.create(asignatura=asignatura, profesor=self.profesor,
            periodo=self.grupo.periodo, modalidad=Modalidad.objects.get(codigo="PRE"))
        OfertaGrupo.objects.create(oferta=oferta, grupo=self.grupo, cupos=10)
        tarjeta = next(t for t in self.panel() if t["plan"].asignatura_id == asignatura.pk)
        self.assertEqual(len(tarjeta["profesores"]), 1)
        self.assertEqual(tarjeta["profesores"][0]["profesor"], self.profesor)

    def test_filtro_grupo_y_sede_no_recorta_totales_docentes(self):
        sede = Sede.objects.get(codigo="SEDE-ACA")
        tarjetas = self.panel(grupo=self.grupo, sede=sede)
        for tarjeta in tarjetas:
            self.assertTrue(all(g.pk == self.grupo.pk for g in tarjeta["grupos"]))
        docentes = [d for t in tarjetas for d in t["profesores"] if d["profesor"].pk == self.profesor.pk]
        self.assertTrue(docentes)
        self.assertEqual(docentes[0]["horas_planificadas"], Decimal("4"))
        sala_sin_clases = Sede.objects.get(codigo="SEDE-VIR")
        self.assertTrue(all(not t["profesores"] for t in self.panel(sede=sala_sin_clases)))

    def test_transversal_no_duplica_horas_y_grupos_del_contexto(self):
        g = Grupo.objects.get(programa__codigo="ING-INF", semestre__numero=1)
        tarjetas = obtener_panel_academico(g.programa, g.semestre, g.centro_tutorial, g.periodo)
        tarjeta = next(t for t in tarjetas if t["plan"].asignatura.codigo == "COMP001")
        self.assertEqual([grupo.pk for grupo in tarjeta["grupos"]], [g.pk])
        self.assertEqual(len(tarjeta["profesores"]), 1)
        self.assertEqual(tarjeta["profesores"][0]["horas_planificadas"], Decimal("2"))

    def test_oferta_inactiva_y_bloques_inactivos_no_se_muestran(self):
        OfertaAcademica.objects.filter(asignatura__codigo="PROGWEB01").update(activo=False)
        tarjeta = next(t for t in self.panel() if t["plan"].asignatura.codigo == "PROGWEB01")
        self.assertEqual(tarjeta["profesores"], [])
        DisponibilidadProfesor.objects.filter(profesor=self.profesor).update(activo=False)
        resumen = obtener_resumen_docente([self.profesor], self.grupo.periodo)
        self.assertEqual(resumen[self.profesor.pk]["disponibilidad"], [])

    def test_consultas_constantes_con_mas_asignaturas_y_profesores(self):
        with CaptureQueriesContext(connection) as inicial:
            self.panel()
        modalidad = Modalidad.objects.get(codigo="PRE")
        for numero in range(5):
            profesor = Profesor.objects.create(identificacion=f"DOC-PANEL-{numero}", nombre="Docente", apellido=f"Prueba {numero}")
            asignatura = Asignatura.objects.create(codigo=f"ASIG-PANEL-{numero}", nombre=f"Asignatura {numero}")
            PlanEstudioAsignatura.objects.create(programa=self.grupo.programa, semestre=self.grupo.semestre,
                asignatura=asignatura, creditos=2)
            oferta = OfertaAcademica.objects.create(asignatura=asignatura, profesor=profesor,
                periodo=self.grupo.periodo, modalidad=modalidad)
            OfertaGrupo.objects.create(oferta=oferta, grupo=self.grupo, cupos=10)
        with CaptureQueriesContext(connection) as ampliado:
            tarjetas = self.panel()
        self.assertEqual(len(inicial), 6)
        self.assertEqual(len(ampliado), len(inicial))
        with self.assertNumQueries(0):
            for t in tarjetas:
                str(t["plan"].asignatura)
                for docente in t["profesores"]:
                    str(docente["profesor"])
                    for oferta in docente["ofertas"]:
                        str(oferta.modalidad)
                        list(oferta.grupos_contexto)

    def test_renderizado_sin_filtros(self):
        response = self.client.get(reverse("planificacion"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["asignaturas_semestre"], [])
