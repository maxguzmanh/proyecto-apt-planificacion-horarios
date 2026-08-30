from django.contrib import admin

from .models import (
    CentroTutorial,
    Sede,
    Facultad,
    Carrera,
    PeriodoAcademico,
    Semestre,
    Asignatura,
    Profesor,
    Aula,
)

admin.site.register(CentroTutorial)
admin.site.register(Sede)
admin.site.register(Facultad)
admin.site.register(Carrera)
admin.site.register(PeriodoAcademico)
admin.site.register(Semestre)
admin.site.register(Asignatura)
admin.site.register(Profesor)
admin.site.register(Aula)

# Register your models here.
