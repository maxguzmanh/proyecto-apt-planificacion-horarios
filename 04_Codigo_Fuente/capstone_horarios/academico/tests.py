from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Facultad, ProgramaAcademico


class EliminacionGenericaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(
            username="admin_prueba", password="ClavePrueba123!"
        )

    def setUp(self):
        self.facultad = Facultad.objects.create(codigo="FAC-TEST", nombre="Facultad Prueba")
        self.url = reverse("facultad_eliminar", args=[self.facultad.pk])
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.usuario)

    def test_get_muestra_confirmacion_sin_eliminar(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "academico/mantenedores/eliminar_generico.html")
        for texto in ["FAC-TEST", "Facultad Prueba", 'method="POST"',
                      "csrfmiddlewaretoken", "Cancelar", "Eliminar"]:
            self.assertContains(response, texto)
        self.assertContains(response, reverse("facultades"))
        self.assertTrue(Facultad.objects.filter(pk=self.facultad.pk).exists())

    def test_post_requiere_csrf_y_elimina_registro_sin_relaciones(self):
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Facultad.objects.filter(pk=self.facultad.pk).exists())
        self.client.get(self.url)
        response = self.client.post(self.url, {
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, reverse("facultades"))
        self.assertFalse(Facultad.objects.filter(pk=self.facultad.pk).exists())

    def test_relaciones_protegidas_impiden_eliminar(self):
        programa = ProgramaAcademico.objects.create(
            codigo="PROG-TEST", nombre="Programa Prueba", facultad=self.facultad,
        )
        self.client.get(self.url)
        response = self.client.post(self.url, {
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        }, follow=True)
        self.assertContains(response, "posee información asociada")
        self.assertTrue(Facultad.objects.filter(pk=self.facultad.pk).exists())
        self.assertTrue(ProgramaAcademico.objects.filter(pk=programa.pk).exists())

    def test_usuario_sin_permiso_no_puede_eliminar(self):
        usuario = get_user_model().objects.create_user(username="sin_permiso")
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.get(reverse("login"))
        response = self.client.post(self.url, {
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Facultad.objects.filter(pk=self.facultad.pk).exists())
