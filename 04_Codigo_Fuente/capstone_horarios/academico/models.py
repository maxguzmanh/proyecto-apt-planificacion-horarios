from django.db import models

class CentroTutorial(models.Model):
    nombre = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre


class Sede(models.Model):
    nombre = models.CharField(max_length=150)
    centro_tutorial = models.ForeignKey(
        CentroTutorial,
        on_delete=models.CASCADE,
        related_name="sedes"
    )

    def __str__(self):
        return self.nombre


class Facultad(models.Model):
    nombre = models.CharField(max_length=150)
    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        related_name="facultades"
    )

    def __str__(self):
        return self.nombre


class Carrera(models.Model):
    nombre = models.CharField(max_length=150)
    facultad = models.ForeignKey(
        Facultad,
        on_delete=models.CASCADE,
        related_name="carreras"
    )

    def __str__(self):
        return self.nombre


class PeriodoAcademico(models.Model):
    nombre = models.CharField(max_length=20)

    def __str__(self):
        return self.nombre


class Semestre(models.Model):
    numero = models.PositiveIntegerField()

    carrera = models.ForeignKey(
        Carrera,
        on_delete=models.CASCADE,
        related_name="semestres"
    )

    periodo = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.CASCADE,
        related_name="semestres",
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Semestre {self.numero} - {self.carrera} - {self.periodo}"


class Asignatura(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.CASCADE,
        related_name="asignaturas"
    )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Profesor(models.Model):
    identificacion = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Aula(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        related_name="aulas"
    )
    capacidad = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre
# Create your models here.
