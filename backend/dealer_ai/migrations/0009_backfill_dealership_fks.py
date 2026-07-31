"""Milestone 1 · Increment 2 — data migration.

Creates the deterministic default Dealership row and backfills the
nullable ``dealership`` FK on every existing row of the six tenant-
carrying models introduced in 0008. Idempotent: safe to re-run against
a partially-migrated DB.

Resolution order for the default Dealership's *name* (matches
``docs/roadmap/MILESTONE_1_PLANNING.md`` §1.5):

1. ``settings.DEALER_AI_DEALER_NAME`` — env override.
2. ``DealerOnboardingProfile.dealership_name`` (first non-empty) — the
   singleton persisted via the Setup UI.
3. ``"Default Dealership"`` — bland but recognizable fallback.

The *slug* is always ``"default"`` regardless of the resolved name.
This keeps the row stable across renames and lets subsequent code
(and the reverse migration) look it up by a known key.

Post-backfill the migration counts nulls per table and raises if any
remain — the whole migration then rolls back inside its transaction,
which is exactly what we want if the backfill failed to cover a row.
"""

from django.conf import settings
from django.db import migrations

_DEFAULT_SLUG = "default"
_DEFAULT_NAME_FALLBACK = "Default Dealership"

# Models that gained a nullable `dealership` FK in migration 0008.
# Kept as (app_label, model_name) tuples so the historical model lookup
# in `apps.get_model()` never depends on the live model registry.
_TENANT_CARRIERS = (
    ("dealer_ai", "Vehicle"),
    ("dealer_ai", "Salesperson"),
    ("dealer_ai", "ChatSession"),
    ("dealer_ai", "ChatMessage"),
    ("dealer_ai", "CustomerLead"),
    ("dealer_ai", "DealerOnboardingProfile"),
)


def _resolve_default_name(apps):
    env_name = (getattr(settings, "DEALER_AI_DEALER_NAME", "") or "").strip()
    if env_name:
        return env_name
    DealerOnboardingProfile = apps.get_model("dealer_ai", "DealerOnboardingProfile")
    profile = (
        DealerOnboardingProfile.objects.exclude(dealership_name="")
        .order_by("pk")
        .first()
    )
    if profile and profile.dealership_name.strip():
        return profile.dealership_name.strip()
    return _DEFAULT_NAME_FALLBACK


def backfill_default_dealership(apps, schema_editor):
    Dealership = apps.get_model("dealer_ai", "Dealership")

    resolved_name = _resolve_default_name(apps)
    default, _created = Dealership.objects.get_or_create(
        slug=_DEFAULT_SLUG,
        defaults={"name": resolved_name},
    )

    for app_label, model_name in _TENANT_CARRIERS:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(dealership__isnull=True).update(dealership=default)

    # Post-backfill count verification. Raising inside a data migration
    # rolls the whole thing back (including the row creation above),
    # per Django's transactional-migration guarantee on backends that
    # support DDL transactions.
    for app_label, model_name in _TENANT_CARRIERS:
        Model = apps.get_model(app_label, model_name)
        residual = Model.objects.filter(dealership__isnull=True).count()
        if residual:
            raise RuntimeError(
                f"Backfill left {residual} row(s) of "
                f"{app_label}.{model_name} without a dealership FK."
            )


def unbackfill(apps, schema_editor):
    """Reverse: null-out backfilled rows and drop the default Dealership.

    Only safe because the FKs revert to nullable via 0010's reverse and
    then get dropped entirely via 0008's reverse. We NULL every row that
    points at the default slug and delete the default row. Rows that
    reference some other Dealership (created after this migration) are
    left untouched.
    """
    Dealership = apps.get_model("dealer_ai", "Dealership")
    default = Dealership.objects.filter(slug=_DEFAULT_SLUG).first()
    if default is None:
        return
    for app_label, model_name in _TENANT_CARRIERS:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(dealership=default).update(dealership=None)
    default.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0008_add_dealership_fks"),
    ]

    operations = [
        migrations.RunPython(backfill_default_dealership, unbackfill),
    ]
