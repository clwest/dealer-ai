# SESSION_241.1 (walk finding 28 — part 3) — a store created tomorrow
# must not silently inherit America/Chicago.
#
# SESSION_240's 0063 shipped ``Dealership.timezone`` with a
# ``default="America/Chicago"`` so existing rows kept rendering exactly
# as they had before. The default did its job for that migration and
# is now the trap: any new store created without an explicit zone
# picks up Chicago from the field default, which is exactly the bug
# SESSION_240 removed.
#
# This migration only alters the field's *default* — from
# ``"America/Chicago"`` to ``""`` (blank). Existing rows are untouched;
# every store already carries a value, and the SESSION_240 backfill
# already set Copper Canyon to America/Phoenix. What changes is the
# column's silent inheritance for freshly-created stores: they now
# arrive blank, and the onboarding save path seeds the zone from the
# store's state via ``suggest_timezone_for_state`` (one-zone states
# resolve outright; multi-zone states like TX/FL keep it blank and the
# operator picks). If a business-day helper is called while the zone
# is blank, ``services.store_time._zone_for`` logs a visible warning
# naming the tenant and falls back to the project ``TIME_ZONE`` — a
# blank column is now visible instead of invisible.

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0063_dealership_timezone"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dealership",
            name="timezone",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "IANA time zone name (e.g. America/Phoenix). All "
                    "business-day decisions for this store use this "
                    "zone. Blank until the operator picks one on "
                    "onboarding — a blank zone falls back to the "
                    "project TIME_ZONE with a visible warning rather "
                    "than silently inheriting Chicago."
                ),
                max_length=64,
            ),
        ),
    ]
