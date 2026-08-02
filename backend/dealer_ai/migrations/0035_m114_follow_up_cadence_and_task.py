"""Milestone 11 · Increment 4 (SESSION_117) — FollowUpCadence + FollowUpTask.

Two-entity schedule model per MILESTONE_11_PLANNING.md §1.4 + §5.d
Option A (user-confirmed at SESSION_114 open, recorded in §0.a). Task
rows are queryable independently for the operator's "tasks due today"
view; cadence rows own template + started_at + is_active.

Tenancy carriers registered at
``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`` (36 → 38).

The M11.4 Celery-beat orchestrator
(:mod:`services.follow_ups.tasks`) surfaces due tasks via a daily
beat entry at 06:00 project-time (next slot after M7.2-M7.5 at
02:00-05:00). State transitions are operator-triggered only per
SESSION_117 §0.a M11.4 amendment (decision 3) — the beat surfacer
never mutates state, only logs the surfaced-count.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0034_m113_deal_writeup_entity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FollowUpCadence",
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
                    "template",
                    models.CharField(
                        choices=[
                            ("24hr", "24 hours"),
                            ("1wk", "1 week"),
                            ("30day", "30 days"),
                            ("90day", "90 days"),
                            ("6mo", "6 months"),
                            ("1yr", "1 year"),
                        ],
                        max_length=16,
                    ),
                ),
                ("started_at", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="follow_up_cadences",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="follow_up_cadences",
                        to="dealer_ai.customerlead",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="FollowUpTask",
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
                ("due_at", models.DateTimeField(db_index=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cadence",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="dealer_ai.followupcadence",
                    ),
                ),
                (
                    "completed_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="follow_up_tasks_completed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="follow_up_tasks",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "ordering": ["due_at"],
            },
        ),
    ]
