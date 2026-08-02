"""Milestone 10 · Increment 2 (SESSION_107) — DealStructure entity
+ additive CreditApplication income/debt columns.

Two additive operations + one CreateModel per
``MILESTONE_10_PLANNING.md`` §1.2 + §1.2.a Option A (user-
confirmed at SESSION_107 open, recorded in §0.a).

**Additive extension of M10.1's CreditApplication.**

- ``AddField`` — ``CreditApplication.gross_monthly_income``,
  nullable Decimal(10,2). Native credit-app data per FINANCE §1.5.
  M10.1-era rows land with NULL; M10.2 PTI / DTI verbs return
  ``None`` for NULL and downstream compliance filters treat NULL
  as "not computable." Follows the M8 §6 lesson 11 additive-
  extension pattern.
- ``AddField`` — ``CreditApplication.existing_monthly_debt``,
  nullable Decimal(10,2). Bureau-response artifact per FINANCE
  §1.10 (operator-entered from the bureau report at M10.2;
  bureau-integration is deferred beyond M10). Same NULL posture
  as ``gross_monthly_income``.

**New DealStructure entity per §1.2.**

- ``CreateModel`` — :class:`DealStructure`. FK to
  :class:`CreditApplication` (parent — CASCADE) + FK to
  :class:`Vehicle` (target unit — CASCADE). Standard M-to-1
  (multiple deal-structures per credit-app; F&I iterates as
  lender terms evolve). Fields per §1.2: sale_price / down /
  trade_allowance / trade_payoff / taxes / fees / amount_financed /
  apr (percent units per :mod:`services.payment_engine`
  convention) / term_months / monthly_payment / back_end_products
  (JSONField default list — vocabulary partitioning deferred to
  M10.5 Contract) + denormalized ratio outputs (``ltv_pct`` /
  ``pti_pct`` / ``dti_pct``) populated at write time by the
  M10.2 service verbs.

**No constraints or indexes at M10.2.** Composite indexes on
``(dealership, -created_at)`` and ``(credit_application,
-created_at)`` land at M10.5+ if aggregation surfaces hot paths.

**Reverse: ``DeleteModel`` + ``RemoveField`` × 2.** Safe at
M10.2 — nothing else FKs into ``dealer_ai_dealstructure`` at
this point, and the CreditApplication columns are nullable
(reversing loses M10.2 data but doesn't break the schema).

**Tenancy carrier extension** — ``DealStructure`` is added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (25 → 26)
in the same session. The autofill signal is a safety net for
callers that bypass
:func:`services.f_and_i.deal_structure.record_deal_structure`;
the service writes ``dealership`` explicitly on every row.
"""

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0025_credit_application_entity"),
    ]

    operations = [
        migrations.AddField(
            model_name="creditapplication",
            name="existing_monthly_debt",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="creditapplication",
            name="gross_monthly_income",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.CreateModel(
            name="DealStructure",
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
                ("sale_price", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "down_payment",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "trade_allowance",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "trade_payoff",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "taxes",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "fees",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "amount_financed",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("apr", models.DecimalField(decimal_places=4, max_digits=6)),
                ("term_months", models.PositiveIntegerField()),
                (
                    "monthly_payment",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("back_end_products", models.JSONField(blank=True, default=list)),
                (
                    "ltv_pct",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=6, null=True
                    ),
                ),
                (
                    "pti_pct",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=6, null=True
                    ),
                ),
                (
                    "dti_pct",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=6, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "credit_application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_structures",
                        to="dealer_ai.creditapplication",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_structures",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deal_structures",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Deal structure",
                "verbose_name_plural": "Deal structures",
                "ordering": ("-created_at",),
            },
        ),
    ]
