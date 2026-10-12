from django.db import models


class DiaSemana(models.TextChoices):
    LUNES = "LU", "Lunes"
    MARTES = "MA", "Martes"
    MIERCOLES = "MI", "Miércoles"
    JUEVES = "JU", "Jueves"
    VIERNES = "VI", "Viernes"
    SABADO = "SA", "Sábado"
    DOMINGO = "DO", "Domingo"
