"""Milestone 7 · Increment 3 (SESSION_090) — StageAgingSnapshot.

Creates :class:`dealer_ai.models.StageAgingSnapshot` — the persisted
output of the M7.3 aging-per-stage snapshot job. Per
``MILESTONE_7_PLANNING.md`` §5.c Option A (user-confirmed at SESSION_088
open).

**Single ``CreateModel`` operation.** No backfill — new tenants and
existing tenants both start with an empty ``dealer_ai_stageagingsnapshot``
table. The first row lands when the M7.3 Beat entry fires at 03:00
project-time daily (or when a test invokes the verb / task under
``CELERY_TASK_ALWAYS_EAGER=True``).

**Two indexes.** Django autogenerates the ``snapshot_at`` b-tree index
from ``db_index=True``. The composite
``(dealership, stage, -snapshot_at)`` index
(``sas_tenant_stage_time_idx``) supports the M8 dashboard's "aging
history for tenant X, stage Y" query without a full-table scan.

**Reverse: ``DeleteModel``.** Safe — no other row anywhere in the DB
references ``dealer_ai_stageagingsnapshot`` at M7.3 close. Future M8
dashboards that materialize aggregates over this table will not FK
back to it.

**No M1-M7.2 substrate touched.** Only ``StageAgingSnapshot`` is
created.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0020_job_run_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="StageAgingSnapshot",
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
                    "stage",
                    models.CharField(
                        choices=[
                            ("incoming", "Incoming"),
                            ("inspection", "Inspection"),
                            ("recon", "Recon"),
                            ("qc", "QC"),
                            ("detail", "Detail"),
                            ("photography", "Photography"),
                            ("listing", "Listing"),
                            ("frontline", "Frontline"),
                            ("wholesale_out", "Wholesale out"),
                            ("hold_reserved", "Hold / reserved"),
                            ("company_use", "Company use"),
                            ("off_market", "Off market"),
                        ],
                        max_length=32,
                    ),
                ),
                ("snapshot_at", models.DateTimeField(db_index=True)),
                ("vehicle_count", models.PositiveIntegerField()),
                ("p50_days", models.PositiveIntegerField()),
                ("p90_days", models.PositiveIntegerField()),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stage_aging_snapshots",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stage aging snapshot",
                "verbose_name_plural": "Stage aging snapshots",
                "ordering": ("-snapshot_at", "stage"),
                "indexes": [
                    models.Index(
                        fields=["dealership", "stage", "-snapshot_at"],
                        name="sas_tenant_stage_time_idx",
                    )
                ],
            },
        ),
    ]
