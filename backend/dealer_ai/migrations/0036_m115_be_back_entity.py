"""Milestone 11 · Increment 5 (SESSION_118) — BeBack entity.

New per MILESTONE_11_PLANNING.md §1.5 + §5.g Options A / A / B
(recorded in §0.a at SESSION_118 open). Mandatory FK to CustomerLead
(CASCADE); no FK to Vehicle. Reason vocab 4+1
(test_drive / bring_co_signer / bring_trade_in / other). State
vocab promised / returned / no_show.

Tenancy carrier registered at
``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`` (38 → 39).

The M11.5 Celery detector
(:mod:`services.be_backs.tasks`) transitions promised → no_show
when ``promised_at + BE_BACK_NO_SHOW_GRACE_HOURS`` passes without
``actual_return_at``. Runs at 07:00 project-time daily via
``CELERY_BEAT_SCHEDULE`` in ``dealer_kit/settings.py`` (next slot
after M11.4 at 06:00).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0035_m114_follow_up_cadence_and_task"),
    ]

    operations = [
        migrations.CreateModel(
            name="BeBack",
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
                    "promised_at",
                    models.DateTimeField(
                        help_text="When the customer said they would return."
                    ),
                ),
                (
                    "promised_reason",
                    models.CharField(
                        choices=[
                            ("test_drive", "Test drive"),
                            ("bring_co_signer", "Bring co-signer"),
                            ("bring_trade_in", "Bring trade-in"),
                            ("other", "Other"),
                        ],
                        max_length=32,
                    ),
                ),
                ("actual_return_at", models.DateTimeField(blank=True, null=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("promised", "Promised"),
                            ("returned", "Returned"),
                            ("no_show", "No-show"),
                        ],
                        default="promised",
                        max_length=16,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="be_backs",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="be_backs",
                        to="dealer_ai.customerlead",
                    ),
                ),
            ],
            options={
                "ordering": ["-promised_at"],
            },
        ),
    ]
