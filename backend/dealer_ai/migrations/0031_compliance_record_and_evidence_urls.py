"""Milestone 10 · Increment 7 (SESSION_112) — ComplianceRecord
entity + additive evidence-URL extensions.

Three operations shipped atomically per
``MILESTONE_10_PLANNING.md`` §1.8 (six §1.8.a-f decisions
confirmed at SESSION_112 open, recorded in §0.a).

**Additive URL extensions per §1.8.c Option C.**

- ``AddField`` — ``Stipulation.evidence_url`` URLField(blank).
- ``AddField`` — ``BackEndProductAgreement.product_agreement_url``
  URLField(blank).

Both fields capture external document references (Google Drive
folder link, DMS document URL, etc.) without upload plumbing.
Full storage infrastructure (Cloudinary/S3, presigned URLs,
MIME validation) is a discrete post-M10 initiative per §1.8.c
Option C.

**New ComplianceRecord entity per §1.8.a Option A + §1.8.b Option A.**

- ``CreateModel`` — :class:`ComplianceRecord`. OneToOne with
  :class:`Contract` CASCADE per §1.8.a — matches FINANCE §6.9
  deal-jacket mental model. Single-entity typed-columns model
  per §1.8.b covering FINANCE §6.1-§6.9 concerns: Reg Z
  (``reg_z_disclosed_at``), OFAC (``ofac_checked_at`` +
  ``ofac_hit``), Red Flags (``red_flags_reviewed_at`` +
  ``red_flags_notes``), Privacy (``privacy_notice_delivered_at``),
  Safeguards (``safeguards_audit_at``), Adverse Action
  (``adverse_action_sent_at`` + ``adverse_action_reason``),
  Retention (``retention_expires_at`` denormalized from parent
  CreditApplication for deal-jacket query-ability),
  ``deal_jacket_url`` (external document reference per §1.8.c).

**Reverse: ``DeleteModel`` + two ``RemoveField``.** Safe at
M10.7 — the URL columns are nullable/blank (reversing loses
M10.7 data but doesn't break the schema); ComplianceRecord
has no other model referencing it.

**Tenancy carrier extension** — ``ComplianceRecord`` added to
:data:`services.tenancy._TENANT_CARRIER_MODEL_NAMES` (33 → 34)
in the same session. The autofill signal is a safety net for
callers that bypass :mod:`services.f_and_i.compliance`.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0030_chargeback_and_bepa_cancellation"),
    ]

    operations = [
        migrations.AddField(
            model_name="backendproductagreement",
            name="product_agreement_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="stipulation",
            name="evidence_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.CreateModel(
            name="ComplianceRecord",
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
                ("reg_z_disclosed_at", models.DateTimeField(blank=True, null=True)),
                ("ofac_checked_at", models.DateTimeField(blank=True, null=True)),
                ("ofac_hit", models.BooleanField(default=False)),
                ("red_flags_reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("red_flags_notes", models.TextField(blank=True, default="")),
                (
                    "privacy_notice_delivered_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("safeguards_audit_at", models.DateTimeField(blank=True, null=True)),
                ("adverse_action_sent_at", models.DateTimeField(blank=True, null=True)),
                ("adverse_action_reason", models.TextField(blank=True, default="")),
                ("retention_expires_at", models.DateTimeField(blank=True, null=True)),
                ("deal_jacket_url", models.URLField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "contract",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="compliance_record",
                        to="dealer_ai.contract",
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="compliance_records",
                        to="dealer_ai.dealership",
                    ),
                ),
            ],
            options={
                "verbose_name": "Compliance record",
                "verbose_name_plural": "Compliance records",
                "ordering": ("-created_at",),
            },
        ),
    ]
