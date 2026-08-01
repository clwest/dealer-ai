"""Milestone 5 · Increment 1 (SESSION_075) — Vehicle lifecycle persistence.

Creates two new models — :class:`dealer_ai.models.VehicleStage` and
:class:`dealer_ai.models.VehicleStageEvent` — and bootstraps a matching
pair of rows (one stage + one event) for every existing
:class:`dealer_ai.models.Vehicle` per ``MILESTONE_5_PLANNING.md`` §5.c
Option C (SESSION_075 refinement — both stage AND event, not just the
stage row).

Bootstrap rules:

- ``Vehicle.is_available=True``  → ``current_stage='frontline'``
- ``Vehicle.is_available=False`` → ``current_stage='off_market'``
- ``VehicleStageEvent`` mirrors the stage row: ``to_stage`` matches
  ``current_stage``, ``from_stage=None`` (legitimate ONLY for bootstrap
  events per M5.2 service invariant), ``entered_at`` **the same instant**
  as the stage row's ``entered_at`` (single ``timezone.now()`` value per
  vehicle for enforceability in tests), ``trigger='bootstrap'``,
  ``by=None``, ``notes=''``.
- ``dealership`` on both rows is threaded explicitly from the parent
  ``Vehicle.dealership`` (not the pre_save autofill safety net — the
  migration is authoritative about tenancy at bootstrap).

Idempotency:

- If a Vehicle already has a ``VehicleStage`` row, the migration skips
  both the stage and event insert for that vehicle (a partially-
  applied migration re-runs safely).
- On an empty database (no Vehicles) the migration is a no-op past
  the CreateModel operations.

Reverse:

- The ``migrations.RunPython`` reverse deletes every ``VehicleStage``
  and ``VehicleStageEvent`` created by this migration. The
  ``CreateModel`` operations drop the tables entirely, so the reverse
  is idempotent whether or not the RunPython reverse ran first. Do
  NOT alter ``Vehicle.is_available`` on reverse.
- ``Vehicle.is_available`` is untouched in both directions.

Post-bootstrap invariants (verified in the M5.1 test suite):

1. Every existing Vehicle has exactly one ``VehicleStage`` row.
2. Every existing Vehicle has exactly one ``VehicleStageEvent`` row
   whose ``trigger='bootstrap'``.
3. Every event row's ``to_stage`` matches the paired stage row's
   ``current_stage``.
4. Every event row's ``from_stage`` is NULL.
5. Every event row's ``entered_at`` equals its paired stage row's
   ``entered_at``.
6. Every event row's ``dealership`` matches its paired vehicle's
   ``dealership``.
7. ``Vehicle.is_available`` values and schema are unchanged.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def bootstrap_vehicle_stages(apps, schema_editor):
    """Insert (VehicleStage, VehicleStageEvent) for every existing Vehicle.

    Idempotent — skips vehicles that already have a stage row so a
    partially-applied migration re-runs safely.
    """
    Vehicle = apps.get_model("dealer_ai", "Vehicle")
    VehicleStage = apps.get_model("dealer_ai", "VehicleStage")
    VehicleStageEvent = apps.get_model("dealer_ai", "VehicleStageEvent")

    for vehicle in Vehicle.objects.all().iterator():
        # Skip if this vehicle already has a stage row (partial re-run).
        if VehicleStage.objects.filter(vehicle=vehicle).exists():
            continue

        stage_value = (
            "frontline" if vehicle.is_available else "off_market"
        )
        # Single timezone.now() value shared by both rows so the "event's
        # entered_at equals stage's entered_at" invariant is enforceable in
        # tests (a second .now() call would drift by microseconds).
        entered_at = timezone.now()

        VehicleStage.objects.create(
            vehicle=vehicle,
            dealership=vehicle.dealership,
            current_stage=stage_value,
            entered_at=entered_at,
            entered_by=None,
            trigger="bootstrap",
            last_transition_note="",
        )
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=vehicle.dealership,
            from_stage=None,
            to_stage=stage_value,
            entered_at=entered_at,
            by=None,
            trigger="bootstrap",
            rule_name="",
            notes="",
        )


def unbootstrap_vehicle_stages(apps, schema_editor):
    """Reverse: delete every stage + event row this migration created.

    The subsequent ``CreateModel`` reverse drops the tables entirely, so
    strictly speaking this RunPython reverse is only useful if the
    reverse is stepped one at a time. Do NOT touch ``Vehicle.is_available``.
    """
    VehicleStage = apps.get_model("dealer_ai", "VehicleStage")
    VehicleStageEvent = apps.get_model("dealer_ai", "VehicleStageEvent")

    # Delete events first — they FK to Vehicle (CASCADE) and are the
    # audit trail; deleting stage rows first would also work because
    # the events reference Vehicle, not the stage row.
    VehicleStageEvent.objects.filter(trigger="bootstrap").delete()
    VehicleStage.objects.filter(trigger="bootstrap").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0016_recon_persistence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleStage",
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
                    "current_stage",
                    models.CharField(
                        choices=[
                            ("incoming", "Incoming"),
                            ("inspection", "Inspection"),
                            ("recon", "Recon"),
                            ("qc", "QC"),
                            ("detail", "Detail"),
                            ("photography", "Photography"),
                            ("listing", "Listing"),
                            ("frontline", "Frontline"),
                            ("wholesale_out", "Wholesale out"),
                            ("hold_reserved", "Hold / reserved"),
                            ("company_use", "Company use"),
                            ("off_market", "Off market"),
                        ],
                        max_length=32,
                    ),
                ),
                ("entered_at", models.DateTimeField()),
                (
                    "trigger",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("rule", "Rule"),
                            ("import", "Import"),
                            ("bootstrap", "Bootstrap"),
                        ],
                        max_length=16,
                    ),
                ),
                ("last_transition_note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vehicle_stages",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "entered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "vehicle",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stage",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vehicle stage",
                "verbose_name_plural": "Vehicle stages",
                "ordering": ("-updated_at",),
            },
        ),
        migrations.CreateModel(
            name="VehicleStageEvent",
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
                    "from_stage",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("incoming", "Incoming"),
                            ("inspection", "Inspection"),
                            ("recon", "Recon"),
                            ("qc", "QC"),
                            ("detail", "Detail"),
                            ("photography", "Photography"),
                            ("listing", "Listing"),
                            ("frontline", "Frontline"),
                            ("wholesale_out", "Wholesale out"),
                            ("hold_reserved", "Hold / reserved"),
                            ("company_use", "Company use"),
                            ("off_market", "Off market"),
                        ],
                        max_length=32,
                        null=True,
                    ),
                ),
                (
                    "to_stage",
                    models.CharField(
                        choices=[
                            ("incoming", "Incoming"),
                            ("inspection", "Inspection"),
                            ("recon", "Recon"),
                            ("qc", "QC"),
                            ("detail", "Detail"),
                            ("photography", "Photography"),
                            ("listing", "Listing"),
                            ("frontline", "Frontline"),
                            ("wholesale_out", "Wholesale out"),
                            ("hold_reserved", "Hold / reserved"),
                            ("company_use", "Company use"),
                            ("off_market", "Off market"),
                        ],
                        max_length=32,
                    ),
                ),
                ("entered_at", models.DateTimeField()),
                (
                    "trigger",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("rule", "Rule"),
                            ("import", "Import"),
                            ("bootstrap", "Bootstrap"),
                        ],
                        max_length=16,
                    ),
                ),
                ("rule_name", models.CharField(blank=True, default="", max_length=128)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vehicle_stage_events",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stage_events",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vehicle stage event",
                "verbose_name_plural": "Vehicle stage events",
                "ordering": ("-entered_at", "-created_at"),
            },
        ),
        migrations.RunPython(
            bootstrap_vehicle_stages,
            unbootstrap_vehicle_stages,
        ),
    ]
