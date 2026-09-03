# SESSION_232 — TASK_de-ford-the-kit: Vehicle.make default "" (was "Ford"),
# Vehicle.condition default "used" (was "new"). No data change; new rows
# only. Two AlterFields, pre-approved in the task file.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0059_m228_1_outside_vendor_part_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehicle",
            name="make",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="condition",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("used", "Used"),
                    ("certified", "Certified Pre-Owned"),
                ],
                default="used",
                max_length=16,
            ),
        ),
    ]
