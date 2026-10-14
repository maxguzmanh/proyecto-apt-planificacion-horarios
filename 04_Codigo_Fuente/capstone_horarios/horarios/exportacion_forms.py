from django import forms
from academico.models import CentroTutorial, Facultad, ProgramaAcademico, PeriodoAcademico, Semestre
from .contexto_academico import facultades_del_centro, programas_del_centro, semestres_del_programa

class ExportacionPlanificacionForm(forms.Form):
    periodo = forms.ModelChoiceField(label="Periodo Académico", queryset=PeriodoAcademico.objects.all().order_by("-codigo"), empty_label="Seleccione un periodo...")
    centro = forms.ModelChoiceField(label="Centro Tutorial", queryset=CentroTutorial.objects.filter(activo=True), required=False, empty_label="Seleccione un centro...")
    facultad = forms.ModelChoiceField(label="Facultad", queryset=Facultad.objects.none(), required=False, empty_label="Seleccione una facultad...")
    programa = forms.ModelChoiceField(label="Programa Académico", queryset=ProgramaAcademico.objects.none(), required=False, empty_label="Seleccione un programa...")
    semestre = forms.ModelChoiceField(label="Semestre", queryset=Semestre.objects.none(), required=False, empty_label="Seleccione un semestre...")

    busqueda = forms.CharField(required=False, max_length=200, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def identificador(nombre):
            valor = self.data.get(nombre, "")
            try:
                valor = int(valor)
                return valor if valor > 0 else None
            except (ValueError, TypeError):
                return None
        centro, facultad, programa, periodo = [identificador(n) for n in ("centro", "facultad", "programa", "periodo")]
        if centro:
            self.fields["facultad"].queryset = facultades_del_centro(centro)
        if centro and facultad:
            self.fields["programa"].queryset = programas_del_centro(centro, facultad)
        if centro and programa and periodo:
            self.fields["semestre"].queryset = semestres_del_programa(centro, programa, periodo)
        for nombre, campo in self.fields.items():
            campo.widget.attrs["class"] = "form-select"
            campo.widget.attrs["id"] = f"exportar-{nombre}"
