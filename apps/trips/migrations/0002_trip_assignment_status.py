from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("trips", "0001_initial")]

    operations = [
        migrations.AddField(model_name="trip", name="passenger_picked_up_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(
            model_name="trip",
            name="status",
            field=models.CharField(
                choices=[("assigned", "Назначена"), ("active", "Выполняется"), ("completed", "Завершена"), ("cancelled", "Отменена")],
                db_index=True,
                default="active",
                max_length=16,
            ),
        ),
    ]
