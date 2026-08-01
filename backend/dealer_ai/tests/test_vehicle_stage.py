"""Milestone 5 · Increment 1 (SESSION_075) — VehicleStage persistence tests.

Persistence-layer coverage only. Service-layer semantics (transition
validation, role-authorized advance, bootstrap-on-read via
``ensure_current_stage``) land at M5.2 per
``MILESTONE_5_PLANNING.md`` §7 M5.2 and §0.a item 6.

Locked invariants:

- OneToOne with Vehicle — a second stage on the same vehicle raises
  IntegrityError.
- Twelve canonical stage choices per §5.a Modified Option C.
- Four canonical trigger choices per §5.b.
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean()`` guard walks ``vehicle.dealership``.
- ``entered_by`` provenance is nullable + SET_NULL.
- ``VehicleStage.save()`` creates no ``VehicleStageEvent`` (no
  side effects; event creation is a service-layer concern).
- Reverse accessor ``Vehicle.stage`` returns the OneToOne row.
- ``sold`` is not a shipped stage value (deferred to M9).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    VEHICLE_STAGE_CHOICES,
    VEHICLE_STAGE_COMPANY_USE,
    VEHICLE_STAGE_DETAIL,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_LISTING,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_PHOTOGRAPHY,
    VEHICLE_STAGE_QC,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    VEHICLE_STAGE_TRIGGER_CHOICES,
    VEHICLE_STAGE_TRIGGER_IMPORT,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    VEHICLE_STAGE_WHOLESALE_OUT,
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
    # M5.5 test-only auto-bootstrap seeds a ``frontline`` stage row
    # for every newly saved Vehicle (see ``tests/__init__.py``).
    # M5.1 persistence tests need the pre-bootstrap state, so wipe
    # immediately.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


class VehicleStageChoicesVocabulary(TestCase):
    """Twelve canonical stages per §5.a Modified Option C — ``sold`` NOT
    shipped in M5 (deferred to M9 alongside the ``Sale`` model)."""

    def test_choices_contain_exactly_twelve_canonical_stages(self):
        keys = {key for key, _ in VEHICLE_STAGE_CHOICES}
        self.assertEqual(
            keys,
            {
                VEHICLE_STAGE_INCOMING,
                VEHICLE_STAGE_INSPECTION,
                VEHICLE_STAGE_RECON,
                VEHICLE_STAGE_QC,
                VEHICLE_STAGE_DETAIL,
                VEHICLE_STAGE_PHOTOGRAPHY,
                VEHICLE_STAGE_LISTING,
                VEHICLE_STAGE_FRONTLINE,
                VEHICLE_STAGE_WHOLESALE_OUT,
                VEHICLE_STAGE_HOLD_RESERVED,
                VEHICLE_STAGE_COMPANY_USE,
                VEHICLE_STAGE_OFF_MARKET,
            },
        )
        self.assertEqual(len(VEHICLE_STAGE_CHOICES), 12)

    def test_sold_is_not_a_shipped_stage_value(self):
        """M9 will add ``sold`` alongside the ``Sale`` model; shipping
        a state the service always rejects would be dishonest."""
        keys = {key for key, _ in VEHICLE_STAGE_CHOICES}
        self.assertNotIn("sold", keys)

    def test_hold_reserved_used_consistently_not_hold(self):
        """§0.a item 1 — use ``hold_reserved`` everywhere; do not
        alternate with the shorter ``hold``."""
        keys = {key for key, _ in VEHICLE_STAGE_CHOICES}
        self.assertIn(VEHICLE_STAGE_HOLD_RESERVED, keys)
        self.assertNotIn("hold", keys)

    def test_company_use_is_distinct_from_off_market(self):
        """§0.a item 1 — ``company_use`` is a real inventory
        disposition per INVENTORY §6.5; not equivalent to ``off_market``."""
        keys = {key for key, _ in VEHICLE_STAGE_CHOICES}
        self.assertIn(VEHICLE_STAGE_COMPANY_USE, keys)
        self.assertIn(VEHICLE_STAGE_OFF_MARKET, keys)
        self.assertNotEqual(VEHICLE_STAGE_COMPANY_USE, VEHICLE_STAGE_OFF_MARKET)

    def test_detail_kept_distinct_from_qc(self):
        """§5.a — detail is its own workflow step in v1."""
        keys = {key for key, _ in VEHICLE_STAGE_CHOICES}
        self.assertIn(VEHICLE_STAGE_DETAIL, keys)
        self.assertIn(VEHICLE_STAGE_QC, keys)


class VehicleStageTriggerVocabulary(TestCase):
    """Four canonical triggers per §5.b."""

    def test_choices_contain_exactly_four_canonical_triggers(self):
        keys = {key for key, _ in VEHICLE_STAGE_TRIGGER_CHOICES}
        self.assertEqual(
            keys,
            {
                VEHICLE_STAGE_TRIGGER_MANUAL,
                VEHICLE_STAGE_TRIGGER_RULE,
                VEHICLE_STAGE_TRIGGER_IMPORT,
                VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
            },
        )
        self.assertEqual(len(VEHICLE_STAGE_TRIGGER_CHOICES), 4)


class VehicleStageCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M51VS-CREATE", self.default)

    def test_round_trip_all_fields(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="stage_actor", password="pw12345678"
        )
        now = timezone.now()
        stage = VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=now,
            entered_by=actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            last_transition_note="Cleared for retail.",
        )
        fetched = VehicleStage.objects.get(pk=stage.pk)
        self.assertEqual(fetched.vehicle_id, self.vehicle.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.current_stage, VEHICLE_STAGE_FRONTLINE)
        self.assertEqual(fetched.entered_at, now)
        self.assertEqual(fetched.entered_by_id, actor.pk)
        self.assertEqual(fetched.trigger, VEHICLE_STAGE_TRIGGER_MANUAL)
        self.assertEqual(fetched.last_transition_note, "Cleared for retail.")

    def test_stage_full_clean_rejects_invalid_choice(self):
        stage = VehicleStage(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage="sold",  # deferred to M9
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        with self.assertRaises(ValidationError):
            stage.full_clean()

    def test_trigger_full_clean_rejects_invalid_choice(self):
        stage = VehicleStage(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_INCOMING,
            entered_at=timezone.now(),
            trigger="auto",  # not a shipped trigger
        )
        with self.assertRaises(ValidationError):
            stage.full_clean()

    def test_last_transition_note_optional(self):
        stage = VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(stage.last_transition_note, "")

    def test_entered_by_nullable_and_set_null_on_user_delete(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="stage_actor_delete", password="pw12345678"
        )
        stage = VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_RECON,
            entered_at=timezone.now(),
            entered_by=actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        actor.delete()
        stage.refresh_from_db()
        self.assertIsNone(stage.entered_by_id)


class VehicleStageOneToOneEnforcement(TestCase):
    """OneToOne means at most one stage per vehicle — the second write
    raises IntegrityError, not silently overwrites."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M51VS-1TO1", self.default)

    def test_second_stage_on_same_vehicle_raises(self):
        VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_INCOMING,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VehicleStage.objects.create(
                    vehicle=self.vehicle,
                    dealership=self.default,
                    current_stage=VEHICLE_STAGE_INSPECTION,
                    entered_at=timezone.now(),
                    trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
                )

    def test_reverse_accessor_returns_the_stage_row(self):
        stage = VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_RECON,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        # OneToOne reverse — ``vehicle.stage`` is the row instance.
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.stage.pk, stage.pk)


class VehicleStageDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            VehicleStage._meta.get_field("dealership").null,
            "VehicleStage.dealership should be NOT NULL from day one",
        )


class VehicleStageCrossTenantClean(TestCase):
    """``dealership`` must match the vehicle's tenant. Same shape as
    ``WorkOrder.clean`` and ``ReconDecision.clean``."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-vs"
        )
        self.vehicle_at_a = _make_vehicle("M51VS-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        stage = VehicleStage(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        stage.full_clean()  # should not raise

    def test_mismatched_dealership_raises_validation_error(self):
        stage = VehicleStage(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        with self.assertRaises(ValidationError) as ctx:
            stage.full_clean()
        self.assertIn("dealership", ctx.exception.error_dict)


class VehicleStageCascadeOnVehicleDelete(TestCase):
    def test_stage_row_removed_when_vehicle_deleted(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VS-CASCADE", default)
        stage = VehicleStage.objects.create(
            vehicle=vehicle,
            dealership=default,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        stage_pk = stage.pk
        vehicle.delete()
        self.assertFalse(VehicleStage.objects.filter(pk=stage_pk).exists())


class VehicleStageNoSideEffectsOnSave(TestCase):
    """``VehicleStage.save()`` MUST NOT create a ``VehicleStageEvent`` —
    event creation is an explicit service-layer concern (§0.a item 6)."""

    def test_creating_stage_creates_no_stage_event(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VS-NOSIDE", default)
        # Sanity: no events exist for this vehicle before or after.
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=vehicle).count(), 0
        )
        VehicleStage.objects.create(
            vehicle=vehicle,
            dealership=default,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=vehicle).count(),
            0,
            "VehicleStage.save() must not auto-create a VehicleStageEvent",
        )

    def test_updating_stage_creates_no_stage_event(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VS-UPDATE", default)
        stage = VehicleStage.objects.create(
            vehicle=vehicle,
            dealership=default,
            current_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        stage.current_stage = VEHICLE_STAGE_RECON
        stage.save()
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=vehicle).count(),
            0,
            "Updating VehicleStage.current_stage must not auto-create "
            "a VehicleStageEvent — that is M5.2 advance_stage() work",
        )


class VehicleStageOrderingAndStr(TestCase):
    """Deterministic ordering by ``-updated_at`` + human-readable str."""

    def test_ordering_is_updated_at_descending(self):
        self.assertEqual(VehicleStage._meta.ordering, ("-updated_at",))

    def test_str_contains_stage_display_and_stock_number(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51VS-STR", default)
        stage = VehicleStage.objects.create(
            vehicle=vehicle,
            dealership=default,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        s = str(stage)
        self.assertIn("Frontline", s)
        self.assertIn("M51VS-STR", s)
