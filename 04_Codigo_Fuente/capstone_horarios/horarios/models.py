from django.core.exceptions import ValidationError
from django.db import models

from academico.models import (
    Asignatura,
    Aula,
    CentroTutorial,
    Modalidad,
    PeriodoAcademico,
    Profesor,
    ProgramaAcademico,
    Semestre,
)

# ==========================================================
# GRUPOS
# ==========================================================


class Grupo(models.Model):
    """
    Representa un grupo académico concreto dentro
    de un Programa, Centro Tutorial, Periodo y Semestre.

    Ejemplo:
    Ingeniería Informática
    Centro Tutorial Ciudad Demo
    Periodo 01-2026
    Semestre V
    Grupo 01PD G1
    """

    codigo = models.CharField(
        max_length=50,
    )

    programa = models.ForeignKey(
        ProgramaAcademico,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    centro_tutorial = models.ForeignKey(
        CentroTutorial,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name="grupos",
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"

        ordering = [
            "centro_tutorial__nombre",
            "programa__nombre",
            "semestre__numero",
            "codigo",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "centro_tutorial",
                    "periodo",
                    "programa",
                    "semestre",
                    "codigo",
                ],
                name="uq_grupo_contexto_codigo",
            ),
        ]

    def __str__(self):
        return (
            f"{self.codigo} - "
            f"{self.programa.nombre} - "
            f"{self.semestre} - "
            f"{self.periodo.nombre}"
        )


# ==========================================================
# OFERTA ACADÉMICA
# ==========================================================


class OfertaAcademica(models.Model):
    """
    Representa una asignatura efectivamente ofrecida
    durante un periodo académico.

    Una misma oferta puede estar asociada a uno o varios
    grupos, permitiendo manejar asignaturas transversales.
    """

    asignatura = models.ForeignKey(
        Asignatura,
        on_delete=models.PROTECT,
        related_name="ofertas_academicas",
    )

    profesor = models.ForeignKey(
        Profesor,
        on_delete=models.PROTECT,
        related_name="ofertas_academicas",
    )

    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="ofertas_academicas",
    )

    modalidad = models.ForeignKey(
        Modalidad,
        on_delete=models.PROTECT,
        related_name="ofertas_academicas",
    )

    grupos = models.ManyToManyField(
        Grupo,
        through="OfertaGrupo",
        related_name="ofertas_academicas",
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Oferta Académica"
        verbose_name_plural = "Ofertas Académicas"

        ordering = [
            "periodo__nombre",
            "asignatura__nombre",
        ]

    def clean(self):

        if self.profesor_id and not self.profesor.activo:
            raise ValidationError(
                {"profesor": ("El profesor seleccionado " "se encuentra inactivo.")}
            )

    def __str__(self):
        return f"{self.asignatura} - " f"{self.profesor} - " f"{self.periodo}"


# ==========================================================
# RELACIÓN OFERTA - GRUPO
# ==========================================================


class OfertaGrupo(models.Model):
    """
    Relaciona una Oferta Académica con los grupos
    que reciben esa asignatura.

    Si una oferta tiene varios grupos asociados,
    estaremos frente a una oferta transversal.
    """

    oferta = models.ForeignKey(
        OfertaAcademica,
        on_delete=models.CASCADE,
        related_name="ofertas_grupo",
    )

    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.PROTECT,
        related_name="ofertas_grupo",
    )

    cupos = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        verbose_name = "Grupo de Oferta Académica"
        verbose_name_plural = "Grupos de Oferta Académica"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "oferta",
                    "grupo",
                ],
                name="uq_oferta_grupo",
            ),
        ]

        ordering = [
            "grupo__programa__nombre",
            "grupo__semestre__numero",
            "grupo__codigo",
        ]

    def clean(self):

        if not all(
            [
                self.oferta_id,
                self.grupo_id,
            ]
        ):
            return

        if self.oferta.periodo_id != self.grupo.periodo_id:

            raise ValidationError(
                {
                    "grupo": (
                        "El grupo pertenece a un periodo "
                        "académico diferente al de la oferta."
                    )
                }
            )

    def __str__(self):
        return f"{self.oferta.asignatura.nombre} - " f"{self.grupo}"


# ==========================================================
# HORARIOS
# ==========================================================


class Horario(models.Model):

    DIAS = [
        ("LU", "Lunes"),
        ("MA", "Martes"),
        ("MI", "Miércoles"),
        ("JU", "Jueves"),
        ("VI", "Viernes"),
        ("SA", "Sábado"),
        ("DO", "Domingo"),
    ]

    oferta = models.ForeignKey(
        OfertaAcademica,
        on_delete=models.CASCADE,
        related_name="horarios",
    )

    aula = models.ForeignKey(
        Aula,
        on_delete=models.PROTECT,
        related_name="horarios",
    )

    dia = models.CharField(
        max_length=2,
        choices=DIAS,
    )

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"

        ordering = [
            "dia",
            "hora_inicio",
        ]

    # ======================================================
    # VALIDACIONES
    # ======================================================

    def clean(self):

        # --------------------------------------------------
        # VALIDAR HORAS
        # --------------------------------------------------

        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:

            raise ValidationError(
                {
                    "hora_fin": (
                        "La hora de término debe ser " "posterior a la hora de inicio."
                    )
                }
            )

        # --------------------------------------------------
        # SI FALTAN DATOS, NO CONTINUAMOS
        # --------------------------------------------------

        if not all(
            [
                self.oferta_id,
                self.aula_id,
                self.dia,
                self.hora_inicio,
                self.hora_fin,
            ]
        ):
            return

        # --------------------------------------------------
        # DATOS DE LA OFERTA
        # --------------------------------------------------

        profesor = self.oferta.profesor
        periodo = self.oferta.periodo

        # --------------------------------------------------
        # CONFLICTO DE PROFESOR
        # --------------------------------------------------

        conflicto_profesor = (
            Horario.objects.filter(
                oferta__profesor=profesor,
                oferta__periodo=periodo,
                dia=self.dia,
                activo=True,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio,
            )
            .exclude(pk=self.pk)
            .select_related(
                "oferta__asignatura",
                "oferta__profesor",
            )
        )

        if conflicto_profesor.exists():

            horario = conflicto_profesor.first()

            raise ValidationError(
                {
                    "oferta": (
                        f"El profesor {profesor} ya tiene "
                        f"programada la asignatura "
                        f'"{horario.oferta.asignatura}" '
                        f"de "
                        f'{horario.hora_inicio.strftime("%H:%M")} '
                        f"a "
                        f'{horario.hora_fin.strftime("%H:%M")}.'
                    )
                }
            )

        # --------------------------------------------------
        # CONFLICTO DE AULA FÍSICA
        # --------------------------------------------------

        if self.aula.tipo == Aula.TIPO_FISICA:

            conflicto_aula = (
                Horario.objects.filter(
                    aula=self.aula,
                    oferta__periodo=periodo,
                    dia=self.dia,
                    activo=True,
                    hora_inicio__lt=self.hora_fin,
                    hora_fin__gt=self.hora_inicio,
                )
                .exclude(pk=self.pk)
                .select_related(
                    "oferta__asignatura",
                    "aula",
                )
            )

            if conflicto_aula.exists():

                horario = conflicto_aula.first()

                raise ValidationError(
                    {
                        "aula": (
                            f"El aula {self.aula.nombre} "
                            f"ya está ocupada por "
                            f'"{horario.oferta.asignatura}" '
                            f"de "
                            f'{horario.hora_inicio.strftime("%H:%M")} '
                            f"a "
                            f'{horario.hora_fin.strftime("%H:%M")}.'
                        )
                    }
                )

        # --------------------------------------------------
        # CONFLICTO DE GRUPO
        # --------------------------------------------------

        grupos_actuales = self.oferta.grupos.all()

        if grupos_actuales.exists():

            conflicto_grupo = (
                Horario.objects.filter(
                    oferta__periodo=periodo,
                    oferta__grupos__in=grupos_actuales,
                    dia=self.dia,
                    activo=True,
                    hora_inicio__lt=self.hora_fin,
                    hora_fin__gt=self.hora_inicio,
                )
                .exclude(pk=self.pk)
                .select_related(
                    "oferta__asignatura",
                )
                .distinct()
            )

            if conflicto_grupo.exists():

                horario = conflicto_grupo.first()

                grupos_conflicto = grupos_actuales.filter(
                    ofertas_academicas=horario.oferta
                )

                nombres_grupos = ", ".join(grupo.codigo for grupo in grupos_conflicto)

                raise ValidationError(
                    {
                        "oferta": (
                            f"El grupo {nombres_grupos} "
                            f"ya tiene programada "
                            f"la asignatura "
                            f'"{horario.oferta.asignatura}" '
                            f"de "
                            f'{horario.hora_inicio.strftime("%H:%M")} '
                            f"a "
                            f'{horario.hora_fin.strftime("%H:%M")}.'
                        )
                    }
                )

    # ======================================================
    # REPRESENTACIÓN
    # ======================================================

    def __str__(self):

        return (
            f"{self.oferta.asignatura} - "
            f"{self.get_dia_display()} "
            f'{self.hora_inicio.strftime("%H:%M")} - '
            f'{self.hora_fin.strftime("%H:%M")}'
        )


# Create your models here.
