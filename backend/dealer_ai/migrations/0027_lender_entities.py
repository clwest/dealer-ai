"""Milestone 10 · Increment 3 (SESSION_108) — LenderProgram +
LenderSubmission entities.

Three operations shipped atomically per ``MILESTONE_10_PLANNING.md``
§1.3 (all four §1.3.a-d decisions confirmed at SESSION_108 open,
all Option A, recorded in §0.a).

**New LenderProgram entity per §1.3.c Option A.**

- ``CreateModel`` — :class:`LenderProgram`. FK to
  :class:`Dealership` (CASCADE — per-dealership catalog scope
  from §1.3.c). Fields: ``name`` CharField(255), ``contact``
  CharField(255) blank, ``terms_summary`` TextField blank,
  ``is_active`` BooleanField default=True. Ordering ``(name,)``.
- ``AddConstraint`` — unique ``(dealership, name)`` so a
  dealership cannot have two programs with the same name. The
  ``LenderSubmission.on_delete=PROTECT`` on the ``lender_program``
  FK plus the deactivation-via-``is_active`` pattern means
  deactivated programs still occupy the name slot.

**New LenderSubmission entity per §1.3.a + §1.3.b + §1.3.d.**

- ``CreateModel`` — :class:`LenderSubmission`. FK to
  :class:`DealStructure` CASCADE (mandatory — every submission
  is *of* a deal structure per §1.3.a Option A) + FK to
  :class:`LenderProgram` **PROTECT** (submissions are historical
  records; operators deactivate programs rather than delete).
  Fields: ``submitted_at`` DateTime, ``status`` from
  :data:`LENDER_SUBMISSION_STATUS_CHOICES` (fixed 4-value set
  per §1.3.b Option A, default ``pending``), ``counter_terms``
  + ``approval_terms`` JSONField default=dict (free-form per
  §1.3.d Option A), ``notes`` TextField blank. Ordering
  ``(-submitted_at, -created_at)``.

**No indexes at M10.3.** Composite indexes on
``(dealership, -submitted_at)`` and ``(deal_structure,
-submitted_at)`` land at M10.7+ if aggregation surfaces hot paths.

**Reverse: two ``DeleteModel`` operations + one ``RemoveConstraint``.**
Safe at M10.3 — nothing else in the DB references either new
table.

**Tenancy carrier extension** — both entities added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (26 → 28)
in the same session. The autofill signal is a safety net for
callers that bypass the M10.3 service verbs
(:mod:`services.f_and_i.lender`); the service writes
``dealership`` explicitly on every row.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0026_deal_structure_entity"),
    ]

    operations = [
        migrations.CreateModel(
            name="LenderProgram",
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
                ("name", models.CharField(max_length=255)),
                ("contact", models.CharField(blank=True, default="", max_length=255)),
                ("terms_summary", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lender_programs",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lender program",
                "verbose_name_plural": "Lender programs",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="LenderSubmission",
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
                ("submitted_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("counter", "Counter-offer"),
                            ("declined", "Declined"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("counter_terms", models.JSONField(blank=True, default=dict)),
                ("approval_terms", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "deal_structure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lender_submissions",
                        to="dealer_ai.dealstructure",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lender_submissions",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "lender_program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="submissions",
                        to="dealer_ai.lenderprogram",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lender submission",
                "verbose_name_plural": "Lender submissions",
                "ordering": ("-submitted_at", "-created_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="lenderprogram",
            constraint=models.UniqueConstraint(
                fields=("dealership", "name"),
                name="unique_lender_program_name_per_dealership",
            ),
        ),
    ]
