# SESSION_241 books-1 — the spine of the books.
#
# Two new fields on ``VehicleAcquisition`` per
# ``TASK_books-1-acquisition-and-relief.md``:
#
# - ``posted_at`` — datetime denormalization stamped by the
#   ``services.accounting.acquisition`` post_save signal when the
#   acquisition JE lands (DR 121000 Used Vehicle Inventory / CR 100000
#   Cash on Hand — CR 210000 Floor Plan Payable when ``is_floored``).
#   Null means the acquisition has never been booked. Mirrors
#   ``VehicleCost.posted_at`` (0044).
#
# - ``is_floored`` — the per-row switch that flips the credit side of
#   the acquisition JE from cash to floor plan. Off by default; the
#   store-level "we floor our cars" toggle is a later child of the
#   books scope (SCOPE_books-real-and-exportable.md) — this migration
#   just puts the plumbing in place so the branch is exercised.

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0064_dealership_timezone_default_blank"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicleacquisition",
            name="posted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="vehicleacquisition",
            name="is_floored",
            field=models.BooleanField(default=False),
        ),
    ]
