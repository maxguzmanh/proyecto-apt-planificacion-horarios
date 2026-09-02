from django import forms

from academico.models import (
    Asignatura,
    Aula,
    Modalidad,
    PlanEstudioAsignatura,
    Profesor,
    Sede,
)

from .models import (
    Grupo,
    Horario,
    OfertaAcademica,
)

# ==========================================================
# FORMULARIO ACTUAL DE HORARIO
#
# Lo conservamos temporalmente porque todavía lo utiliza
# la pantalla de edición.
# ==========================================================


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
            "oferta": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "aula": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "dia": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
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

        # ==================================================
        # OFERTAS ACADÉMICAS
        # ==================================================

        ofertas = OfertaAcademica.objects.filter(
            activo=True,
            profesor__activo=True,
        )

        if periodo:

            ofertas = ofertas.filter(
                periodo=periodo,
            )

        if programa:

            ofertas = ofertas.filter(
                grupos__programa=programa,
            )

        if semestre:

            ofertas = ofertas.filter(
                grupos__semestre=semestre,
            )

        if centro_tutorial:

            ofertas = ofertas.filter(
                grupos__centro_tutorial=centro_tutorial,
            )

        self.fields["oferta"].queryset = (
            ofertas.select_related(
                "asignatura",
                "profesor",
                "periodo",
                "modalidad",
            )
            .distinct()
            .order_by(
                "asignatura__nombre",
            )
        )

        # ==================================================
        # AULAS
        # ==================================================

        aulas = Aula.objects.filter(
            activo=True,
        )

        if sede:

            aulas = aulas.filter(
                sede=sede,
            )

        self.fields["aula"].queryset = aulas.select_related(
            "sede",
        ).order_by(
            "nombre",
        )


# ==========================================================
# NUEVA ASIGNACIÓN
#
# Este formulario representa la operación que ve el usuario.
# Django creará por detrás:
#
# OfertaAcademica
# OfertaGrupo
# Horario
# ==========================================================


class NuevaAsignacionForm(forms.Form):

    # ======================================================
    # ASIGNATURA
    # ======================================================

    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.none(),
        label="Asignatura",
        empty_label="Seleccione una asignatura...",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # ======================================================
    # PROFESOR
    # ======================================================

    profesor = forms.ModelChoiceField(
        queryset=Profesor.objects.none(),
        label="Profesor",
        empty_label="Seleccione un profesor...",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # ======================================================
    # MODALIDAD
    # ======================================================

    modalidad = forms.ModelChoiceField(
        queryset=Modalidad.objects.none(),
        label="Modalidad",
        empty_label="Seleccione una modalidad...",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # ======================================================
    # GRUPOS
    #
    # Uno       = horario normal
    # Varios    = horario transversal
    # ======================================================

    grupos = forms.ModelMultipleChoiceField(
        queryset=Grupo.objects.none(),
        label="Grupo(s)",
        required=True,
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "form-check-input",
            }
        ),
        help_text=(
            "Seleccione uno o varios grupos. "
            "Si selecciona más de uno, la asignación "
            "se considerará transversal."
        ),
    )

    # ======================================================
    # CUPOS
    # ======================================================

    cupos = forms.IntegerField(
        label="Cupos",
        min_value=1,
        initial=30,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
            }
        ),
        help_text=("Los cupos indicados se aplicarán a " "cada grupo seleccionado."),
    )

    # ======================================================
    # SEDE
    # ======================================================

    sede = forms.ModelChoiceField(
        queryset=Sede.objects.none(),
        label="Sede",
        empty_label="Seleccione una sede...",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_sede",
            }
        ),
    )

    # ======================================================
    # AULA
    # ======================================================

    aula = forms.ModelChoiceField(
        queryset=Aula.objects.none(),
        label="Aula",
        empty_label="Seleccione un aula...",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_aula",
            }
        ),
    )

    # ======================================================
    # DÍA
    # ======================================================

    dia = forms.ChoiceField(
        choices=Horario.DIAS,
        label="Día",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # ======================================================
    # HORA INICIO
    # ======================================================

    hora_inicio = forms.TimeField(
        label="Hora inicio",
        widget=forms.TimeInput(
            attrs={
                "class": "form-control",
                "type": "time",
            }
        ),
    )

    # ======================================================
    # HORA TÉRMINO
    # ======================================================

    hora_fin = forms.TimeField(
        label="Hora término",
        widget=forms.TimeInput(
            attrs={
                "class": "form-control",
                "type": "time",
            }
        ),
    )

    # ======================================================
    # INICIALIZACIÓN
    # ======================================================

    def __init__(
        self,
        *args,
        programa=None,
        semestre=None,
        centro_tutorial=None,
        periodo=None,
        sede_inicial=None,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        self.programa = programa
        self.semestre = semestre
        self.centro_tutorial = centro_tutorial
        self.periodo = periodo

        # ==================================================
        # ASIGNATURAS DEL PLAN DE ESTUDIO
        # ==================================================

        asignaturas = Asignatura.objects.filter(
            activo=True,
        )

        if programa:

            asignaturas = asignaturas.filter(
                planes_estudio__programa=programa,
                planes_estudio__activo=True,
            )

        if semestre:

            asignaturas = asignaturas.filter(
                planes_estudio__semestre=semestre,
                planes_estudio__activo=True,
            )

        self.fields["asignatura"].queryset = asignaturas.distinct().order_by(
            "nombre",
        )

        # ==================================================
        # PROFESORES ACTIVOS
        # ==================================================

        self.fields["profesor"].queryset = Profesor.objects.filter(
            activo=True,
        ).order_by(
            "apellido",
            "nombre",
        )

        # ==================================================
        # MODALIDADES ACTIVAS
        # ==================================================

        self.fields["modalidad"].queryset = Modalidad.objects.filter(
            activo=True,
        ).order_by(
            "nombre",
        )

        # ==================================================
        # GRUPOS DEL CONTEXTO ACADÉMICO
        # ==================================================

        grupos = Grupo.objects.filter(
            activo=True,
        )

        if centro_tutorial:

            grupos = grupos.filter(
                centro_tutorial=centro_tutorial,
            )

        if periodo:

            grupos = grupos.filter(
                periodo=periodo,
            )

        if semestre:

            grupos = grupos.filter(
                semestre=semestre,
            )

        self.fields["grupos"].queryset = grupos.select_related(
            "programa",
            "semestre",
            "periodo",
        ).order_by(
            "codigo",
        )

        self.fields["grupos"].label_from_instance = lambda grupo: (
            f"{grupo.programa.nombre} — {grupo.codigo}"
        )

        # ==================================================
        # SEDES DEL CENTRO TUTORIAL
        # ==================================================

        sedes = Sede.objects.filter(
            activo=True,
        )

        if centro_tutorial:

            sedes = sedes.filter(
                centro_tutorial=centro_tutorial,
            )

        self.fields["sede"].queryset = sedes.order_by(
            "nombre",
        )

        # ==================================================
        # SEDE INICIAL
        # ==================================================

        if sede_inicial:

            self.fields["sede"].initial = sede_inicial

        # ==================================================
        # AULAS
        #
        # Si el formulario viene enviado por POST,
        # usamos la sede seleccionada.
        #
        # Si es la primera carga y tenemos sede inicial,
        # utilizamos esa sede.
        # ==================================================

        aulas = Aula.objects.filter(
            activo=True,
        )

        if centro_tutorial:

            aulas = aulas.filter(
                sede__centro_tutorial=centro_tutorial,
            )

        sede_id = None

        if self.is_bound:

            sede_id = self.data.get("sede")

        elif sede_inicial:

            sede_id = sede_inicial.pk

        if sede_id:

            try:

                aulas = aulas.filter(
                    sede_id=int(sede_id),
                )

            except (
                TypeError,
                ValueError,
            ):

                aulas = Aula.objects.none()

        else:

            aulas = Aula.objects.none()

        self.fields["aula"].queryset = aulas.select_related(
            "sede",
        ).order_by(
            "nombre",
        )

    # ======================================================
    # VALIDACIÓN GENERAL
    # ======================================================

    def clean(self):

        cleaned_data = super().clean()

        hora_inicio = cleaned_data.get("hora_inicio")

        hora_fin = cleaned_data.get("hora_fin")

        sede = cleaned_data.get("sede")

        aula = cleaned_data.get("aula")

        # --------------------------------------------------
        # ASIGNATURA / GRUPOS
        #
        # La asignatura debe pertenecer al plan de estudio
        # de cada programa asociado a los grupos elegidos.
        # --------------------------------------------------

        asignatura = cleaned_data.get("asignatura")

        grupos = cleaned_data.get("grupos")

        if asignatura and grupos:

            grupos_invalidos = []

            for grupo in grupos:

                existe_en_plan = PlanEstudioAsignatura.objects.filter(
                    programa=grupo.programa,
                    asignatura=asignatura,
                    semestre=grupo.semestre,
                    activo=True,
                ).exists()

                if not existe_en_plan:

                    grupos_invalidos.append(
                        (f"{grupo.programa.nombre} " f"- {grupo.codigo}")
                    )

            if grupos_invalidos:

                self.add_error(
                    "grupos",
                    (
                        "La asignatura seleccionada no "
                        "pertenece al plan de estudio de: "
                        + ", ".join(grupos_invalidos)
                        + "."
                    ),
                )

        # --------------------------------------------------
        # HORAS
        # --------------------------------------------------

        if hora_inicio and hora_fin and hora_inicio >= hora_fin:

            self.add_error(
                "hora_fin",
                ("La hora de término debe ser " "posterior a la hora de inicio."),
            )

        # --------------------------------------------------
        # AULA / SEDE
        # --------------------------------------------------

        if sede and aula and aula.sede_id != sede.id:

            self.add_error(
                "aula",
                ("El aula seleccionada no pertenece " "a la sede indicada."),
            )

        return cleaned_data
