"""Milestone 9 · Increment 1 (SESSION_100) — Sale entity + acquisition-buyer FK.

Creates :class:`dealer_ai.models.Sale` (the closing event that turns
a Vehicle from inventory into a completed transaction) and adds the
nullable ``buyer`` FK on :class:`dealer_ai.models.VehicleAcquisition`
(the in-house purchase decision-maker Q7 needs to compute buyer-
estimate accuracy). Per ``MILESTONE_9_PLANNING.md`` §1.1 + §5.a
Option A + §5.b Option A + §5.c Option A (all user-confirmed at
SESSION_100 open, recorded in §0.a).

**Two operations shipped atomically.**

1. ``AddField`` — ``VehicleAcquisition.buyer`` FK to
   ``settings.AUTH_USER_MODEL``, nullable + SET_NULL. §5.a Option A
   ("bundle into M9"). Historical acquisition rows populate NULL —
   the M9.4 :func:`services.analytics.recon.buyer_estimate_accuracy`
   verb excludes NULL rows from the aggregation rather than
   treating them as a single anonymous buyer bucket.
2. ``CreateModel`` — :class:`Sale`. OneToOne with Vehicle. §5.b
   Option A places ``buyer`` FK on ``CustomerLead`` (reuses M3-M5
   CRM substrate). §5.c Option A locks the initial finance-type
   vocabulary to ``cash`` / ``retail`` / ``bhph``.

**No constraints or indexes at M9.1.** The OneToOne on ``vehicle``
already enforces "one Sale per Vehicle" at the DB level via the
unique constraint Django adds for OneToOneField. Composite indexes
land at M9.3 if the aggregation queries surface hot paths.

**Reverse: field removal + ``DeleteModel``.** Safe at M9.1 —
nothing else in the DB references ``dealer_ai_sale`` and the
``buyer`` FK addition on ``VehicleAcquisition`` is pure additive
(nullable). Reversibility survives until M9.2 adds Delivery FK to
Sale.

**Tenancy carrier extension** — ``Sale`` is added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (22 → 23) in
the same session. The autofill signal is a safety net for callers
that bypass :func:`services.sale.record_sale`; the service writes
``dealership`` explicitly on every row.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0022_sla_breach_record"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicleacquisition",
            name="buyer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="acquisitions_bought",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="Sale",
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
                ("sale_date", models.DateField()),
                ("sold_price", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "finance_type",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("retail", "Retail (bank / credit union)"),
                            ("bhph", "Buy-here-pay-here"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "lender_name",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "gross_realized",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sales",
                        to="dealer_ai.customerlead",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sales",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "vehicle",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sale",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sale",
                "verbose_name_plural": "Sales",
                "ordering": ("-sale_date", "-created_at"),
            },
        ),
    ]
