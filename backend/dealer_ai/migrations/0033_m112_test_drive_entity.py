"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive entity.

New per MILESTONE_11_PLANNING.md §1.2 + §5.c Option A (user-confirmed
at SESSION_114 open, recorded in §0.a). Mandatory FKs to CustomerLead
+ Vehicle (both CASCADE); optional FK to auth User (driven_by_user,
SET_NULL) for the salesperson who accompanied the drive. Tenancy
carrier registered at ``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES``
(34 → 35) so ad-hoc creates without an explicit ``dealership=`` still
land on the default tenant via the pre_save autofill safety net.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0032_m111_lead_channel_and_referrer"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TestDrive",
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
                ("driven_at", models.DateTimeField()),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("route_notes", models.TextField(blank=True, default="")),
                ("customer_reaction", models.TextField(blank=True, default="")),
                ("objections_captured", models.JSONField(blank=True, default=list)),
                ("next_action", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_drives",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "driven_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="test_drives_conducted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_drives",
                        to="dealer_ai.customerlead",
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_drives",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "ordering": ["-driven_at"],
            },
        ),
    ]
