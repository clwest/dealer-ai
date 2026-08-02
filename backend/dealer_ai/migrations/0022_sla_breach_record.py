"""Milestone 8 · Increment 1 (SESSION_094) — SlaBreachRecord.

Creates :class:`dealer_ai.models.SlaBreachRecord` — the persisted
counterpart to the M7.4 vendor-SLA-breach detection verb's
``logging.WARNING`` records. Per ``MILESTONE_8_PLANNING.md`` §5.b
Option B (user-confirmed at SESSION_094 open).

**Two operations.** ``CreateModel`` for the row shape + one
``AddConstraint`` for the ``(work_order, kind, detected_at_date)``
uniqueness invariant that anchors the M7.4 daily-scan idempotency.

**Three indexes.** Django autogenerates the ``detected_at`` b-tree
index from ``db_index=True``. The composite
``(dealership, kind, -detected_at)`` index
(``sbr_tenant_kind_time_idx``) supports the M8.3 dashboard's "breach
patterns for tenant X, kind Y" query without a full-table scan. The
unique constraint itself creates a third index over
``(work_order, kind, detected_at_date)`` — used by the M7.4 verb's
``get_or_create`` collision check.

**Reverse: ``DeleteModel``.** Safe — no other row anywhere in the DB
references ``dealer_ai_slabreachrecord`` at M8.1 close. M8.3
aggregation reads via ``.values()`` / ``.aggregate()`` don't FK back
to it.

**No M1-M7 substrate touched.** Only ``SlaBreachRecord`` is created.
The M7.4 verb-extension writing rows into this table lives in
``services/vendor_sla/detection.py`` — a code change, not a
migration.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0021_stage_aging_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="SlaBreachRecord",
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
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("in_progress_past_eta", "In progress past ETA"),
                            ("approved_stale", "Approved stale"),
                        ],
                        max_length=32,
                    ),
                ),
                ("breach_days", models.PositiveIntegerField()),
                ("detected_at", models.DateTimeField(db_index=True)),
                ("detected_at_date", models.DateField()),
                ("vehicle_stock", models.CharField(max_length=64)),
                ("vendor_name", models.CharField(max_length=255)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sla_breach_records",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "work_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sla_breach_records",
                        to="dealer_ai.workorder",
                    ),
                ),
            ],
            options={
                "verbose_name": "SLA breach record",
                "verbose_name_plural": "SLA breach records",
                "ordering": ("-detected_at",),
                "indexes": [
                    models.Index(
                        fields=["dealership", "kind", "-detected_at"],
                        name="sbr_tenant_kind_time_idx",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="slabreachrecord",
            constraint=models.UniqueConstraint(
                fields=("work_order", "kind", "detected_at_date"),
                name="sbr_wo_kind_date_uq",
            ),
        ),
    ]
