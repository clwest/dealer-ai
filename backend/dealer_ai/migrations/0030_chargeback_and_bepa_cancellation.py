"""Milestone 10 · Increment 6 (SESSION_111) — Chargeback entity +
additive BEPA cancellation-field extension.

Three operations shipped atomically per
``MILESTONE_10_PLANNING.md`` §1.7 (six §1.7.a-f decisions
confirmed at SESSION_111 open, all as-recommended, recorded in
§0.a; the §5.c chargeback-impact decision was previously
confirmed at SESSION_106 open — Option B, additive verb only,
no M9 schema change).

**Additive BEPA extension per §1.7.c Option A.**

- ``AddField`` — ``BackEndProductAgreement.cancelled_at``
  DateTime nullable.
- ``AddField`` — ``BackEndProductAgreement.cancellation_amount``
  Decimal(10,2) nullable.

Both populated by the M10.6
:func:`services.f_and_i.record_chargeback` verb when
``chargeback_type=product_cancellation`` and the ``bepa`` FK is
set on the Chargeback. Same additive-extension pattern used at
M10.2 for M10.1 CreditApplication income columns.

**New Chargeback entity per §1.7.a Option A.**

- ``CreateModel`` — :class:`Chargeback`. Nullable FKs to both
  :class:`Contract` (CASCADE) + :class:`BackEndProductAgreement`
  (CASCADE) per §1.7.a. clean() requires at least one set.
  Fields: ``chargeback_type`` from fixed 5+1 vocab per §1.7.b
  Option B, ``chargeback_date`` (operator-provided business
  date), ``chargeback_amount`` Decimal (positive; sign is
  implicit), ``recorded_by`` FK to
  ``settings.AUTH_USER_MODEL`` SET_NULL per §1.7.e Option A,
  ``notes`` TextField. Ordering
  ``(-chargeback_date, -created_at)``.

**Funding auto-transition side effect** per §1.7.f Option A.
The M10.6 service verb transitions the associated Funding row
to ``chargedback`` state atomically when ``chargeback_type`` is
one of the four deal-level types
(``first_payment_default`` / ``early_payoff`` /
``repossession`` / ``deal_unwind``). ``product_cancellation``
and ``other`` chargebacks do not touch Funding state.

**No indexes at M10.6.** Composite indexes on
``(dealership, -chargeback_date)`` land at M10.7+ if
aggregation surfaces hot paths.

**Reverse: ``DeleteModel`` + two ``RemoveField``.** Safe at
M10.6 — nothing else references ``dealer_ai_chargeback``, and
the BEPA columns are nullable (reversing loses M10.6 data but
doesn't break the schema).

**Tenancy carrier extension** — ``Chargeback`` added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (32 → 33)
in the same session. The autofill signal is a safety net for
callers that bypass :mod:`services.f_and_i.chargeback`.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0029_contract_funding"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="backendproductagreement",
            name="cancellation_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="backendproductagreement",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Chargeback",
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
                    "chargeback_type",
                    models.CharField(
                        choices=[
                            ("first_payment_default", "First payment default"),
                            ("early_payoff", "Early payoff"),
                            ("product_cancellation", "Product cancellation"),
                            ("repossession", "Repossession"),
                            ("deal_unwind", "Deal unwind"),
                            ("other", "Other"),
                        ],
                        max_length=32,
                    ),
                ),
                ("chargeback_date", models.DateField()),
                (
                    "chargeback_amount",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "bepa",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chargebacks",
                        to="dealer_ai.backendproductagreement",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chargebacks",
                        to="dealer_ai.contract",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chargebacks",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chargebacks_recorded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Chargeback",
                "verbose_name_plural": "Chargebacks",
                "ordering": ("-chargeback_date", "-created_at"),
            },
        ),
    ]
