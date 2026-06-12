from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("herramientas", "0002_herramienta_token"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="herramienta",
            name="token",
        ),
    ]
