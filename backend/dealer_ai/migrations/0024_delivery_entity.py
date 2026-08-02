"""Milestone 9 · Increment 2 (SESSION_101) — Delivery entity.

Creates :class:`dealer_ai.models.Delivery` — the delivery-preparation
workflow row that a Sale transitions through before the customer
takes possession. Per ``MILESTONE_9_PLANNING.md`` §1.2 Option A
(user-confirmed at SESSION_101 open, recorded in §0.a).

**One operation shipped atomically.**

- ``CreateModel`` — :class:`Delivery`. OneToOne with :class:`Sale`
  (mandatory — every Delivery references a Sale at the DB level).
  ``checklist`` JSONField defaults to
  :func:`dealer_ai.models._default_delivery_checklist` (every M9.2
  key set to False). ``insurance_verified`` (boolean) +
  ``insurance_verified_at`` (timestamp) denormalized from the
  ``insurance_verified`` checklist key for query-ability at the
  compliance layer.

**No constraints or indexes at M9.2.** The OneToOne on ``sale``
already enforces "one Delivery per Sale" via the unique constraint
Django adds for OneToOneField. Composite indexes on
``(dealership, -created_at)`` and ``(insurance_verified,
dealership)`` land at M9.3+ if the aggregation queries surface hot
paths.

**Reverse: ``DeleteModel``.** Safe at M9.2 — nothing else in the DB
references ``dealer_ai_delivery`` and no other row FKs into it.

**Tenancy carrier extension** — ``Delivery`` is added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (23 → 24) in
the same session. The autofill signal is a safety net for callers
that bypass :func:`services.delivery.record_delivery`; the service
writes ``dealership`` explicitly on every row.

**No auto-creation on Sale write.** Option A's "mandatory OneToOne"
is the DB invariant "every Delivery has a Sale" — not "every Sale
auto-spawns a Delivery." Delivery is created via the M9.2 endpoint
after Sale creation. This preserves the M9.1 boundary — no
post_save signal on Sale, no coupling change in
:func:`services.sale.record_sale`.
"""

import dealer_ai.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0023_sale_entity_and_buyer_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="Delivery",
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
                ("delivery_date", models.DateField(blank=True, null=True)),
                (
                    "checklist",
                    models.JSONField(
                        blank=True, default=dealer_ai.models._default_delivery_checklist
                    ),
                ),
                (
                    "temp_tag_number",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                ("insurance_verified", models.BooleanField(default=False)),
                ("insurance_verified_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "sale",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="delivery",
                        to="dealer_ai.sale",
                    ),
                ),
            ],
            options={
                "verbose_name": "Delivery",
                "verbose_name_plural": "Deliveries",
                "ordering": ("-created_at",),
            },
        ),
    ]
