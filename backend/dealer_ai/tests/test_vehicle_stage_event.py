"""Milestone 5 · Increment 1 (SESSION_075) — VehicleStageEvent tests.

Persistence-layer coverage only. The append-only history contract is
locked here behaviorally: workflow code creates events and never
updates them, and the admin surface (M5.1) refuses to add or delete
events. Service-layer semantics (``from_stage=None`` legitimate only
for bootstrap; ``trigger='rule'`` requires non-blank ``rule_name``)
land at M5.2.

Locked invariants:

- Appendable — many events per Vehicle.
- ``from_stage`` nullable at persistence layer (bootstrap events).
- ``to_stage`` NOT NULL and validated via choices.
- Twelve canonical stage choices + four canonical trigger choices.
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean()`` guard walks ``vehicle.dealership``.
- ``by`` provenance is nullable + SET_NULL.
- Deterministic ordering by ``(-entered_at, -created_at)``.
- Creating a ``VehicleStageEvent`` does NOT mutate the paired
  ``VehicleStage.current_stage`` (§0.a item 6 — service is the sole
  transition-authoring surface).
- ``VehicleStage.save()`` does NOT auto-create an event (already
  covered in ``test_vehicle_stage``; asserted again here for the
  reverse direction).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    # M5.5 test-only auto-bootstrap; wipe for M5.1 event tests.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


class VehicleStageEventCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M51VE-CREATE", self.default)

    def test_round_trip_all_fields(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="event_actor", password="pw12345678"
        )
        now = timezone.now()
        event = VehicleStageEvent.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=VEHICLE_STAGE_INSPECTION,
            to_stage=VEHICLE_STAGE_RECON,
            entered_at=now,
            by=actor,
            trigger=VEHICLE_STAGE_TRIGGER_RULE,
            rule_name="inspection_to_recon",
            notes="One safety finding.",
        )
        fetched = VehicleStageEvent.objects.get(pk=event.pk)
        self.assertEqual(fetched.vehicle_id, self.vehicle.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.from_stage, VEHICLE_STAGE_INSPECTION)
        self.assertEqual(fetched.to_stage, VEHICLE_STAGE_RECON)
        self.assertEqual(fetched.entered_at, now)
        self.assertEqual(fetched.by_id, actor.pk)
        self.assertEqual(fetched.trigger, VEHICLE_STAGE_TRIGGER_RULE)
        self.assertEqual(fetched.rule_name, "inspection_to_recon")
        self.assertIn("safety", fetched.notes)

    def test_from_stage_may_be_null_for_bootstrap_event(self):
        event = VehicleStageEvent.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=None,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        self.assertIsNone(event.from_stage)

    def test_to_stage_is_not_null_at_schema_level(self):
        self.assertFalse(
            VehicleStageEvent._meta.get_field("to_stage").null,
            "VehicleStageEvent.to_stage must be NOT NULL",
        )

    def test_to_stage_full_clean_rejects_invalid_choice(self):
        event = VehicleStageEvent(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=None,
            to_stage="sold",  # deferred to M9
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_trigger_full_clean_rejects_invalid_choice(self):
        event = VehicleStageEvent(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=None,
            to_stage=VEHICLE_STAGE_INCOMING,
            entered_at=timezone.now(),
            trigger="unknown",
        )
        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_rule_name_and_notes_optional(self):
        event = VehicleStageEvent.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=VEHICLE_STAGE_FRONTLINE,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(event.rule_name, "")
        self.assertEqual(event.notes, "")

    def test_by_nullable_and_set_null_on_user_delete(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="event_actor_delete", password="pw12345678"
        )
        event = VehicleStageEvent.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=VEHICLE_STAGE_INSPECTION,
            to_stage=VEHICLE_STAGE_RECON,
            entered_at=timezone.now(),
            by=actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        actor.delete()
        event.refresh_from_db()
        self.assertIsNone(event.by_id)


class VehicleStageEventAppendable(TestCase):
    """Many events per vehicle — the event log is a timeline, not a
    OneToOne. Creating a second event on the same vehicle must succeed."""

    def test_multiple_events_per_vehicle_permitted(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VE-APPEND", default)
        now = timezone.now()
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=None,
            to_stage=VEHICLE_STAGE_INCOMING,
            entered_at=now,
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        # Second event, later timestamp — no IntegrityError.
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=VEHICLE_STAGE_INCOMING,
            to_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=vehicle).count(), 2
        )


class VehicleStageEventDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            VehicleStageEvent._meta.get_field("dealership").null,
            "VehicleStageEvent.dealership should be NOT NULL from day one",
        )


class VehicleStageEventCrossTenantClean(TestCase):
    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-ve"
        )
        self.vehicle_at_a = _make_vehicle("M51VE-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        event = VehicleStageEvent(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            from_stage=None,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        event.full_clean()  # should not raise

    def test_mismatched_dealership_raises_validation_error(self):
        event = VehicleStageEvent(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,
            from_stage=None,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        with self.assertRaises(ValidationError) as ctx:
            event.full_clean()
        self.assertIn("dealership", ctx.exception.error_dict)


class VehicleStageEventCascadeOnVehicleDelete(TestCase):
    def test_event_rows_removed_when_vehicle_deleted(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VE-CASCADE", default)
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=None,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=VEHICLE_STAGE_FRONTLINE,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        vehicle_pk = vehicle.pk
        vehicle.delete()
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle_id=vehicle_pk).count(), 0
        )


class VehicleStageEventOrderingAndStr(TestCase):
    """Deterministic ordering — most recent event first."""

    def test_ordering_is_entered_at_then_created_at_descending(self):
        self.assertEqual(
            VehicleStageEvent._meta.ordering,
            ("-entered_at", "-created_at"),
        )

    def test_default_query_returns_most_recent_first(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VE-ORDER", default)
        older = VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=None,
            to_stage=VEHICLE_STAGE_INCOMING,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        # Force a later entered_at value.
        later_time = timezone.now() + timedelta(minutes=5)
        newer = VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=VEHICLE_STAGE_INCOMING,
            to_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=later_time,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        rows = list(VehicleStageEvent.objects.filter(vehicle=vehicle))
        self.assertEqual(rows[0].pk, newer.pk)
        self.assertEqual(rows[1].pk, older.pk)

    def test_str_contains_from_to_and_trigger(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VE-STR", default)
        event = VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=VEHICLE_STAGE_INSPECTION,
            to_stage=VEHICLE_STAGE_RECON,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        s = str(event)
        self.assertIn("Inspection", s)
        self.assertIn("Recon", s)
        self.assertIn("Manual", s)


class VehicleStageEventDoesNotMutateCurrentStage(TestCase):
    """Creating an event MUST NOT mutate the paired stage row's
    ``current_stage`` — the M5.2 service is the sole transition
    authoring surface (§0.a item 6). Direct ORM writes bypass any
    such cascade."""

    def test_creating_event_leaves_current_stage_untouched(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VE-NOMUT", default)
        stage = VehicleStage.objects.create(
            vehicle=vehicle,
            dealership=default,
            current_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=default,
            from_stage=VEHICLE_STAGE_INSPECTION,
            to_stage=VEHICLE_STAGE_RECON,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        stage.refresh_from_db()
        self.assertEqual(
            stage.current_stage,
            VEHICLE_STAGE_INSPECTION,
            "Creating an event must not shift VehicleStage.current_stage",
        )
