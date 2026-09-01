from django import forms

from academico.models import Aula

from .models import Horario, OfertaAcademica


class HorarioForm(forms.ModelForm):
    class Meta:
        model = Horario
        fields = [
            "oferta",
            "aula",
            "dia",
            "hora_inicio",
            "hora_fin",
        ]
        widgets = {
            "oferta": forms.Select(attrs={"class": "form-select"}),
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
        programa=None,
        semestre=None,
        centro_tutorial=None,
        sede=None,
        periodo=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        ofertas = OfertaAcademica.objects.filter(
            activo=True,
            profesor__activo=True,
        )

        if periodo:
            ofertas = ofertas.filter(periodo=periodo)

        if programa:
            ofertas = ofertas.filter(grupos__programa=programa)

        if semestre:
            ofertas = ofertas.filter(grupos__semestre=semestre)

        if centro_tutorial:
            ofertas = ofertas.filter(grupos__centro_tutorial=centro_tutorial)

        self.fields["oferta"].queryset = (
            ofertas.select_related(
                "asignatura",
                "profesor",
                "periodo",
                "modalidad",
            )
            .distinct()
            .order_by("asignatura__nombre")
        )

        aulas = Aula.objects.filter(activo=True)

        if sede:
            aulas = aulas.filter(sede=sede)

        self.fields["aula"].queryset = aulas.select_related("sede").order_by("nombre")
