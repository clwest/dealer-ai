"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup entity.

New per MILESTONE_11_PLANNING.md §1.3 + §5.e Option A (user-confirmed
at SESSION_114 open, recorded in §0.a). Mandatory FKs to CustomerLead
+ Vehicle (both CASCADE); optional user attributions on written /
approved. Tenancy carrier registered at
``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`` (35 → 36).

The F&I handoff verb (:func:`services.deal_writeups.hand_off_to_fandi`)
auto-creates a matching M10.1 :class:`CreditApplication` via the
existing :func:`services.f_and_i.record_credit_application` verb; the
CA is a peer row (retention clock is the M10.1 record of record),
not a child of the writeup — so no FK on either side. Their shared
lead FK is the linking key.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0033_m112_test_drive_entity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DealWriteup",
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
                    "vehicle_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "trade_allowance",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "down_payment",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "monthly_payment_target",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "term_months_target",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "apr_target",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("write_up_at", models.DateTimeField()),
                (
                    "sales_manager_approved_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("handed_off_to_fandi_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_writeups",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_writeups",
                        to="dealer_ai.customerlead",
                    ),
                ),
                (
                    "sales_manager_approved_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deal_writeups_approved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_writeups",
                        to="dealer_ai.vehicle",
                    ),
                ),
                (
                    "written_up_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deal_writeups_written",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-write_up_at"],
            },
        ),
    ]
