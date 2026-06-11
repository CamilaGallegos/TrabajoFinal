from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0004_auditoriaventa'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='monto_efectivo',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='venta',
            name='monto_transferencia',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='venta',
            name='tipo_pago',
            field=models.CharField(
                choices=[
                    ('efectivo', 'Efectivo'),
                    ('transferencia', 'Transferencia'),
                    ('combinado', 'Combinado'),
                    ('cuenta_abierta', 'Cuenta Abierta'),
                ],
                default='efectivo',
                max_length=20,
            ),
        ),
    ]
