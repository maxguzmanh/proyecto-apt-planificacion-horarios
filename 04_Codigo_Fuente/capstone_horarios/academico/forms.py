from django import forms

from django.db import models

from .models import (
    CentroTutorial,
    Profesor,
    Sede,
)


class ProfesorForm(forms.ModelForm):

    class Meta:

        model = Profesor

        fields = [
            "identificacion",
            "nombre",
            "apellido",
            "correo_institucional",
            "activo",
        ]

        widgets = {
            "identificacion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: DOC-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre",
                }
            ),
            "apellido": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Apellido",
                }
            ),
            "correo_institucional": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "correo@institucion.edu",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "identificacion": "Identificación",
            "nombre": "Nombre",
            "apellido": "Apellido",
            "correo_institucional": "Correo institucional",
            "activo": "Profesor activo",
        }


# ==========================================================
# CENTRO TUTORIAL
# ==========================================================


class CentroTutorialForm(forms.ModelForm):

    class Meta:

        model = CentroTutorial

        fields = [
            "codigo",
            "nombre",
            "activo",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: CT-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del Centro Tutorial",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "codigo": "Código",
            "nombre": "Nombre",
            "activo": "Centro Tutorial activo",
        }


# ==========================================================
# SEDE
# ==========================================================


class SedeForm(forms.ModelForm):

    class Meta:

        model = Sede

        fields = [
            "centro_tutorial",
            "codigo",
            "nombre",
            "activo",
        ]

        widgets = {
            "centro_tutorial": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: SEDE-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la sede",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "centro_tutorial": "Centro Tutorial",
            "codigo": "Código",
            "nombre": "Nombre",
            "activo": "Sede activa",
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        centros = CentroTutorial.objects.filter(activo=True)

        # Si se está editando una sede cuyo Centro Tutorial
        # posteriormente fue desactivado, seguimos mostrándolo.
        if self.instance and self.instance.pk and self.instance.centro_tutorial_id:
            centros = CentroTutorial.objects.filter(
                models.Q(activo=True) | models.Q(pk=self.instance.centro_tutorial_id)
            )

        self.fields["centro_tutorial"].queryset = centros.order_by("nombre")
