from django.contrib import admin
from .models import Horario


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):

    list_display = (
        'asignatura',
        'profesor',
        'aula',
        'periodo',
        'dia',
        'hora_inicio',
        'hora_fin',
    )

    list_filter = (
        'periodo',
        'dia',
        'aula',
    )

    search_fields = (
        'asignatura__nombre',
        'profesor__nombre',
        'profesor__apellido',
        'aula__nombre',
    )
# Register your models here.
