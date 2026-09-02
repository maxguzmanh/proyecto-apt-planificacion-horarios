from django import forms
from django.db import transaction
from django.db.models import Q

from horarios.models import Grupo

from .models import (
    AreaAcademica,
    Asignatura,
    Aula,
    CentroTutorial,
    Facultad,
    Modalidad,
    PeriodoAcademico,
    PlanEstudioAsignatura,
    Profesor,
    ProgramaAcademico,
    ProgramaCentroTutorial,
    Sede,
    Semestre,
)

# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================


def queryset_activos_con_actual(
    modelo,
    actual_id=None,
):
    """
    Devuelve registros activos.

    Cuando estamos editando un registro y la relación
    actualmente seleccionada fue desactivada, también
    la incluye para no perder el valor existente.
    """

    queryset = modelo.objects.filter(activo=True)

    if actual_id:
        queryset = modelo.objects.filter(Q(activo=True) | Q(pk=actual_id))

    return queryset.distinct()


# ==========================================================
# PROFESOR
# ==========================================================


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

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        centro_actual = None

        if self.instance and self.instance.pk and self.instance.centro_tutorial_id:
            centro_actual = self.instance.centro_tutorial_id

        self.fields["centro_tutorial"].queryset = queryset_activos_con_actual(
            CentroTutorial,
            centro_actual,
        ).order_by("nombre")


# ==========================================================
# FACULTAD
# ==========================================================


class FacultadForm(forms.ModelForm):

    class Meta:

        model = Facultad

        fields = [
            "codigo",
            "nombre",
            "activo",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: FAC-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la Facultad",
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
            "activo": "Facultad activa",
        }


# ==========================================================
# PROGRAMA ACADÉMICO
# ==========================================================


class ProgramaAcademicoForm(forms.ModelForm):

    centros_tutoriales = forms.ModelMultipleChoiceField(
        queryset=CentroTutorial.objects.none(),
        required=True,
        label="Centros Tutoriales",
        help_text=(
            "Seleccione uno o más Centros Tutoriales " "donde se imparte el programa."
        ),
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select",
                "size": "6",
            }
        ),
    )

    class Meta:

        model = ProgramaAcademico

        fields = [
            "facultad",
            "codigo",
            "nombre",
            "centros_tutoriales",
            "activo",
        ]

        widgets = {
            "facultad": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: ING-INF",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del Programa Académico",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "facultad": "Facultad",
            "codigo": "Código",
            "nombre": "Programa Académico",
            "activo": "Programa activo",
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        facultad_actual = None
        centros_actuales = []

        if self.instance and self.instance.pk:

            facultad_actual = self.instance.facultad_id

            centros_actuales = list(
                ProgramaCentroTutorial.objects.filter(
                    programa=self.instance,
                    activo=True,
                ).values_list(
                    "centro_tutorial_id",
                    flat=True,
                )
            )

        self.fields["facultad"].queryset = queryset_activos_con_actual(
            Facultad,
            facultad_actual,
        ).order_by("nombre")

        self.fields["centros_tutoriales"].queryset = (
            CentroTutorial.objects.filter(Q(activo=True) | Q(pk__in=centros_actuales))
            .distinct()
            .order_by("nombre")
        )

        if self.instance and self.instance.pk and not self.is_bound:
            self.initial["centros_tutoriales"] = centros_actuales

    def save(
        self,
        commit=True,
    ):

        if not commit:
            return super().save(commit=False)

        with transaction.atomic():

            programa = super().save(commit=True)

            centros_seleccionados = list(self.cleaned_data["centros_tutoriales"])

            # Las relaciones que ya no fueron seleccionadas
            # quedan inactivas, no se eliminan físicamente.
            ProgramaCentroTutorial.objects.filter(programa=programa).exclude(
                centro_tutorial__in=centros_seleccionados
            ).update(activo=False)

            # Creamos o reactivamos las seleccionadas.
            for centro in centros_seleccionados:

                ProgramaCentroTutorial.objects.update_or_create(
                    programa=programa,
                    centro_tutorial=centro,
                    defaults={
                        "activo": True,
                    },
                )

            return programa


# ==========================================================
# PERIODO ACADÉMICO
# ==========================================================


class PeriodoAcademicoForm(forms.ModelForm):

    class Meta:

        model = PeriodoAcademico

        fields = [
            "codigo",
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "activo",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: 01-2026",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Primer periodo 2026",
                }
            ),
            "fecha_inicio": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
            "fecha_fin": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
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
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de término",
            "activo": "Periodo activo",
        }

    def clean(self):

        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get("fecha_inicio")

        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            self.add_error(
                "fecha_fin",
                ("La fecha de término no puede " "ser anterior a la fecha de inicio."),
            )

        return cleaned_data


# ==========================================================
# SEMESTRE
# ==========================================================


class SemestreForm(forms.ModelForm):

    class Meta:

        model = Semestre

        fields = [
            "numero",
        ]

        widgets = {
            "numero": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

        labels = {
            "numero": "Semestre",
        }


# ==========================================================
# MODALIDAD
# ==========================================================


class ModalidadForm(forms.ModelForm):

    class Meta:

        model = Modalidad

        fields = [
            "codigo",
            "nombre",
            "activo",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: PRE",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Presencial",
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
            "activo": "Modalidad activa",
        }


# ==========================================================
# ÁREA ACADÉMICA
# ==========================================================


class AreaAcademicaForm(forms.ModelForm):

    class Meta:

        model = AreaAcademica

        fields = [
            "codigo",
            "nombre",
            "activo",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: INF",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Informática",
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
            "activo": "Área Académica activa",
        }


# ==========================================================
# ASIGNATURA
# ==========================================================


class AsignaturaForm(forms.ModelForm):

    class Meta:

        model = Asignatura

        fields = [
            "codigo",
            "nombre",
            "activo",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: PROGWEB01",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la asignatura",
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
            "nombre": "Asignatura",
            "activo": "Asignatura activa",
        }


# ==========================================================
# PLAN DE ESTUDIO
# ==========================================================


class PlanEstudioAsignaturaForm(forms.ModelForm):

    class Meta:

        model = PlanEstudioAsignatura

        fields = [
            "programa",
            "asignatura",
            "semestre",
            "creditos",
            "area_academica",
            "activo",
        ]

        widgets = {
            "programa": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "asignatura": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "semestre": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "creditos": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
            "area_academica": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "programa": "Programa Académico",
            "asignatura": "Asignatura",
            "semestre": "Semestre",
            "creditos": "Créditos",
            "area_academica": "Área Académica",
            "activo": "Registro activo",
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        programa_actual = None
        asignatura_actual = None
        area_actual = None

        if self.instance and self.instance.pk:

            programa_actual = self.instance.programa_id

            asignatura_actual = self.instance.asignatura_id

            area_actual = self.instance.area_academica_id

        self.fields["programa"].queryset = (
            queryset_activos_con_actual(
                ProgramaAcademico,
                programa_actual,
            )
            .select_related("facultad")
            .order_by("nombre")
        )

        self.fields["asignatura"].queryset = queryset_activos_con_actual(
            Asignatura,
            asignatura_actual,
        ).order_by("nombre")

        self.fields["semestre"].queryset = Semestre.objects.all().order_by("numero")

        self.fields["area_academica"].queryset = queryset_activos_con_actual(
            AreaAcademica,
            area_actual,
        ).order_by("nombre")


# ==========================================================
# AULA
# ==========================================================


class AulaForm(forms.ModelForm):

    class Meta:

        model = Aula

        fields = [
            "sede",
            "codigo",
            "nombre",
            "capacidad",
            "tipo",
            "activo",
        ]

        widgets = {
            "sede": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: SALA-101",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del aula",
                }
            ),
            "capacidad": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
            "tipo": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "sede": "Sede",
            "codigo": "Código",
            "nombre": "Aula",
            "capacidad": "Capacidad",
            "tipo": "Tipo",
            "activo": "Aula activa",
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        sede_actual = None

        if self.instance and self.instance.pk:
            sede_actual = self.instance.sede_id

        self.fields["sede"].queryset = (
            queryset_activos_con_actual(
                Sede,
                sede_actual,
            )
            .select_related("centro_tutorial")
            .order_by(
                "centro_tutorial__nombre",
                "nombre",
            )
        )


# ==========================================================
# GRUPO
# ==========================================================


class GrupoForm(forms.ModelForm):

    class Meta:

        model = Grupo

        fields = [
            "centro_tutorial",
            "programa",
            "periodo",
            "semestre",
            "codigo",
            "activo",
        ]

        widgets = {
            "centro_tutorial": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "programa": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "periodo": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "semestre": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: 05PD G1",
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
            "programa": "Programa Académico",
            "periodo": "Periodo Académico",
            "semestre": "Semestre",
            "codigo": "Código del grupo",
            "activo": "Grupo activo",
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        centro_actual = None
        programa_actual = None
        periodo_actual = None

        if self.instance and self.instance.pk:

            centro_actual = self.instance.centro_tutorial_id

            programa_actual = self.instance.programa_id

            periodo_actual = self.instance.periodo_id

        self.fields["centro_tutorial"].queryset = queryset_activos_con_actual(
            CentroTutorial,
            centro_actual,
        ).order_by("nombre")

        self.fields["programa"].queryset = (
            queryset_activos_con_actual(
                ProgramaAcademico,
                programa_actual,
            )
            .select_related("facultad")
            .order_by("nombre")
        )

        self.fields["periodo"].queryset = queryset_activos_con_actual(
            PeriodoAcademico,
            periodo_actual,
        ).order_by("-codigo")

        self.fields["semestre"].queryset = Semestre.objects.all().order_by("numero")

    def clean(self):

        cleaned_data = super().clean()

        programa = cleaned_data.get("programa")

        centro = cleaned_data.get("centro_tutorial")

        if programa and centro:

            relacion_valida = ProgramaCentroTutorial.objects.filter(
                programa=programa,
                centro_tutorial=centro,
                activo=True,
            ).exists()

            if not relacion_valida:

                self.add_error(
                    "programa",
                    (
                        "El Programa Académico seleccionado "
                        "no se encuentra habilitado en el "
                        "Centro Tutorial seleccionado."
                    ),
                )

        return cleaned_data
