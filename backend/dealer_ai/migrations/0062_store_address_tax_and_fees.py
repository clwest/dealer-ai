# SESSION_239 (finding 49, second half) — TASK_tax-fees-and-store-address.
#
# One migration adds the four address parts (street/city/state/postal),
# plus the store's own sales-tax rate and doc/admin fee. All six are
# additive and nullable/blank so historical rows keep rendering
# through the payment_engine module constants.
#
# The RunPython step best-effort backfills the four address parts
# from the existing free-text ``store_location`` (e.g.
# ``"1420 Frontage Rd, Yuma, AZ 85364"``) and prints how many
# profiles parsed cleanly vs. how many were left blank so the
# operator can see the number rather than assume they all parsed.
# The parse is intentionally conservative — anything ambiguous is
# left blank, matching the "no silent rewrite" line in the task.

from __future__ import annotations

import re

from django.db import migrations, models


_ADDRESS_TAIL_RE = re.compile(
    r"^\s*(?P<state>[A-Za-z]{2})\s+(?P<postal>\d{5}(?:-\d{4})?)\s*$"
)
_US_STATE_CODES = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
        "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
        "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
        "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
        "WY",
    }
)


def _parse_store_location(raw: str) -> dict:
    """Best-effort parse of ``"street, city, ST postal"`` shape.

    Returns a dict with any of ``street_address``, ``city``, ``state``,
    ``postal_code`` that we could recover; missing keys are left out so
    the caller can distinguish "parsed nothing" from "parsed part".
    Never raises — the point is to preserve what we can, not to fight
    with legacy data.
    """
    if not raw:
        return {}
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) < 2:
        return {}
    tail = parts[-1]
    match = _ADDRESS_TAIL_RE.match(tail)
    if not match:
        return {}
    state = match.group("state").upper()
    if state not in _US_STATE_CODES:
        return {}
    postal = match.group("postal")
    parsed: dict = {"state": state, "postal_code": postal}
    if len(parts) >= 2:
        parsed["city"] = parts[-2]
    if len(parts) >= 3:
        parsed["street_address"] = ", ".join(parts[:-2])
    return parsed


def backfill_address_parts(apps, schema_editor):
    Profile = apps.get_model("dealer_ai", "DealerOnboardingProfile")
    parsed_full = 0
    parsed_partial = 0
    unparsed = 0
    total = 0
    for profile in Profile.objects.all():
        total += 1
        parsed = _parse_store_location(profile.store_location or "")
        if not parsed:
            unparsed += 1
            continue
        for key, value in parsed.items():
            setattr(profile, key, value)
        # ``street_address`` is the only optional part of a full parse
        # (a city-only ``"Yuma, AZ 85364"`` still gets state/postal/city
        # but no street). Distinguish full vs. partial for the report.
        keys = {"street_address", "city", "state", "postal_code"}
        if keys.issubset(parsed.keys()):
            parsed_full += 1
        else:
            parsed_partial += 1
        profile.save(
            update_fields=[
                "street_address", "city", "state", "postal_code",
            ]
        )
    if total:
        # Migration output is what an operator sees on ``migrate``;
        # print so the task's "how many parsed" check has a real
        # number rather than an assumption.
        print(
            f"  dealer_ai.0062 store_location backfill: "
            f"{parsed_full} full, {parsed_partial} partial, "
            f"{unparsed} unparsed (of {total} profiles)."
        )


def reverse_backfill(apps, schema_editor):
    # Reversible only in the "clear the four parts" sense; the free-text
    # ``store_location`` was never rewritten so unwind is a no-op on
    # that side. Left as an empty callable so `migrate <name> zero`
    # still round-trips cleanly.
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0061_front_door_payment_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="street_address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="city",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="state",
            field=models.CharField(
                blank=True,
                choices=[
                    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"),
                    ("AR", "Arkansas"), ("CA", "California"),
                    ("CO", "Colorado"), ("CT", "Connecticut"),
                    ("DE", "Delaware"),
                    ("DC", "District of Columbia"),
                    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"),
                    ("ID", "Idaho"), ("IL", "Illinois"), ("IN", "Indiana"),
                    ("IA", "Iowa"), ("KS", "Kansas"), ("KY", "Kentucky"),
                    ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
                    ("MA", "Massachusetts"), ("MI", "Michigan"),
                    ("MN", "Minnesota"),
                    ("MS", "Mississippi"), ("MO", "Missouri"),
                    ("MT", "Montana"),
                    ("NE", "Nebraska"), ("NV", "Nevada"),
                    ("NH", "New Hampshire"),
                    ("NJ", "New Jersey"), ("NM", "New Mexico"),
                    ("NY", "New York"),
                    ("NC", "North Carolina"), ("ND", "North Dakota"),
                    ("OH", "Ohio"),
                    ("OK", "Oklahoma"), ("OR", "Oregon"),
                    ("PA", "Pennsylvania"),
                    ("RI", "Rhode Island"), ("SC", "South Carolina"),
                    ("SD", "South Dakota"),
                    ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
                    ("VT", "Vermont"), ("VA", "Virginia"),
                    ("WA", "Washington"),
                    ("WV", "West Virginia"), ("WI", "Wisconsin"),
                    ("WY", "Wyoming"),
                ],
                default="",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="postal_code",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="sales_tax_rate_pct",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=5, null=True
            ),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="doc_fees",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True
            ),
        ),
        migrations.RunPython(backfill_address_parts, reverse_backfill),
    ]
