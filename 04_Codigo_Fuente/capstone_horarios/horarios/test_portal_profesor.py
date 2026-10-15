import json
from datetime import time
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command,CommandError
from django.db import connection
from django.test import TestCase,Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from academico.models import Profesor,PeriodoAcademico,Facultad,ProgramaAcademico,ProgramaCentroTutorial,Sede
from .models import Horario,Grupo,OfertaGrupo
from .test_validacion_docente import DatosDocencia

PASSWORD="PruebaPortal2026!"

class PortalProfesorTests(DatosDocencia,TestCase):
    def setUp(self):
        self.crear_datos()
        User=get_user_model()
        self.docente=User.objects.create_user(username="docente_ficticio_a",password=PASSWORD)
        self.docente_b=User.objects.create_user(username="docente_ficticio_b",password=PASSWORD)
        self.admin=User.objects.create_superuser(username="admin_portal_ficticio",password=PASSWORD)
        self.profesor.usuario=self.docente;self.profesor.save(update_fields=["usuario"])
        self.otro_profesor.usuario=self.docente_b;self.otro_profesor.save(update_fields=["usuario"])
        OfertaGrupo.objects.create(oferta=self.oferta,grupo=self.grupo,cupos=10)
        OfertaGrupo.objects.create(oferta=self.otra_oferta,grupo=self.grupo,cupos=10)
        self.h=self.horario();self.h.save()
        self.h_b=self.horario(dia="MA",oferta=self.otra_oferta,aula=self.otra_aula);self.h_b.save()
        self.nueva_oferta(self.profesor) # oferta sin horario mantiene el periodo consultable.
        self.condiciones(self.profesor,self.otro_periodo)
        oferta2=self.nueva_oferta(self.profesor,self.otro_periodo)
        self.h2=self.horario(oferta=oferta2);self.h2.save()
        self.client.force_login(self.docente)
    def eventos(self,**datos):return self.client.get(reverse("profesor_eventos"),{"periodo_id":self.periodo.pk,**datos})
    def pagina(self):return self.client.get(reverse("profesor_horario"),{"periodo_id":self.periodo.pk})
    def login(self,usuario):
        self.client.logout();return self.client.post(reverse("login"),{"username":usuario.get_username(),"password":PASSWORD})
    def test_anonimo_login(self):
        self.client.logout();r=self.pagina();self.assertEqual(r.status_code,302);self.assertIn(reverse("login"),r.url)
    def test_login_docente(self):self.assertEqual(self.login(self.docente).url,reverse("profesor_horario"))
    def test_login_admin(self):self.assertEqual(self.login(self.admin).url,reverse("inicio"))
    def test_login_docente_ignora_next_admin(self):
        self.client.logout();r=self.client.post(reverse("login"),{"username":self.docente.username,"password":PASSWORD,"next":reverse("planificacion")});self.assertEqual(r.url,reverse("profesor_horario"))
    def test_superusuario_asociado_prioridad_admin(self):
        Profesor.objects.create(identificacion="DOC-ADMIN-FIC",nombre="Admin",apellido="Ficticio",usuario=self.admin)
        self.assertEqual(self.login(self.admin).url,reverse("inicio"))
    def test_doble_capacidad_planificador(self):
        self.docente.user_permissions.add(*Permission.objects.filter(content_type__app_label="horarios",codename__in=["view_horario","change_horario"]))
        self.assertEqual(self.login(self.docente).url,reverse("inicio"))
    def test_capacidad_catalogos_prioritaria(self):
        self.docente.user_permissions.add(Permission.objects.get(content_type__app_label="academico",codename="view_profesor"))
        self.assertEqual(self.login(self.docente).url,reverse("mantenedores"))
    def test_sin_perfil_controlado(self):
        u=get_user_model().objects.create_user(username="sin_perfil_ficticio",password=PASSWORD)
        self.assertEqual(self.login(u).url,reverse("acceso_no_configurado"))
        self.assertContains(self.client.get(reverse("acceso_no_configurado")),"Su usuario no tiene un perfil docente asociado.",status_code=403)
    def test_docente_inicio_redirige_portal(self):self.assertEqual(self.client.get(reverse("inicio")).url,reverse("profesor_horario"))
    def test_pagina_solo_lectura_y_sidebar(self):
        r=self.pagina();self.assertEqual(r.status_code,200);self.assertContains(r,str(self.profesor));self.assertContains(r,"Mi horario")
        self.assertContains(r,'class="sidebar-professor-icon"');self.assertContains(r,"Profesor actual")
        for enlace in [reverse("planificacion"),reverse("mantenedores"),reverse("admin:index")]:self.assertNotContains(r,f'href="{enlace}"')
        for id in ["calendar-context-menu","mover-horario-modal","asignar-aula-modal","eliminar-horario-modal"]:self.assertNotContains(r,f'id="{id}"')
    def test_aislamiento(self):self.assertEqual([int(e["id"]) for e in self.eventos().json()],[self.h.pk])
    def test_profesor_b_solo_b(self):
        self.client.force_login(self.docente_b);self.assertEqual([int(e["id"]) for e in self.eventos().json()],[self.h_b.pk])
    def test_parametros_profesor_ignorados(self):
        d=self.eventos(profesor=self.otro_profesor.pk,profesor_id=self.otro_profesor.pk).json();self.assertEqual([int(e["id"]) for e in d],[self.h.pk])
    def test_otro_periodo_aislado(self):
        self.assertEqual([int(e["id"]) for e in self.eventos(periodo_id=self.otro_periodo.pk).json()],[self.h2.pk])
    def test_periodo_ajeno_no_consultable(self):
        p=PeriodoAcademico.objects.create(codigo="AJENO",nombre="Periodo ajeno")
        self.assertEqual(self.eventos(periodo_id=p.pk).status_code,404)
    def test_periodo_invalido(self):
        for valor in ["", "abc", "-1", "0"]:self.assertEqual(self.eventos(periodo_id=valor).status_code,400)
    def test_periodos_solo_docente_y_prioriza_horarios(self):
        p=PeriodoAcademico.objects.create(codigo="SOLO-OFERTA",nombre="Solo oferta",fecha_inicio="2030-01-01")
        self.nueva_oferta(self.profesor,p)
        r=self.pagina();self.assertTrue(r.context["periodos"][0].tiene_horarios);self.assertFalse(r.context["periodos"][-1].tiene_horarios)
    def test_periodo_cerrado_consulta_propia(self):
        self.periodo.activo=False;self.periodo.save();self.assertEqual(self.eventos().status_code,200)
    def test_horario_inactivo_excluido(self):
        self.h.activo=False;self.h.save();self.assertEqual(self.eventos().json(),[])
    def test_oferta_inactiva_excluida(self):
        self.oferta.activo=False;self.oferta.save();self.assertEqual(self.eventos().json(),[])
    def test_sede_aula_y_contexto_correctos(self):
        p=self.eventos().json()[0]["extendedProps"]
        self.assertEqual(p["aula"],self.aula.nombre);self.assertEqual(p["sede"],self.aula.sede.nombre)
        self.assertEqual(p["grupos"][0]["codigo"],self.grupo.codigo);self.assertEqual(p["programas"],[self.grupo.programa.nombre]);self.assertEqual(p["facultades"],[self.grupo.programa.facultad.nombre])
    def test_aula_pendiente_color(self):
        self.h.aula=None;self.h.save(update_fields=["aula"])
        e=self.eventos().json()[0];self.assertEqual(e["classNames"],["evento-pendiente"]);self.assertEqual(e["extendedProps"]["aula"],"Aula pendiente")
    def test_detalle_propio(self):
        r=self.client.get(reverse("profesor_detalle",args=[self.h.pk]));self.assertEqual(r.status_code,200);self.assertEqual(r.json()["event"]["extendedProps"]["horario_id"],self.h.pk)
    def test_detalle_ajeno_rechazado(self):
        self.assertEqual(self.client.get(reverse("profesor_detalle",args=[self.h_b.pk])).status_code,404)
    def test_exportar_pdf_periodo_propio(self):
        r=self.client.get(reverse("profesor_horario_pdf"),{"periodo_id":self.periodo.pk})
        self.assertEqual(r.status_code,200);self.assertEqual(r["Content-Type"],"application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF-"));self.assertIn("attachment;",r["Content-Disposition"])
        self.assertIn("Horario_",r["Content-Disposition"]);self.assertIn(self.periodo.codigo,r["Content-Disposition"])
        for texto in [b"Lunes",b"Martes",b"Jueves",b"Viernes",b"Domingo"]:
            self.assertIn(texto,r.content)
        self.assertNotIn(f"{self.periodo.codigo} ({self.periodo.codigo})".encode(),r.content)
    def test_pdf_exige_autenticacion(self):
        self.client.logout();r=self.client.get(reverse("profesor_horario_pdf"),{"periodo_id":self.periodo.pk})
        self.assertEqual(r.status_code,302);self.assertIn(reverse("login"),r.url)
    def test_pdf_no_expone_periodo_ajeno(self):
        p=PeriodoAcademico.objects.create(codigo="PDF-AJENO",nombre="Periodo PDF ajeno")
        self.assertEqual(self.client.get(reverse("profesor_horario_pdf"),{"periodo_id":p.pk}).status_code,404)
    def test_pdf_periodo_invalido(self):
        self.assertEqual(self.client.get(reverse("profesor_horario_pdf"),{"periodo_id":"abc"}).status_code,400)
    def test_pdf_no_duplica_periodo_si_nombre_y_codigo_son_iguales(self):
        self.periodo.nombre=self.periodo.codigo;self.periodo.save(update_fields=["nombre"])
        r=self.client.get(reverse("profesor_horario_pdf"),{"periodo_id":self.periodo.pk})
        self.assertEqual(r.status_code,200)
        self.assertNotIn(f"{self.periodo.codigo} ({self.periodo.codigo})".encode(),r.content)
    def test_pagina_muestra_exportacion_pdf_del_periodo(self):
        r=self.pagina();self.assertContains(r,reverse("profesor_horario_pdf"));self.assertContains(r,"Exportar PDF")
    def test_transversal_muestra_todos_sin_duplicar(self):
        f=Facultad.objects.create(codigo="FAC-PORTAL",nombre="Facultad Portal Ficticia")
        p=ProgramaAcademico.objects.create(codigo="PROG-PORTAL",nombre="Programa Portal Ficticio",facultad=f)
        ProgramaCentroTutorial.objects.create(programa=p,centro_tutorial=self.grupo.centro_tutorial)
        g=Grupo.objects.create(codigo="G-PORTAL",programa=p,centro_tutorial=self.grupo.centro_tutorial,periodo=self.periodo,semestre=self.grupo.semestre)
        OfertaGrupo.objects.create(oferta=self.oferta,grupo=g,cupos=10)
        d=self.eventos().json();self.assertEqual(len(d),1);self.assertEqual(len(d[0]["extendedProps"]["grupos"]),2)
        self.assertEqual(set(d[0]["extendedProps"]["facultades"]),{f.nombre,self.grupo.programa.facultad.nombre})
    def test_otra_sede_no_filtra_calendario_docente(self):
        sede=Sede.objects.create(codigo="PORTAL-OTRA",nombre="Otra sede ficticia",centro_tutorial=self.grupo.centro_tutorial)
        h=Horario.objects.create(oferta=self.oferta,sede=sede,dia="VI",hora_inicio=time(8),hora_fin=time(9))
        self.assertEqual({int(e["id"]) for e in self.eventos(sede=self.aula.sede_id).json()},{self.h.pk,h.pk})
    def test_perfil_inactivo_rechazado(self):
        self.profesor.activo=False;self.profesor.save();self.assertEqual(self.eventos().status_code,403);self.assertEqual(self.pagina().status_code,403)
    def test_sin_perfil_endpoint_403(self):
        self.profesor.usuario=None;self.profesor.save();self.assertEqual(self.eventos().status_code,403)
    def test_endpoints_solo_get(self):
        for url in [reverse("profesor_eventos"),reverse("profesor_detalle",args=[self.h.pk])]:self.assertEqual(self.client.post(url,{}).status_code,405)
    def test_docente_no_mantenedores(self):
        for url in [reverse("mantenedores"),reverse("profesores"),reverse("cargas_docentes"),reverse("grupos")]:self.assertEqual(self.client.get(url).status_code,403)
    def test_docente_no_operaciones_administrativas(self):
        for nombre in ["crear_horario_oferta","mover_horario","redimensionar_horario","eliminar_horario_calendario","asignar_aula_horario"]:
            self.assertEqual(self.client.post(reverse(nombre),json.dumps({"horario_id":self.h.pk}),content_type="application/json").status_code,403)
        self.assertTrue(Horario.objects.filter(pk=self.h.pk).exists())
    def test_docente_no_admin_tecnico(self):
        self.assertFalse(self.docente.is_staff);self.assertEqual(self.client.get(reverse("admin:index")).status_code,302)
    def test_admin_conserva_area(self):
        self.client.force_login(self.admin)
        for nombre in ["inicio","planificacion","mantenedores"]:
            r=self.client.get(reverse(nombre));self.assertEqual(r.status_code,200)
            self.assertContains(r,'class="sidebar-admin-icon"');self.assertContains(r,"Administrador")
    def test_sin_n_mas_uno(self):
        with CaptureQueriesContext(connection) as antes:self.eventos()
        for dia in ["MI","JU","VI"]:
            h=self.horario(dia=dia);h.save()
        with CaptureQueriesContext(connection) as despues:self.eventos()
        self.assertEqual(len(antes),len(despues))
    def test_sin_datos_estado_vacio(self):
        self.client.force_login(self.docente_b);self.otra_oferta.activo=False;self.otra_oferta.save()
        r=self.client.get(reverse("profesor_horario"));self.assertEqual(r.status_code,200);self.assertIsNone(r.context["periodo"])
    def test_login_y_logout_csrf_docente(self):
        c=Client(enforce_csrf_checks=True);c.get(reverse("login"));d={"username":self.docente.username,"password":PASSWORD}
        self.assertEqual(c.post(reverse("login"),d).status_code,403);d["csrfmiddlewaretoken"]=c.cookies["csrftoken"].value
        self.assertEqual(c.post(reverse("login"),d).url,reverse("profesor_horario"));c.get(reverse("profesor_horario"))
        self.assertEqual(c.post(reverse("logout"),{}).status_code,403)
        self.assertEqual(c.post(reverse("logout"),{"csrfmiddlewaretoken":c.cookies["csrftoken"].value}).url,reverse("login"))
    def test_postgres(self):self.assertEqual(connection.vendor,"postgresql")

class UsuarioDocenteDemoTests(TestCase):
    def setUp(self):self.p=Profesor.objects.create(identificacion="DOC-DEMO-100",nombre="Docente",apellido="Demo")
    def comando(self,nombre="docente_demo_ficticio"):
        with patch("horarios.management.commands.crear_usuario_profesor_demo.getpass",side_effect=[PASSWORD,PASSWORD]):
            out=StringIO();call_command("crear_usuario_profesor_demo",profesor=self.p.identificacion,usuario=nombre,stdout=out);return out.getvalue()
    def test_crea_sin_permisos_y_no_imprime_password(self):
        out=self.comando();self.p.refresh_from_db();u=self.p.usuario
        self.assertTrue(u.check_password(PASSWORD));self.assertFalse(u.is_staff);self.assertFalse(u.is_superuser);self.assertFalse(u.user_permissions.exists());self.assertNotIn(PASSWORD,out)
    def test_idempotente_sin_reset_password(self):
        self.comando();self.p.refresh_from_db();u=self.p.usuario;hash_anterior=u.password
        self.comando();u.refresh_from_db();self.assertEqual(u.password,hash_anterior);self.assertEqual(get_user_model().objects.count(),1)
    def test_no_reutiliza_usuario_existente(self):
        get_user_model().objects.create_superuser(username="admin_existente",password=PASSWORD)
        with self.assertRaises(CommandError):self.comando("admin_existente")
        self.p.refresh_from_db();self.assertIsNone(self.p.usuario_id)
    def test_no_reemplaza_vinculo(self):
        self.comando()
        with self.assertRaises(CommandError):self.comando("otra_cuenta")
    def test_solo_demo(self):
        with self.assertRaises(CommandError):call_command("crear_usuario_profesor_demo",profesor="DOC-REAL",usuario="x",stdout=StringIO())
