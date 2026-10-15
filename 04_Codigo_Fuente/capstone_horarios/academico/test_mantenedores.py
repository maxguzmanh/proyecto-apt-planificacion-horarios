from datetime import time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from horarios.test_validacion_docente import DatosDocencia
from horarios.models import Grupo
from .views import MANTENEDORES
from .models import AreaAcademica,Profesor,Facultad,ProgramaAcademico,CentroTutorial,ProgramaCentroTutorial,Semestre,PlanEstudioAsignatura
from .forms import GrupoForm

class MantenedoresExperienciaTests(DatosDocencia,TestCase):
    def setUp(self):
        self.crear_datos()
        self.admin=get_user_model().objects.create_superuser(username="admin_catalogos",password="demo")
        self.normal=get_user_model().objects.create_user(username="operador_catalogos",is_staff=True)
        self.area=AreaAcademica.objects.create(codigo="AREA-FIC",nombre="Área Ficticia")
        self.recurso=Profesor.objects.create(identificacion="DOC-RECURSO-FIC",nombre="Recurso",apellido="Ficticio")
        self.client.force_login(self.admin)
    def permitir(self,c):
        meta=c["modelo"]._meta
        self.normal.user_permissions.add(Permission.objects.get(content_type__app_label=meta.app_label,codename=f"view_{meta.model_name}"))
    def payload(self,clave):
        base={"codigo":"CRUD-FIC","nombre":"Registro Ficticio","activo":"on"}
        return {
            "centros":base,"sedes":{**base,"centro_tutorial":self.grupo.centro_tutorial_id},"facultades":base,
            "programas":{**base,"facultad":self.grupo.programa.facultad_id,"centros_tutoriales":[self.grupo.centro_tutorial_id]},
            "periodos":{**base,"fecha_inicio":"2027-01-01","fecha_fin":"2027-06-30"},"semestres":{"numero":9},"modalidades":base,"areas":base,"asignaturas":base,
            "planes":{"programa":self.grupo.programa_id,"asignatura":self.asignatura.pk,"semestre":self.grupo.semestre_id,"creditos":3,"area_academica":self.area.pk,"activo":"on"},
            "profesores":{"identificacion":"DOC-CRUD-FIC","nombre":"Registro","apellido":"Ficticio","activo":"on"},
            "disponibilidades":{"profesor":self.recurso.pk,"periodo":self.periodo.pk,"dia":"LU","hora_inicio":"08:00","hora_fin":"12:00","activo":"on"},
            "cargas_docentes":{"profesor":self.recurso.pk,"periodo":self.periodo.pk,"horas_asignadas":8,"activo":"on"},
            "aulas":{**base,"sede":self.aula.sede_id,"capacidad":20,"tipo":self.aula.tipo},
            "grupos":{"codigo":"CRUD-G-FIC","programa":self.grupo.programa_id,"centro_tutorial":self.grupo.centro_tutorial_id,"periodo":self.periodo.pk,"semestre":self.grupo.semestre_id,"activo":"on"},
        }[clave]
    def crear(self,clave,c):
        datos=self.payload(clave)
        if clave=="planes": datos["semestre"]=Semestre.objects.get_or_create(numero=8)[0].pk
        prev=set(c["modelo"].objects.values_list("pk",flat=True))
        r=self.client.post(reverse(c["crear_url"]),datos)
        self.assertEqual(r.status_code,302,str(r.context["form"].errors) if r.context and "form" in r.context else r.content[:300])
        objeto=c["modelo"].objects.exclude(pk__in=prev).get()
        return objeto,datos
    def test_todas_rutas_y_crud(self):
        for clave,c in MANTENEDORES.items():
            with self.subTest(mantenedor=clave):
                self.assertEqual(self.client.get(reverse(c["listado_url"])).status_code,200)
                self.assertEqual(self.client.get(reverse(c["crear_url"])).status_code,200)
                objeto,datos=self.crear(clave,c)
                self.assertEqual(self.client.get(reverse(c["editar_url"],args=[objeto.pk])).status_code,200)
                self.assertEqual(self.client.get(reverse(c["eliminar_url"],args=[objeto.pk])).status_code,200)
                if "nombre" in datos: datos["nombre"]="Registro Editado"
                elif clave=="profesores": datos["apellido"]="Editado"
                elif clave=="semestres": datos["numero"]=10
                elif clave=="planes": datos["creditos"]=4
                elif clave=="cargas_docentes": datos["horas_asignadas"]=9
                elif clave=="disponibilidades": datos["hora_fin"]="13:00"
                else: datos["codigo"]="CRUD-EDITADO"
                self.assertEqual(self.client.post(reverse(c["editar_url"],args=[objeto.pk]),datos).status_code,302)
                objeto.refresh_from_db()
                if "nombre" in datos:self.assertEqual(objeto.nombre,"Registro Editado")
                if c["mostrar_estado"]:
                    inactivo={k:v for k,v in datos.items() if k!="activo"}
                    self.assertEqual(self.client.post(reverse(c["editar_url"],args=[objeto.pk]),inactivo).status_code,302)
                    objeto.refresh_from_db();self.assertFalse(objeto.activo)
                    self.assertEqual(self.client.post(reverse(c["editar_url"],args=[objeto.pk]),datos).status_code,302)
                    objeto.refresh_from_db();self.assertTrue(objeto.activo)
                pk=objeto.pk
                self.assertEqual(self.client.post(reverse(c["eliminar_url"],args=[pk])).status_code,302)
                self.assertFalse(c["modelo"].objects.filter(pk=pk).exists())
    def test_sin_permiso_todos_endpoints(self):
        self.client.force_login(self.normal)
        for c in MANTENEDORES.values():
            for ruta,args in [(c["listado_url"],[]),(c["crear_url"],[]),(c["editar_url"],[999]),(c["eliminar_url"],[999])]:
                with self.subTest(ruta=ruta):self.assertEqual(self.client.get(reverse(ruta,args=args)).status_code,403)
    def test_con_permiso_consulta_todos(self):
        for c in MANTENEDORES.values():self.permitir(c)
        self.client.force_login(self.normal)
        for c in MANTENEDORES.values():self.assertEqual(self.client.get(reverse(c["listado_url"])).status_code,200)
    def test_sidebar_permisos_y_ruta_activa(self):
        self.permitir(MANTENEDORES["profesores"]);self.client.force_login(self.normal)
        r=self.client.get(reverse("profesores"))
        self.assertEqual([o["nombre"] for o in r.context["menu_mantenedores"]],["Profesores"])
        self.assertTrue(r.context["mantenedores_abierto"]);self.assertContains(r,'id="sidebar-mantenedores" class="sidebar-maintenance" open')
        self.assertTrue(r.context["menu_mantenedores"][0]["activa"])
        self.assertNotContains(r,'href="/admin/"');self.assertNotContains(r,"Administración técnica")
    def test_edicion_mantiene_submenu_abierto(self):
        r=self.client.get(reverse("profesor_editar",args=[self.profesor.pk]));self.assertTrue(r.context["mantenedores_abierto"])
        self.assertTrue(next(o for o in r.context["menu_mantenedores"] if o["ruta"]=="profesores")["activa"])
    def test_superuser_admin_tecnico(self):self.assertContains(self.client.get(reverse("profesores")),"Administración técnica ↗")
    def test_sidebar_todos_15(self):self.assertEqual(len(self.client.get(reverse("profesores")).context["menu_mantenedores"]),15)
    def test_busqueda_nombre_y_total(self):
        r=self.client.get(reverse("profesores"),{"q":"Ana Prueba"})
        self.assertEqual(r.context["total_registros"],3);self.assertEqual(len(r.context["registros"]),1)
    def test_busqueda_relaciones(self):
        r=self.client.get(reverse("aulas"),{"q":"Sede Prueba"});self.assertEqual(len(r.context["registros"]),2)
    def test_busqueda_vacia(self):self.assertContains(self.client.get(reverse("profesores"),{"q":"inexistente"}),"No se encontraron registros")
    def test_busqueda_semestre_romano(self):self.assertEqual(len(self.client.get(reverse("semestres"),{"q":"I"}).context["registros"]),1)
    def test_protect_sin_eliminar(self):
        r=self.client.post(reverse("facultad_eliminar",args=[self.grupo.programa.facultad_id]),follow=True)
        self.assertContains(r,"información asociada");self.assertTrue(Facultad.objects.filter(pk=self.grupo.programa.facultad_id).exists())
    def test_programa_incompatible_rechazado(self):
        centro=CentroTutorial.objects.create(codigo="CT-OTRO",nombre="Otro ficticio")
        d=self.payload("grupos");d["centro_tutorial"]=centro.pk
        f=GrupoForm(d);self.assertFalse(f.is_valid());self.assertIn("programa",f.errors)
    def test_orm_postgresql(self):self.assertEqual(connection.vendor,"postgresql")
    def test_get_no_elimina(self):
        self.client.get(reverse("profesor_eliminar",args=[self.recurso.pk]));self.assertTrue(Profesor.objects.filter(pk=self.recurso.pk).exists())

    def test_programa_no_elimina_planes_en_cascada(self):
        programa=ProgramaAcademico.objects.create(codigo="PROG-PLAN-FIC",nombre="Programa con plan ficticio",facultad=self.grupo.programa.facultad)
        plan=PlanEstudioAsignatura.objects.create(programa=programa,asignatura=self.asignatura,semestre=self.grupo.semestre,creditos=3,area_academica=self.area)
        r=self.client.post(reverse("programa_eliminar",args=[programa.pk]),follow=True)
        self.assertContains(r,"información asociada")
        self.assertTrue(ProgramaAcademico.objects.filter(pk=programa.pk).exists());self.assertTrue(PlanEstudioAsignatura.objects.filter(pk=plan.pk).exists())
