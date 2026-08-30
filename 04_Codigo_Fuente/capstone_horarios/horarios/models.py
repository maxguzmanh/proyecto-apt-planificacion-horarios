from django.db import models
from django.core.exceptions import ValidationError

from academico.models import Asignatura, Profesor, Aula, PeriodoAcademico


class Horario(models.Model):

    DIAS = [
        ("LU", "Lunes"),
        ("MA", "Martes"),
        ("MI", "Miércoles"),
        ("JU", "Jueves"),
        ("VI", "Viernes"),
        ("SA", "Sábado"),
    ]

    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)

    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)

    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)

    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE)

    dia = models.CharField(max_length=2, choices=DIAS)

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    def clean(self):

        # Validar que la hora de término sea mayor
        # que la hora de inicio
        if self.hora_inicio and self.hora_fin:

            if self.hora_inicio >= self.hora_fin:
                raise ValidationError(
                    {
                        "hora_fin": "La hora de término debe ser posterior a la hora de inicio."
                    }
                )

        # Si todavía faltan datos, no hacemos validaciones
        if not all(
            [
                self.profesor_id,
                self.aula_id,
                self.periodo_id,
                self.dia,
                self.hora_inicio,
                self.hora_fin,
            ]
        ):
            return

        # --------------------------------------------------
        # CONFLICTO DE PROFESOR
        # --------------------------------------------------

        conflicto_profesor = Horario.objects.filter(
            profesor=self.profesor,
            periodo=self.periodo,
            dia=self.dia,
            # Detectar superposición de horas
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk)

        if conflicto_profesor.exists():

            horario = conflicto_profesor.first()

            raise ValidationError(
                {
                    "profesor": f"El profesor {self.profesor} ya tiene asignada "
                    f'"{horario.asignatura}" '
                    f'de {horario.hora_inicio.strftime("%H:%M")} '
                    f'a {horario.hora_fin.strftime("%H:%M")}.'
                }
            )

        # --------------------------------------------------
        # CONFLICTO DE AULA
        # --------------------------------------------------

        conflicto_aula = Horario.objects.filter(
            aula=self.aula,
            periodo=self.periodo,
            dia=self.dia,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk)

        if conflicto_aula.exists():

            horario = conflicto_aula.first()

            raise ValidationError(
                {
                    "aula": f"El aula {self.aula} ya está ocupada "
                    f'por "{horario.asignatura}" '
                    f'de {horario.hora_inicio.strftime("%H:%M")} '
                    f'a {horario.hora_fin.strftime("%H:%M")}.'
                }
            )

        # --------------------------------------------------
        # CONFLICTO DEL MISMO SEMESTRE
        # --------------------------------------------------

        if self.asignatura_id:

            semestre = self.asignatura.semestre

            conflicto_semestre = Horario.objects.filter(
                asignatura__semestre=semestre,
                periodo=self.periodo,
                dia=self.dia,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio,
            ).exclude(pk=self.pk)

            if conflicto_semestre.exists():

                horario = conflicto_semestre.first()

                raise ValidationError(
                    {
                        "asignatura": f"El semestre {semestre.numero} ya tiene "
                        f'la asignatura "{horario.asignatura}" '
                        f'de {horario.hora_inicio.strftime("%H:%M")} '
                        f'a {horario.hora_fin.strftime("%H:%M")}.'
                    }
                )

    def __str__(self):
        return (
            f"{self.asignatura} - "
            f"{self.get_dia_display()} "
            f'{self.hora_inicio.strftime("%H:%M")} - '
            f'{self.hora_fin.strftime("%H:%M")}'
        )


# Create your models here.
