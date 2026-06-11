import uuid
from django.db import migrations, models


def generar_tokens(apps, schema_editor):
    Herramienta = apps.get_model("herramientas", "Herramienta")
    for h in Herramienta.objects.all():
        h.token = uuid.uuid4()
        h.save(update_fields=["token"])


class Migration(migrations.Migration):

    dependencies = [
        ("herramientas", "0001_initial"),
    ]

    operations = [
        # 1. Agregar columna sin unique, con un valor temporal fijo
        migrations.AddField(
            model_name="herramienta",
            name="token",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        # 2. Rellenar cada fila con un UUID único
        migrations.RunPython(generar_tokens, migrations.RunPython.noop),
        # 3. Aplicar la restricción unique
        migrations.AlterField(
            model_name="herramienta",
            name="token",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
