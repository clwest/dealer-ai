"""Milestone 7 · Increment 1 (SESSION_088) — JobRunLog.

Creates :class:`dealer_ai.models.JobRunLog` — the observability substrate
for every ``@instrumented_task`` invocation across M7.2-M7.5 scheduled
jobs. Per ``MILESTONE_7_PLANNING.md`` §5.e Option A (user-confirmed at
SESSION_088 open).

**Single ``CreateModel`` operation.** No backfill — new tenants and
existing tenants both start with an empty ``dealer_ai_jobrunlog`` table
because M7.1 registers no scheduled tasks. The first row lands when M7.2
ships the floor-plan interest accrual task and Beat fires it (dev / prod)
or when a test invokes an ``@instrumented_task``-wrapped task under
``CELERY_TASK_ALWAYS_EAGER``.

**Two indexes.** Django autogenerates the ``task_name`` and ``status``
b-tree indexes from ``db_index=True``. The composite
``(task_name, -started_at)`` index (``jrl_task_started_idx``) supports the
M8 dashboard's "most-recent run of task X" query without a full-table
scan.

**Reverse: ``DeleteModel``.** Safe — no other row anywhere in the DB
references ``dealer_ai_jobrunlog`` at M7.1 close. Future M8 dashboards
that materialize aggregates over this table will not FK back to it.

**No M1-M6 substrate touched.** Only ``JobRunLog`` is created.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0019_vehicle_photo_public_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobRunLog",
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
                ("task_name", models.CharField(db_index=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("started", "Started"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("retried", "Retried"),
                        ],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("started_at", models.DateTimeField()),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, default="")),
                (
                    "args_summary",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="job_run_logs",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Job run log",
                "verbose_name_plural": "Job run logs",
                "ordering": ("-started_at",),
                "indexes": [
                    models.Index(
                        fields=["task_name", "-started_at"], name="jrl_task_started_idx"
                    )
                ],
            },
        ),
    ]
