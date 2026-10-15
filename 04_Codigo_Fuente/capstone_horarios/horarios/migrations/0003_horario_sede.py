from datetime import time

import django.db.models.deletion
from django.db import migrations, models


def poblar_sedes(apps, schema_editor):
    Horario = apps.get_model("horarios", "Horario")
    Sede = apps.get_model("academico", "Sede")
    alias = schema_editor.connection.alias
    horarios = list(Horario.objects.using(alias).filter(sede__isnull=True).select_related(
        "aula", "oferta__profesor", "oferta__asignatura", "oferta__periodo"))
    asignaciones = []
    for horario in horarios:
        if horario.aula_id:
            sede_id = horario.aula.sede_id
        elif (horario.pk == 11 and horario.oferta.profesor.identificacion == "DOC-DEMO-001"
              and horario.oferta.asignatura.codigo == "ARQ01" and horario.oferta.periodo.codigo == "01-2026"
              and horario.dia == "LU" and horario.hora_inicio == time(7) and horario.hora_fin == time(8)):
            # Asignación explícita confirmada por el usuario para el único pendiente
            # existente al preparar esta migración; no es un valor predeterminado.
            sede_id = Sede.objects.using(alias).get(codigo="SEDE-ACA", centro_tutorial__codigo="CT-DEMO").pk
        else:
            raise RuntimeError(f"No se puede deducir la sede del horario {horario.pk} sin aula. Debe confirmarse explícitamente antes de migrar.")
        asignaciones.append((horario.pk, sede_id))
    for pk, sede_id in asignaciones:
        Horario.objects.using(alias).filter(pk=pk).update(sede_id=sede_id)


class Migration(migrations.Migration):
    dependencies = [("horarios", "0002_alter_horario_aula")]
    operations = [
        migrations.AddField(model_name="horario", name="sede", field=models.ForeignKey(
            null=True, on_delete=django.db.models.deletion.PROTECT, related_name="horarios_planificados", to="academico.sede")),
        migrations.RunPython(poblar_sedes, migrations.RunPython.noop),
        migrations.AlterField(model_name="horario", name="sede", field=models.ForeignKey(
            on_delete=django.db.models.deletion.PROTECT, related_name="horarios_planificados", to="academico.sede")),
    ]
