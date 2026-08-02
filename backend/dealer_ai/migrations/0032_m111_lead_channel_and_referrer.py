"""Milestone 11 · Increment 1 (SESSION_114) — CustomerLead.channel + referrer.

Additive extension per MILESTONE_11_PLANNING.md §1.1 + §1.6 (§5.a + §5.b
+ §5.f confirmed as-recommended at SESSION_114 open, recorded in §0.a).

The ``channel`` AddField carries ``default="chat"`` — Django backfills
every pre-existing row atomically in the same operation. All pre-M11
CustomerLead rows originated in the chat funnel (M1 was the only intake
path), so ``chat`` is the correct historical default. No separate
RunPython op is required; the field-level default IS the backfill.

The ``referrer`` self-FK captures referral attribution (§1.6). SET_NULL
keeps the referred row intact when the referrer is deleted — referral
incentive payout logic is deferred beyond M11 (§2 non-goals), so soft
nulling is fine.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0031_compliance_record_and_evidence_urls"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerlead",
            name="channel",
            field=models.CharField(
                choices=[
                    ("chat", "Chat"),
                    ("walk_in", "Walk-in"),
                    ("phone", "Phone"),
                    ("listing_form", "Listing form"),
                    ("referral", "Referral"),
                    ("other", "Other"),
                ],
                default="chat",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="customerlead",
            name="referrer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referred_leads",
                to="dealer_ai.customerlead",
            ),
        ),
    ]
