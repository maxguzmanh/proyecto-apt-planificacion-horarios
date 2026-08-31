from django import forms

from academico.models import Asignatura, Aula, Profesor

from .models import Horario


class HorarioForm(forms.ModelForm):

    class Meta:
        model = Horario

        fields = [
            "asignatura",
            "profesor",
            "aula",
            "dia",
            "hora_inicio",
            "hora_fin",
        ]

        widgets = {
            "asignatura": forms.Select(attrs={"class": "form-select"}),
            "profesor": forms.Select(attrs={"class": "form-select"}),
            "aula": forms.Select(attrs={"class": "form-select"}),
            "dia": forms.Select(attrs={"class": "form-select"}),
            "hora_inicio": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),
            "hora_fin": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),
        }

    def __init__(
        self,
        *args,
        semestre=None,
        sede=None,
        periodo=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # IMPORTANTE:
        # El periodo debe existir en la instancia ANTES de form.is_valid()
        # para que Horario.clean() pueda validar los conflictos.
        if periodo:
            self.instance.periodo = periodo

        if semestre:
            self.fields["asignatura"].queryset = Asignatura.objects.filter(
                semestre=semestre
            )

        if sede:
            self.fields["aula"].queryset = Aula.objects.filter(sede=sede)

        self.fields["profesor"].queryset = Profesor.objects.filter(activo=True)
