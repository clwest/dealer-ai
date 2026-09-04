# SESSION_243 books-2 — three floor companies, some cars still in cash.
#
# Per ``docs/_internal/TASK_books-2-three-floor-companies.md``:
#
# - New ``FloorPlanCompany`` model. Dealer-maintained panel entry with
#   name, code, contact, apr. Same shape decision as the F&I
#   ``LenderProgram`` panel — the two are deliberately separate models
#   because the domains differ (inventory financing vs consumer credit)
#   and share no lifecycle. Uniqueness on (dealership, name).
#
# - Nullable FK from ``VehicleAcquisition`` to ``FloorPlanCompany`` with
#   ``on_delete=PROTECT`` — a panel row that has ever floored a car
#   cannot be hard-deleted; deactivate via ``is_active=False`` instead.
#   NULL means the car was paid for in cash and held in house — a real
#   state, not a missing value.
#
# The ``is_floored`` boolean on ``VehicleAcquisition`` (added 0065) is
# now derived from ``floor_plan_company_id`` and kept in sync by the
# model's ``save()`` — no migration changes it. Removing the field
# entirely was considered and put on the ask list of the task file
# rather than shipping a third migration this session.

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0065_vehicleacquisition_posted_at_and_floor"),
    ]

    operations = [
        migrations.CreateModel(
            name="FloorPlanCompany",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("code", models.CharField(max_length=16)),
                ("contact", models.CharField(blank=True, default="", max_length=255)),
                (
                    "apr",
                    models.DecimalField(decimal_places=4, default=0, max_digits=6),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="floor_plan_companies",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Floor plan company",
                "verbose_name_plural": "Floor plan companies",
                "ordering": ("name",),
            },
        ),
        migrations.AddConstraint(
            model_name="floorplancompany",
            constraint=models.UniqueConstraint(
                fields=("dealership", "name"),
                name="unique_floor_plan_company_name_per_dealership",
            ),
        ),
        migrations.AddField(
            model_name="vehicleacquisition",
            name="floor_plan_company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="acquisitions",
                to="dealer_ai.floorplancompany",
            ),
        ),
    ]
