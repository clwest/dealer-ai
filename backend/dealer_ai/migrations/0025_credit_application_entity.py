"""Milestone 10 · Increment 1 (SESSION_106) — CreditApplication entity.

Creates :class:`dealer_ai.models.CreditApplication` — the customer
credit application intake row per
``FINANCE_DEPARTMENT_MAPPING.md`` §1.1 and
``MILESTONE_10_PLANNING.md`` §5.a Option C (user-confirmed at
SESSION_106 open, recorded in §0.a).

**One operation shipped atomically.**

- ``CreateModel`` — :class:`CreditApplication`. Nullable FKs to
  both :class:`CustomerLead` (``lead``) and :class:`Sale`
  (``sale``) per §5.a Option C. ``captured_at`` starts the
  retention clock; ``retention_expires_at`` is denormalized at
  write time (``captured_at + CREDIT_APP_RETENTION_YEARS``) so
  compliance-audit queries can filter without per-row date
  arithmetic. Model-layer :meth:`CreditApplication.delete`
  refuses unexpired records — per
  ``MILESTONE_10_PLANNING.md`` §5.e retention is a model-layer
  invariant, not a service-layer one.

**No constraints or indexes at M10.1.** Composite indexes on
``(dealership, -captured_at)`` and ``(retention_expires_at,
dealership)`` land at M10.7+ if the compliance-audit queries
surface hot paths.

**Reverse: ``DeleteModel``.** Safe at M10.1 — nothing else in the
DB references ``dealer_ai_creditapplication`` and no other row
FKs into it.

**Tenancy carrier extension** — ``CreditApplication`` is added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (24 → 25)
in the same session. The autofill signal is a safety net for
callers that bypass :func:`services.f_and_i.record_credit_application`;
the service writes ``dealership`` explicitly on every row.

**Minimal PII surface at M10.1.** Only ``applicant_full_name`` +
optional ``applicant_ssn_last4`` at rest. Full SSN / DOB /
driver's-license number land with the M10.7 Safeguards Rule
technical-controls layer (encryption at rest, access logging,
field-level ACLs per FINANCE §6.4). Storing full SSN before that
layer ships would violate the Safeguards Rule; the schema is
intentionally narrow so M10.1 cannot become a compliance-debt
substrate.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0024_delivery_entity"),
    ]

    operations = [
        migrations.CreateModel(
            name="CreditApplication",
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
                ("applicant_full_name", models.CharField(max_length=255)),
                (
                    "applicant_ssn_last4",
                    models.CharField(blank=True, default="", max_length=4),
                ),
                (
                    "source_format",
                    models.CharField(
                        choices=[
                            ("paper", "Paper (clipboard)"),
                            ("tablet", "In-store tablet / terminal"),
                            ("online_prequal", "Online pre-qualification"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("received", "Received (not yet submitted)"),
                            ("submitted", "Submitted to lender(s)"),
                            ("withdrawn", "Withdrawn"),
                        ],
                        default="received",
                        max_length=32,
                    ),
                ),
                ("captured_at", models.DateTimeField()),
                ("retention_expires_at", models.DateTimeField()),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credit_applications",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="credit_applications",
                        to="dealer_ai.customerlead",
                    ),
                ),
                (
                    "sale",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="credit_applications",
                        to="dealer_ai.sale",
                    ),
                ),
            ],
            options={
                "verbose_name": "Credit application",
                "verbose_name_plural": "Credit applications",
                "ordering": ("-captured_at", "-created_at"),
            },
        ),
    ]
