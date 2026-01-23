from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vinculacion', '0004_alter_logintegracion_accion'),
    ]

    operations = [
        migrations.AddField(
            model_name='preregistro',
            name='intentos_biometria',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Intentos fallidos de validacion biometrica'
            ),
        ),
        migrations.AddField(
            model_name='preregistro',
            name='vetado',
            field=models.BooleanField(
                default=False,
                help_text='Bloquea nuevos intentos hasta apertura manual'
            ),
        ),
    ]
