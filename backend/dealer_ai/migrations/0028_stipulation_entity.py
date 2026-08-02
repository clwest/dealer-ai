"""Milestone 10 · Increment 4 (SESSION_109) — Stipulation entity.

One operation shipped atomically per ``MILESTONE_10_PLANNING.md``
§1.4 (all four §1.4.a-d decisions confirmed at SESSION_109 open,
all Option A, recorded in §0.a; the §5.b stipulation-vocabulary
decision was previously confirmed at SESSION_106 open).

**New Stipulation entity.**

- ``CreateModel`` — :class:`Stipulation`. Mandatory FK to
  :class:`LenderSubmission` CASCADE (per §1.4.a Option A — stips
  are lender-specific per FINANCE §1.9). Fields: ``stip_type``
  from fixed 5-value set per §5.b Option A (proof_of_income /
  proof_of_insurance / proof_of_residence / references / other),
  ``state`` from fixed 3-value set per §1.4.b Option A (open
  default / cleared / waived), ``documented_by`` FK to
  ``settings.AUTH_USER_MODEL`` nullable SET_NULL per §1.4.c
  Option A (audit-trail rigor), ``cleared_at`` DateTime nullable
  (auto-populated by the service verb on state transition to
  cleared/waived; reset to NULL on transition back to open),
  ``notes`` TextField blank. Ordering ``(-created_at,)``.

**No photo / document evidence at M10.4** per §1.4.d Option A —
deferred to M10.7 compliance layer. Structured storage plumbing
(Cloudinary/S3 wiring, presigned URLs, MIME validation, retention
discipline) lands with the compliance record.

**Reverse: ``DeleteModel``.** Safe at M10.4 — nothing else
references ``dealer_ai_stipulation``.

**Tenancy carrier extension** — ``Stipulation`` added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (28 → 29)
in the same session. The autofill signal is a safety net for
callers that bypass :mod:`services.f_and_i.stipulation`.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0027_lender_entities"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Stipulation",
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
                    "stip_type",
                    models.CharField(
                        choices=[
                            ("proof_of_income", "Proof of income"),
                            ("proof_of_insurance", "Proof of insurance"),
                            ("proof_of_residence", "Proof of residence"),
                            ("references", "References"),
                            ("other", "Other"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("open", "Open (evidence outstanding)"),
                            ("cleared", "Cleared (evidence provided)"),
                            ("waived", "Waived (lender no longer requires)"),
                        ],
                        default="open",
                        max_length=16,
                    ),
                ),
                ("cleared_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stipulations",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "documented_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stipulations_documented",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lender_submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stipulations",
                        to="dealer_ai.lendersubmission",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stipulation",
                "verbose_name_plural": "Stipulations",
                "ordering": ("-created_at",),
            },
        ),
    ]
