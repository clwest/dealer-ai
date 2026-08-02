"""Milestone 10 · Increment 5 (SESSION_110) — Contract +
BackEndProductAgreement + Funding entities.

Three operations shipped atomically per
``MILESTONE_10_PLANNING.md`` §1.5 + §1.6 (all five decisions
confirmed at SESSION_110 open, recorded in §0.a).

**Three new entities.**

- ``CreateModel`` — :class:`Contract`. Mandatory FK to
  :class:`DealStructure` CASCADE per §1.5.c Option A. Fields
  per §1.5: ``contract_type`` (RISC / lease / cash), ``state``
  (unsigned default / signed / voided per §1.5.b Option A),
  ``signer_name``, ``signed_at``, ``financed_amount`` /
  ``total_of_payments`` / ``finance_charge`` /
  ``apr_disclosure`` (Reg Z Truth in Lending Act mandatory
  disclosures per FINANCE §6.1), ``first_payment_date``,
  ``voided_at`` + ``voided_reason``.
- ``CreateModel`` — :class:`BackEndProductAgreement`. FK to
  :class:`Contract` CASCADE per §1.5.a Option B (per-product
  rows enable M10.6 per-product chargeback attribution).
  Fixed ``product_type`` vocabulary per §1.5.d Option A (VSC
  / GAP / T&W / prepaid maintenance / appearance / other).
  Fields: ``cost`` / ``retail_price`` (base at-write
  economics) + optional ``term_months`` / ``mileage_limit`` /
  ``deductible`` per FINANCE §4.3-§4.5 shape. Cancellation
  fields deferred to M10.6.
- ``CreateModel`` — :class:`Funding`. OneToOne to
  :class:`Contract` CASCADE per §1.6.a Option C (one funding
  per contract; unwinds / re-signs require a new Contract
  row per FINANCE §5.8). State machine: ``pending_funding``
  default → ``funded`` → optional ``chargedback`` (M10.6
  wires the transition — vocabulary shipped now to avoid
  data migration then).

**No persisted FundingPacket** per §1.6.a Option C — the packet
is a computed view over Contract + Stipulation + related rows.
M10.7 compliance layer can materialize a packet report if
operators need one.

**No cancellation fields on BackEndProductAgreement** per §0.a
resolution — ``cancelled_at`` + ``cancellation_amount`` are
M10.6 Chargeback concerns and land there.

**No indexes at M10.5.** Composite indexes on
``(dealership, -created_at)`` land at M10.7+ if aggregation
surfaces hot paths.

**Reverse: three ``DeleteModel`` operations.** Safe at M10.5 —
nothing else in the DB references these tables.

**Tenancy carrier extension** — all three entities added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (29 → 32)
in the same session. The autofill signal is a safety net for
callers that bypass the M10.5 service verbs
(:mod:`services.f_and_i.contract` +
:mod:`services.f_and_i.funding`).
"""

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0028_stipulation_entity"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contract",
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
                    "contract_type",
                    models.CharField(
                        choices=[
                            ("risc", "Retail Installment Sale Contract"),
                            ("lease", "Lease"),
                            ("cash", "Cash"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("unsigned", "Unsigned (drafted)"),
                            ("signed", "Signed"),
                            ("voided", "Voided"),
                        ],
                        default="unsigned",
                        max_length=16,
                    ),
                ),
                (
                    "signer_name",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("signed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "financed_amount",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "total_of_payments",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "finance_charge",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=10
                    ),
                ),
                (
                    "apr_disclosure",
                    models.DecimalField(
                        decimal_places=4, default=Decimal("0.0000"), max_digits=6
                    ),
                ),
                ("first_payment_date", models.DateField(blank=True, null=True)),
                ("voided_at", models.DateTimeField(blank=True, null=True)),
                ("voided_reason", models.TextField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "deal_structure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contracts",
                        to="dealer_ai.dealstructure",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contracts",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contract",
                "verbose_name_plural": "Contracts",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="BackEndProductAgreement",
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
                    "product_type",
                    models.CharField(
                        choices=[
                            ("vsc", "Vehicle Service Contract"),
                            ("gap", "GAP (Guaranteed Asset Protection)"),
                            ("t_and_w", "Tire & Wheel"),
                            ("prepaid_maint", "Prepaid maintenance"),
                            ("appearance", "Appearance / paintless dent repair"),
                            ("other", "Other"),
                        ],
                        max_length=32,
                    ),
                ),
                ("provider", models.CharField(blank=True, default="", max_length=255)),
                ("cost", models.DecimalField(decimal_places=2, max_digits=10)),
                ("retail_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("term_months", models.PositiveIntegerField(blank=True, null=True)),
                ("mileage_limit", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "deductible",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="back_end_product_agreements",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="back_end_products",
                        to="dealer_ai.contract",
                    ),
                ),
            ],
            options={
                "verbose_name": "Back-end product agreement",
                "verbose_name_plural": "Back-end product agreements",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="Funding",
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
                    "state",
                    models.CharField(
                        choices=[
                            ("pending_funding", "Pending funding"),
                            ("funded", "Funded"),
                            ("chargedback", "Chargedback (M10.6)"),
                        ],
                        default="pending_funding",
                        max_length=32,
                    ),
                ),
                ("submitted_to_lender_at", models.DateTimeField(blank=True, null=True)),
                ("funded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "funding_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "contract",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="funding",
                        to="dealer_ai.contract",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fundings",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Funding",
                "verbose_name_plural": "Fundings",
                "ordering": ("-created_at",),
            },
        ),
    ]
