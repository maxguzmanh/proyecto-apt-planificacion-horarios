from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse


class AutenticacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="usuario_prueba", password="ClavePrueba123!"
        )
        # El usuario que verifica login/logout accede al dashboard como planificador.
        cls.usuario.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="horarios", codename__in=["view_horario", "change_horario"]))

    def test_acceso_anonimo_redirige_al_login(self):
        response = self.client.get(reverse("inicio"))
        self.assertRedirects(response, reverse("login") + "?next=/")

    def test_login_muestra_plantilla_actual(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/login.html")

    def test_login_redirige_a_inicio(self):
        response = self.client.post(reverse("login"), {
            "username": "usuario_prueba", "password": "ClavePrueba123!",
        })
        self.assertRedirects(response, reverse("inicio"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_respeta_next_y_rechaza_destino_externo(self):
        for destino, esperado in [
            (reverse("mantenedores"), reverse("mantenedores")),
            ("https://example.com/", reverse("inicio")),
        ]:
            with self.subTest(destino=destino):
                self.client.logout()
                response = self.client.post(reverse("login"), {
                    "username": "usuario_prueba", "password": "ClavePrueba123!",
                    "next": destino,
                })
                self.assertRedirects(response, esperado)

    def test_login_incorrecto_no_inicia_sesion(self):
        response = self.client.post(reverse("login"), {
            "username": "usuario_prueba", "password": "incorrecta",
        })
        self.assertContains(response, "Usuario o contraseña incorrectos.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_post_con_csrf_y_redireccion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        response = client.get(reverse("inicio"))
        self.assertContains(response, reverse("logout"))
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        response = client.post(reverse("logout"), {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", client.session)

    def test_login_post_con_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("login") + "?next=/mantenedores/")
        self.assertContains(response, 'name="next" value="/mantenedores/"')
        datos = {"username": "usuario_prueba", "password": "ClavePrueba123!"}
        self.assertEqual(client.post(reverse("login"), datos).status_code, 403)
        datos["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        response = client.post(reverse("login"), datos)
        self.assertRedirects(response, reverse("inicio"))
