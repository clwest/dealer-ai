"""Milestone 6 · Increment 4 (SESSION_085) — M6.4 rule integration tests.

Coverage of the two rules M6.4 ships:

- **`_rule_photography_to_listing` (filled)** — real photo-count
  predicate replacing the M5.3 stub. Active when
  ``listing_ready_count >= LISTING_READY_PHOTO_COUNT`` (8 per
  SESSION_082 confirmation). Structured unmet-prereq otherwise.
- **`_rule_listing_to_frontline` (new)** — active when
  ``VehicleListing.status == 'published' AND Vehicle.price > 0``.
  Structured unmet-prereq per failing condition otherwise.

Plus the ``suggest_transitions`` composition dispatch extension
(``listing`` stage now dispatches to the new rule).

M5.3 rule coverage lives in ``test_vehicle_lifecycle_rules.py``;
those tests were updated in-place at SESSION_085 to reflect the
M6.4 predicates (three tests: prerequisite mentions photo count
not "M6", listing stage composes new rule, price-only guard).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    VEHICLE_LISTING_STATUS_APPROVED,
    VEHICLE_LISTING_STATUS_DRAFT,
    VEHICLE_LISTING_STATUS_PUBLISHED,
    VEHICLE_LISTING_STATUS_UNPUBLISHED,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_LISTING,
    VEHICLE_STAGE_PHOTOGRAPHY,
    Vehicle,
    VehicleListing,
)
from dealer_ai.services import photo_gallery
from dealer_ai.services.vehicle_lifecycle import (
    CrossTenantLifecycleError,
    SuggestedTransition,
    _rule_listing_to_frontline,
    _rule_photography_to_listing,
    ensure_current_stage,
    suggest_transitions,
)


_SAMPLE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg"


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("29500.00"),
        dealership=dealership,
    )
    # M5.5 test-only auto-bootstrap seeds a frontline stage row on
    # every Vehicle save. Wipe so M6.4 rule tests observe the
    # specific stage state each test seeds via ensure_current_stage.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


def _upload_listing_ready_photos(
    vehicle: Vehicle, dealership: Dealership, *, count: int
) -> None:
    for _ in range(count):
        photo_gallery.upload_photo(
            vehicle,
            dealership=dealership,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1920,
            height_px=1080,
        )


def _publish_listing(
    vehicle: Vehicle, dealership: Dealership
) -> VehicleListing:
    """Directly persist a published listing without walking the M6.3
    draft/approve/publish ladder — this test file exercises the M6.4
    rule predicates, not the M6.3 workflow.
    """
    now = timezone.now()
    return VehicleListing.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        status=VEHICLE_LISTING_STATUS_PUBLISHED,
        body="Nice vehicle.",
        drafted_at=now,
        approved_at=now,
        published_at=now,
    )


# ============================================================================
# _rule_photography_to_listing — active path
# ============================================================================


class RulePhotographyToListingActive(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M64-PL-ACTIVE", self.default)

    def test_fires_at_exactly_threshold(self):
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT,
        )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.unmet_prerequisites, ())

    def test_fires_above_threshold(self):
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT + 3,
        )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.unmet_prerequisites, ())

    def test_active_target_and_rule_name(self):
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT,
        )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.to_stage, VEHICLE_STAGE_LISTING)
        self.assertEqual(result.rule_name, "photography_to_listing")

    def test_active_evidence_names_count_and_threshold(self):
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT + 1,
        )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertIn(
            str(photo_gallery.LISTING_READY_PHOTO_COUNT + 1), result.evidence
        )
        self.assertIn(
            str(photo_gallery.LISTING_READY_PHOTO_COUNT), result.evidence
        )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-pl-active")
        with self.assertRaises(CrossTenantLifecycleError):
            _rule_photography_to_listing(self.vehicle, dealership=other)


# ============================================================================
# _rule_photography_to_listing — unmet path
# ============================================================================


class RulePhotographyToListingUnmet(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M64-PL-UNMET", self.default)

    def test_zero_photos_returns_unmet(self):
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)

    def test_below_threshold_returns_unmet(self):
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT - 1,
        )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)
        joined = " ".join(result.unmet_prerequisites)
        # "Need 1 more listing-ready photo(s)"
        self.assertIn("Need 1 more", joined)

    def test_low_res_photos_dont_count(self):
        # Upload count-threshold worth of low-res photos (below the
        # SESSION_083 §3 1024x768 dimension threshold). The predicate
        # excludes them → still unmet.
        for _ in range(photo_gallery.LISTING_READY_PHOTO_COUNT):
            photo_gallery.upload_photo(
                self.vehicle,
                dealership=self.default,
                data=_SAMPLE_BYTES,
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                width_px=800,
                height_px=600,
            )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)

    def test_marked_deleted_photos_dont_count(self):
        # Upload threshold + 1 listing-ready photos, then mark one deleted.
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT + 1,
        )
        first_photo = self.vehicle.photos.first()
        photo_gallery.mark_deleted(first_photo, dealership=self.default)
        # Should still be at threshold — active suggestion.
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.unmet_prerequisites, ())
        # Now mark two more deleted — below threshold → unmet.
        for photo in self.vehicle.photos.filter(
            marked_deleted_at__isnull=True
        )[:2]:
            photo_gallery.mark_deleted(photo, dealership=self.default)
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)

    def test_unmet_evidence_names_specific_shortfall(self):
        _upload_listing_ready_photos(
            self.vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT - 3,
        )
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        joined = " ".join(result.unmet_prerequisites)
        # "Need 3 more listing-ready photo(s)"
        self.assertIn("Need 3 more", joined)


# ============================================================================
# _rule_listing_to_frontline — active path
# ============================================================================


class RuleListingToFrontlineActive(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M64-LF-ACTIVE", self.default)
        _publish_listing(self.vehicle, self.default)

    def test_fires_when_published_and_price_positive(self):
        result = _rule_listing_to_frontline(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.unmet_prerequisites, ())
        self.assertEqual(result.to_stage, VEHICLE_STAGE_FRONTLINE)
        self.assertEqual(result.rule_name, "listing_to_frontline")

    def test_active_evidence_includes_price(self):
        result = _rule_listing_to_frontline(
            self.vehicle, dealership=self.default
        )
        self.assertIn("29500", result.evidence)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-lf-active")
        with self.assertRaises(CrossTenantLifecycleError):
            _rule_listing_to_frontline(self.vehicle, dealership=other)

    def test_returns_suggested_transition_type(self):
        result = _rule_listing_to_frontline(
            self.vehicle, dealership=self.default
        )
        self.assertIsInstance(result, SuggestedTransition)


# ============================================================================
# _rule_listing_to_frontline — unmet path
# ============================================================================


class RuleListingToFrontlineUnmet(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_no_listing_returns_unmet_naming_listing(self):
        vehicle = _make_vehicle("M64-LF-NOLISTING", self.default)
        result = _rule_listing_to_frontline(
            vehicle, dealership=self.default
        )
        joined = " ".join(result.unmet_prerequisites)
        self.assertIn("VehicleListing", joined)

    def test_draft_listing_returns_unmet(self):
        vehicle = _make_vehicle("M64-LF-DRAFT", self.default)
        VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_DRAFT,
            body="Draft body.",
            drafted_at=timezone.now(),
        )
        result = _rule_listing_to_frontline(
            vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)
        joined = " ".join(result.unmet_prerequisites)
        self.assertIn("draft", joined)
        self.assertIn("published", joined)

    def test_approved_listing_returns_unmet(self):
        vehicle = _make_vehicle("M64-LF-APPROVED", self.default)
        now = timezone.now()
        VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_APPROVED,
            body="Approved body.",
            drafted_at=now,
            approved_at=now,
        )
        result = _rule_listing_to_frontline(
            vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)
        joined = " ".join(result.unmet_prerequisites)
        self.assertIn("approved", joined)

    def test_unpublished_listing_returns_unmet(self):
        vehicle = _make_vehicle("M64-LF-UNPUB", self.default)
        now = timezone.now()
        VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_UNPUBLISHED,
            body="Was published.",
            drafted_at=now,
            approved_at=now,
            published_at=now,
            unpublished_at=now,
            unpublished_reason="Sold.",
        )
        result = _rule_listing_to_frontline(
            vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)

    def test_zero_price_returns_unmet(self):
        # Create vehicle with price=0, then a published listing.
        vehicle = Vehicle.objects.create(
            stock_number="M64-LF-ZEROPRICE",
            year=2024,
            model="Escape",
            price=Decimal("0.00"),
            dealership=self.default,
        )
        _publish_listing(vehicle, self.default)
        result = _rule_listing_to_frontline(
            vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)
        joined = " ".join(result.unmet_prerequisites)
        self.assertIn("price", joined)

    def test_both_conditions_missing_returns_two_unmets(self):
        vehicle = Vehicle.objects.create(
            stock_number="M64-LF-BOTHMISS",
            year=2024,
            model="Escape",
            price=Decimal("0.00"),
            dealership=self.default,
        )
        # No listing at all + price=0 — both conditions fail.
        result = _rule_listing_to_frontline(
            vehicle, dealership=self.default
        )
        self.assertEqual(len(result.unmet_prerequisites), 2)


# ============================================================================
# suggest_transitions composition — M6.4 extension
# ============================================================================


class SuggestTransitionsM6Composition(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def _seed_at_stage(self, stock: str, stage: str) -> Vehicle:
        v = _make_vehicle(stock, self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=stage
        )
        return v

    def test_photography_stage_dispatches_to_photo_rule(self):
        vehicle = self._seed_at_stage(
            "M64-COMP-PHOTO", VEHICLE_STAGE_PHOTOGRAPHY
        )
        _upload_listing_ready_photos(
            vehicle,
            self.default,
            count=photo_gallery.LISTING_READY_PHOTO_COUNT,
        )
        result = suggest_transitions(vehicle, dealership=self.default)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].rule_name, "photography_to_listing")
        self.assertEqual(result[0].to_stage, VEHICLE_STAGE_LISTING)
        self.assertEqual(result[0].unmet_prerequisites, ())

    def test_listing_stage_dispatches_to_frontline_rule(self):
        vehicle = self._seed_at_stage(
            "M64-COMP-LIST", VEHICLE_STAGE_LISTING
        )
        _publish_listing(vehicle, self.default)
        result = suggest_transitions(vehicle, dealership=self.default)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].rule_name, "listing_to_frontline")
        self.assertEqual(result[0].to_stage, VEHICLE_STAGE_FRONTLINE)
        self.assertEqual(result[0].unmet_prerequisites, ())

    def test_full_lifecycle_walk_generates_correct_suggestions(self):
        """Walk photography → listing → frontline verifying the rule
        composition changes at each stage."""
        vehicle = self._seed_at_stage(
            "M64-COMP-WALK", VEHICLE_STAGE_PHOTOGRAPHY
        )
        # Photography with no photos → photography_to_listing (unmet).
        result = suggest_transitions(vehicle, dealership=self.default)
        self.assertEqual(result[0].rule_name, "photography_to_listing")
        self.assertGreater(len(result[0].unmet_prerequisites), 0)

        # Advance to listing (via ensure_current_stage bootstrap — we
        # skip the real advance_stage since this test exercises rule
        # dispatch, not state-machine).
        vehicle.stage.current_stage = VEHICLE_STAGE_LISTING
        vehicle.stage.save()
        _publish_listing(vehicle, self.default)
        result = suggest_transitions(vehicle, dealership=self.default)
        self.assertEqual(result[0].rule_name, "listing_to_frontline")
        self.assertEqual(result[0].unmet_prerequisites, ())

    def test_frontline_stage_still_returns_empty(self):
        """M6.4 added a rule for LISTING stage; frontline itself
        still has no applicable rule (composition returns empty)."""
        vehicle = self._seed_at_stage(
            "M64-COMP-FRONT", VEHICLE_STAGE_FRONTLINE
        )
        result = suggest_transitions(vehicle, dealership=self.default)
        self.assertEqual(result, [])
