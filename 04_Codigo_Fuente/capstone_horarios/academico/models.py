from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal

from .choices import DiaSemana

# ==========================================================
# ESTRUCTURA TERRITORIAL
# ==========================================================


class CentroTutorial(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
        unique=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Centro Tutorial"
        verbose_name_plural = "Centros Tutoriales"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Sede(models.Model):
    codigo = models.CharField(
        max_length=30,
    )

    nombre = models.CharField(
        max_length=150,
    )

    centro_tutorial = models.ForeignKey(
        CentroTutorial,
        on_delete=models.PROTECT,
        related_name="sedes",
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        ordering = [
            "centro_tutorial__nombre",
            "nombre",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "centro_tutorial",
                    "codigo",
                ],
                name="uq_sede_centro_codigo",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.centro_tutorial.nombre}"


# ==========================================================
# ESTRUCTURA ACADÉMICA
# ==========================================================


class Facultad(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
        unique=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Facultad"
        verbose_name_plural = "Facultades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ProgramaAcademico(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=200,
    )

    facultad = models.ForeignKey(
        Facultad,
        on_delete=models.PROTECT,
        related_name="programas_academicos",
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Programa Académico"
        verbose_name_plural = "Programas Académicos"
        ordering = [
            "facultad__nombre",
            "nombre",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "facultad",
                    "nombre",
                ],
                name="uq_programa_facultad_nombre",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ProgramaCentroTutorial(models.Model):
    """
    Indica en qué Centros Tutoriales se ofrece
    cada Programa Académico.
    """

    programa = models.ForeignKey(
        ProgramaAcademico,
        on_delete=models.CASCADE,
        related_name="centros_tutoriales",
    )

    centro_tutorial = models.ForeignKey(
        CentroTutorial,
        on_delete=models.CASCADE,
        related_name="programas_academicos",
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Programa por Centro Tutorial"
        verbose_name_plural = "Programas por Centro Tutorial"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "programa",
                    "centro_tutorial",
                ],
                name="uq_programa_centro_tutorial",
            ),
        ]

    def __str__(self):
        return f"{self.programa.nombre} - " f"{self.centro_tutorial.nombre}"


# ==========================================================
# CATÁLOGOS ACADÉMICOS
# ==========================================================


class PeriodoAcademico(models.Model):
    codigo = models.CharField(
        max_length=20,
        unique=True,
    )

    nombre = models.CharField(
        max_length=50,
    )

    fecha_inicio = models.DateField(
        null=True,
        blank=True,
    )

    fecha_fin = models.DateField(
        null=True,
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Periodo Académico"
        verbose_name_plural = "Periodos Académicos"
        ordering = ["-codigo"]

    def __str__(self):
        return self.nombre


class Semestre(models.Model):

    SEMESTRES = [
        (1, "I"),
        (2, "II"),
        (3, "III"),
        (4, "IV"),
        (5, "V"),
        (6, "VI"),
        (7, "VII"),
        (8, "VIII"),
        (9, "IX"),
        (10, "X"),
    ]

    numero = models.PositiveSmallIntegerField(
        choices=SEMESTRES,
        unique=True,
    )

    class Meta:
        verbose_name = "Semestre"
        verbose_name_plural = "Semestres"
        ordering = ["numero"]

    def __str__(self):
        return f"Semestre {self.get_numero_display()}"


class Modalidad(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=100,
        unique=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Modalidad"
        verbose_name_plural = "Modalidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class AreaAcademica(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
        unique=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Área Académica"
        verbose_name_plural = "Áreas Académicas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# ==========================================================
# ASIGNATURAS Y PLAN DE ESTUDIO
# ==========================================================


class Asignatura(models.Model):
    codigo = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=200,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class PlanEstudioAsignatura(models.Model):
    """
    Relaciona una asignatura con un programa académico.

    Los créditos, semestre y área académica pertenecen
    a esta relación y no directamente a Asignatura.
    """

    programa = models.ForeignKey(
        ProgramaAcademico,
        on_delete=models.CASCADE,
        related_name="plan_estudio",
    )

    asignatura = models.ForeignKey(
        Asignatura,
        on_delete=models.PROTECT,
        related_name="planes_estudio",
    )

    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name="planes_estudio",
    )

    creditos = models.PositiveSmallIntegerField(
        default=0,
    )

    area_academica = models.ForeignKey(
        AreaAcademica,
        on_delete=models.PROTECT,
        related_name="planes_estudio",
        null=True,
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Asignatura del Plan de Estudio"
        verbose_name_plural = "Asignaturas del Plan de Estudio"

        ordering = [
            "programa__nombre",
            "semestre__numero",
            "asignatura__nombre",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "programa",
                    "asignatura",
                    "semestre",
                ],
                name="uq_plan_programa_asignatura_semestre",
            ),
        ]

    def __str__(self):
        return (
            f"{self.programa.nombre} - "
            f"{self.semestre} - "
            f"{self.asignatura.nombre}"
        )


# ==========================================================
# PROFESORES
# ==========================================================


class Profesor(models.Model):
    identificacion = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    apellido = models.CharField(
        max_length=150,
    )

    correo_institucional = models.EmailField(
        unique=True,
        null=True,
        blank=True,
    )

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfil_profesor",
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Profesores"
        ordering = [
            "apellido",
            "nombre",
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


# ==========================================================
# AULAS
# ==========================================================


class Aula(models.Model):

    TIPO_FISICA = "FISICA"
    TIPO_VIRTUAL = "VIRTUAL"

    TIPOS_AULA = [
        (TIPO_FISICA, "Física"),
        (TIPO_VIRTUAL, "Virtual"),
    ]

    codigo = models.CharField(
        max_length=50,
    )

    nombre = models.CharField(
        max_length=100,
    )

    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        related_name="aulas",
    )

    capacidad = models.PositiveIntegerField(
        default=0,
    )

    tipo = models.CharField(
        max_length=10,
        choices=TIPOS_AULA,
        default=TIPO_FISICA,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"
        ordering = [
            "sede__nombre",
            "nombre",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "sede",
                    "codigo",
                ],
                name="uq_aula_sede_codigo",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.sede.nombre}"


class DisponibilidadProfesor(models.Model):
    profesor = models.ForeignKey(
        Profesor, on_delete=models.PROTECT, related_name="disponibilidades",
    )
    periodo = models.ForeignKey(
        PeriodoAcademico, on_delete=models.PROTECT,
        related_name="disponibilidades_profesores",
    )
    dia = models.CharField(max_length=2, choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Disponibilidad de Profesor"
        verbose_name_plural = "Disponibilidad de Profesores"
        ordering = ["profesor__apellido", "profesor__nombre", "periodo", "dia", "hora_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["profesor", "periodo", "dia", "hora_inicio", "hora_fin"],
                name="uq_disponibilidad_bloque",
            ),
            models.CheckConstraint(
                condition=models.Q(hora_fin__gt=models.F("hora_inicio")),
                name="ck_disponibilidad_horas",
            ),
            models.CheckConstraint(
                condition=models.Q(dia__in=DiaSemana.values),
                name="ck_disponibilidad_dia",
            ),
        ]

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la hora de inicio."})
        if not all([self.profesor_id, self.periodo_id, self.dia, self.hora_inicio, self.hora_fin]):
            return
        bloques = DisponibilidadProfesor.objects.filter(
            profesor_id=self.profesor_id, periodo_id=self.periodo_id, dia=self.dia,
        ).exclude(pk=self.pk)
        if bloques.filter(hora_inicio=self.hora_inicio, hora_fin=self.hora_fin).exists():
            raise ValidationError("Ya existe un bloque de disponibilidad exactamente igual.")
        if self.activo and bloques.filter(
            activo=True, hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio,
        ).exists():
            raise ValidationError("El bloque se superpone con otra disponibilidad activa del profesor.")

    def __str__(self):
        return (
            f"{self.profesor} - {self.periodo} - {self.get_dia_display()} "
            f"{self.hora_inicio:%H:%M} a {self.hora_fin:%H:%M}"
        )


class CargaDocente(models.Model):
    profesor = models.ForeignKey(
        Profesor, on_delete=models.PROTECT, related_name="cargas_docentes",
    )
    periodo = models.ForeignKey(
        PeriodoAcademico, on_delete=models.PROTECT, related_name="cargas_docentes",
    )
    horas_asignadas = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Horas cronológicas semanales de 60 minutos.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Carga Docente"
        verbose_name_plural = "Cargas Docentes"
        ordering = ["profesor__apellido", "profesor__nombre", "periodo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(horas_asignadas__gte=0),
                name="ck_carga_docente_no_negativa",
            ),
            models.UniqueConstraint(
                fields=["profesor", "periodo"], condition=models.Q(activo=True),
                name="uq_carga_docente_activa",
            ),
        ]

    def clean(self):
        super().clean()
        if self.horas_asignadas is not None and self.horas_asignadas < 0:
            raise ValidationError({"horas_asignadas": "La carga docente no puede ser negativa."})
        if self.activo and self.profesor_id and self.periodo_id:
            if CargaDocente.objects.filter(
                profesor_id=self.profesor_id, periodo_id=self.periodo_id, activo=True,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("Ya existe una carga docente activa para este profesor y periodo.")

    def __str__(self):
        return f"{self.profesor} - {self.periodo} - {self.horas_asignadas} horas semanales"
