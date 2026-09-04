# SESSION_240 (walk finding 28) — TASK_store-timezone.
#
# Every store keeps its own clock. This migration adds one column,
# ``Dealership.timezone`` (IANA name, default "America/Chicago") and
# backfills the Copper Canyon Auto demo dealership to
# "America/Phoenix" so its ledger dates, aging, be-back detection,
# BHPH delinquency day-counts, and every "today" agree with the store
# clock the moment the migration runs.
#
# The default lets existing rows keep rendering exactly as they did
# before (project ``TIME_ZONE = "America/Chicago"``). The backfill is
# targeted at ``slug="copper-canyon-auto"`` only — every other row
# stays on Chicago until an operator edits the field via the
# onboarding page.

from __future__ import annotations

from django.db import migrations, models


def backfill_copper_canyon_zone(apps, schema_editor):
    Dealership = apps.get_model("dealer_ai", "Dealership")
    updated = Dealership.objects.filter(slug="copper-canyon-auto").update(
        timezone="America/Phoenix"
    )
    if updated:
        # Migration output is what an operator sees on ``migrate``;
        # print so the task's "backfilled Copper Canyon" check has a
        # real number rather than an assumption.
        print(
            f"  dealer_ai.0063 timezone backfill: "
            f"{updated} Copper Canyon dealership set to "
            f"America/Phoenix."
        )


def reverse_backfill(apps, schema_editor):
    # Reversible: reset the same slug back to the project default so a
    # ``migrate <name> zero`` round-trips cleanly.
    Dealership = apps.get_model("dealer_ai", "Dealership")
    Dealership.objects.filter(slug="copper-canyon-auto").update(
        timezone="America/Chicago"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0062_store_address_tax_and_fees"),
    ]

    operations = [
        migrations.AddField(
            model_name="dealership",
            name="timezone",
            field=models.CharField(
                default="America/Chicago",
                help_text=(
                    "IANA time zone name (e.g. America/Phoenix). All "
                    "business-day decisions for this store use this "
                    "zone."
                ),
                max_length=64,
            ),
        ),
        migrations.RunPython(
            backfill_copper_canyon_zone, reverse_backfill
        ),
    ]
