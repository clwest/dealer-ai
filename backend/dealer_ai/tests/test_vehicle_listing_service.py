"""Milestone 6 · Increment 3 (SESSION_084) — vehicle listing service tests.

Coverage of ``dealer_ai/services/vehicle_listing.py``:

- draft_listing happy path (row + provenance + LLM body).
- draft_listing refused when a listing already exists.
- draft_listing cross-tenant refused.
- Scrub-dropped / empty-draft errors not persisted.
- Recon-fact scrub reuse via ``kind='vehicle_listing'`` dispatch.
- Source bundle shape (vehicle facts + findings + photo counts).
- regenerate_draft replaces body / provenance / drafted_at.
- regenerate_draft refused on non-draft.
- approve_listing draft → approved.
- publish_listing approved → published.
- unpublish_listing published → unpublished (reason required).
- Cross-tenant refused on every transition.
- Distinct error hierarchy locked.
- Full lifecycle draft → approved → published → unpublished.

No frontend / API / migration side effects.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    VEHICLE_LISTING_STATUS_APPROVED,
    VEHICLE_LISTING_STATUS_DRAFT,
    VEHICLE_LISTING_STATUS_PUBLISHED,
    VEHICLE_LISTING_STATUS_UNPUBLISHED,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    Vehicle,
    VehicleListing,
)
from dealer_ai.services import photo_gallery, vehicle_listing
from dealer_ai.services.vehicle_listing import (
    CrossTenantListingError,
    EmptyListingDraftError,
    InvalidListingTransitionError,
    ListingImmutableError,
    ListingScrubDroppedError,
    _build_source_bundle,
    approve_listing,
    draft_listing,
    publish_listing,
    regenerate_draft,
    unpublish_listing,
)
from dealer_ai.tests._mocks import MockLLMProvider


User = get_user_model()

_SAMPLE_BODY = (
    "The 2024 Ford Escape SEL is a well-equipped compact SUV ready for "
    "family duty. Comfortable interior, capable all-wheel drive, and a "
    "smooth ride make it a strong pick for daily commuting and weekend "
    "trips."
)

_SAMPLE_PHOTO_BYTES = b"\xff\xd8\xff\xe0fake-jpeg"


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        make="Ford",
        trim="SEL",
        mileage=8_500,
        price=Decimal("29500.00"),
        dealership=dealership,
    )


def _make_actor(username: str):
    return User.objects.create_user(username=username, password="pw12345678")


# ---- draft_listing --------------------------------------------------------


class DraftListing(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63DL-A", self.default)
        self.drafter = _make_actor("m63_drafter_a")
        self.provider = MockLLMProvider(replies=[_SAMPLE_BODY])

    def test_creates_row_at_status_draft(self):
        listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=self.provider,
        )
        self.assertEqual(listing.status, VEHICLE_LISTING_STATUS_DRAFT)
        self.assertEqual(listing.vehicle_id, self.vehicle.pk)
        self.assertEqual(listing.dealership_id, self.default.pk)

    def test_persists_body_from_llm(self):
        listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=self.provider,
        )
        self.assertEqual(listing.body, _SAMPLE_BODY)

    def test_persists_source_provenance(self):
        listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=self.provider,
        )
        prov = listing.source_provenance
        self.assertIn("source_bundle", prov)
        self.assertIn("scrubs_fired", prov)
        self.assertEqual(prov["llm_provider"], "mock")
        # Source bundle carries vehicle facts.
        self.assertEqual(
            prov["source_bundle"]["vehicle"]["stock"], "M63DL-A"
        )

    def test_captures_drafted_by_and_drafted_at(self):
        before = timezone.now()
        listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=self.provider,
        )
        self.assertEqual(listing.drafted_by_id, self.drafter.pk)
        self.assertIsNotNone(listing.drafted_at)
        self.assertGreaterEqual(listing.drafted_at, before)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-dl")
        with self.assertRaises(CrossTenantListingError):
            draft_listing(
                self.vehicle,
                dealership=other,
                drafted_by=self.drafter,
                provider=self.provider,
            )

    def test_refused_when_listing_exists(self):
        draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=self.provider,
        )
        second_provider = MockLLMProvider(replies=[_SAMPLE_BODY])
        with self.assertRaises(ListingImmutableError):
            draft_listing(
                self.vehicle,
                dealership=self.default,
                drafted_by=self.drafter,
                provider=second_provider,
            )

    def test_llm_provider_defaults_when_omitted(self):
        """The service accepts ``provider=None`` and falls through to
        :func:`get_llm_provider`. Not exercised end-to-end here (would
        require Ollama), but the parameter shape is locked."""
        import inspect
        sig = inspect.signature(draft_listing)
        self.assertIn("provider", sig.parameters)
        self.assertIsNone(sig.parameters["provider"].default)


# ---- Draft empty / scrub-dropped -----------------------------------------


class DraftEmptyOrScrubbed(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63DL-EMPTY", self.default)
        self.drafter = _make_actor("m63_drafter_empty")

    def test_empty_llm_output_raises_empty_error(self):
        provider = MockLLMProvider(replies=[""])
        with self.assertRaises(EmptyListingDraftError):
            draft_listing(
                self.vehicle,
                dealership=self.default,
                drafted_by=self.drafter,
                provider=provider,
            )
        # No row persisted.
        self.assertFalse(
            VehicleListing.objects.filter(vehicle=self.vehicle).exists()
        )

    def test_wholesale_rewrite_signal_raises_scrub_dropped(self):
        # A response containing sensitive-pricing phrasing (e.g. "we
        # paid") trips :func:`detect_unsafe_response` →
        # ``dropped_reason='dealer_cost_safety'``. See
        # ``services/chat_engine.py::_RESPONSE_FORBIDDEN_PATTERNS``.
        provider = MockLLMProvider(
            replies=[
                "Great SUV. We paid a fair price for this trade-in."
            ]
        )
        with self.assertRaises(ListingScrubDroppedError):
            draft_listing(
                self.vehicle,
                dealership=self.default,
                drafted_by=self.drafter,
                provider=provider,
            )
        self.assertFalse(
            VehicleListing.objects.filter(vehicle=self.vehicle).exists()
        )


# ---- Scrub integration ---------------------------------------------------


class ScrubIntegration(TestCase):
    """Locks the §5.d Option A user-confirmed decision: the M4.5
    ``_scrub_invented_recon_fact`` scrub fires on
    ``kind='vehicle_listing'`` (via the extended
    ``_RECON_COMM_KINDS`` frozenset in ``services.llm_safety``).
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63SCRUB", self.default)
        self.drafter = _make_actor("m63_scrubber")

    def test_invented_finding_id_stripped(self):
        provider = MockLLMProvider(
            replies=[
                "Great vehicle. Recent work per Finding #9999 completed."
            ]
        )
        listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=provider,
        )
        self.assertNotIn("Finding #9999", listing.body)
        self.assertIn("the finding", listing.body)
        self.assertIn(
            "invented_recon_fact", listing.source_provenance["scrubs_fired"]
        )

    def test_invented_dollar_amount_stripped(self):
        # Source bundle carries no authorized_cost → any $-amount is
        # invented.
        provider = MockLLMProvider(
            replies=[
                "Well-maintained SUV with $500 recent brake work invested."
            ]
        )
        listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=provider,
        )
        self.assertNotIn("$500", listing.body)
        self.assertIn("the quoted amount", listing.body)

    def test_vehicle_listing_kind_in_recon_comm_kinds(self):
        """The dispatch extension is the single source of truth for
        the scrub-firing gate."""
        from dealer_ai.services.llm_safety import _RECON_COMM_KINDS
        self.assertIn("vehicle_listing", _RECON_COMM_KINDS)


# ---- Source bundle -------------------------------------------------------


class SourceBundle(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63SB", self.default)

    def test_includes_vehicle_facts(self):
        bundle = _build_source_bundle(self.vehicle)
        vehicle_facts = bundle["vehicle"]
        self.assertEqual(vehicle_facts["stock"], "M63SB")
        self.assertEqual(vehicle_facts["year"], 2024)
        self.assertEqual(vehicle_facts["make"], "Ford")
        self.assertEqual(vehicle_facts["model"], "Escape")
        self.assertEqual(vehicle_facts["trim"], "SEL")
        self.assertEqual(vehicle_facts["mileage"], 8_500)

    def test_includes_findings_from_latest_completed_report(self):
        report = ConditionReport.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            inspector_name="M. Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=8_500,
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=timezone.now(),
        )
        finding = ConditionFinding.objects.create(
            report=report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Brake pad replacement completed.",
        )
        bundle = _build_source_bundle(self.vehicle)
        self.assertIsNotNone(bundle["condition_report"])
        self.assertEqual(len(bundle["findings"]), 1)
        self.assertEqual(bundle["findings"][0]["id"], finding.pk)

    def test_includes_photo_counts(self):
        # Upload two listing-ready photos (>=1024x768) and one below.
        photo_gallery.upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_PHOTO_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1920,
            height_px=1080,
        )
        photo_gallery.upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_PHOTO_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1024,
            height_px=768,
        )
        photo_gallery.upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_PHOTO_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        bundle = _build_source_bundle(self.vehicle)
        self.assertEqual(bundle["photos"]["total_count"], 3)
        self.assertEqual(bundle["photos"]["listing_ready_count"], 2)


# ---- regenerate_draft ----------------------------------------------------


class RegenerateDraft(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63RE-A", self.default)
        self.drafter = _make_actor("m63_regen_a")
        self.provider_initial = MockLLMProvider(replies=["initial body"])
        self.listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=self.provider_initial,
        )

    def test_replaces_body(self):
        new_provider = MockLLMProvider(replies=["redrafted body v2"])
        updated = regenerate_draft(
            self.listing,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=new_provider,
        )
        self.assertEqual(updated.body, "redrafted body v2")

    def test_updates_drafted_at_and_drafted_by(self):
        new_drafter = _make_actor("m63_regen_b")
        new_provider = MockLLMProvider(replies=["v3 body"])
        before = timezone.now()
        updated = regenerate_draft(
            self.listing,
            dealership=self.default,
            drafted_by=new_drafter,
            provider=new_provider,
        )
        self.assertEqual(updated.drafted_by_id, new_drafter.pk)
        self.assertGreaterEqual(updated.drafted_at, before)

    def test_refused_on_approved(self):
        approve_listing(
            self.listing,
            dealership=self.default,
            approved_by=self.drafter,
        )
        with self.assertRaises(ListingImmutableError):
            regenerate_draft(
                self.listing,
                dealership=self.default,
                drafted_by=self.drafter,
                provider=MockLLMProvider(replies=["nope"]),
            )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-re")
        with self.assertRaises(CrossTenantListingError):
            regenerate_draft(
                self.listing,
                dealership=other,
                drafted_by=self.drafter,
                provider=MockLLMProvider(replies=["nope"]),
            )

    def test_preserves_title(self):
        """title is operator-authored; regenerate replaces body but
        leaves title unchanged."""
        self.listing.title = "Operator-set headline"
        self.listing.save(update_fields=["title"])
        regenerate_draft(
            self.listing,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=MockLLMProvider(replies=["fresh body"]),
        )
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Operator-set headline")


# ---- approve_listing -----------------------------------------------------


class ApproveListing(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63AP-A", self.default)
        self.drafter = _make_actor("m63_approver_a")
        self.approver = _make_actor("m63_approver_b")
        self.listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=MockLLMProvider(replies=[_SAMPLE_BODY]),
        )

    def test_flips_draft_to_approved(self):
        result = approve_listing(
            self.listing,
            dealership=self.default,
            approved_by=self.approver,
        )
        self.assertEqual(result.status, VEHICLE_LISTING_STATUS_APPROVED)

    def test_persists_approved_by_and_approved_at(self):
        before = timezone.now()
        result = approve_listing(
            self.listing,
            dealership=self.default,
            approved_by=self.approver,
        )
        self.assertEqual(result.approved_by_id, self.approver.pk)
        self.assertGreaterEqual(result.approved_at, before)

    def test_refused_on_non_draft(self):
        approve_listing(
            self.listing,
            dealership=self.default,
            approved_by=self.approver,
        )
        with self.assertRaises(InvalidListingTransitionError):
            approve_listing(
                self.listing,
                dealership=self.default,
                approved_by=self.approver,
            )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-ap")
        with self.assertRaises(CrossTenantListingError):
            approve_listing(
                self.listing,
                dealership=other,
                approved_by=self.approver,
            )


# ---- publish_listing -----------------------------------------------------


class PublishListing(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63PB-A", self.default)
        self.drafter = _make_actor("m63_pub_a")
        self.publisher = _make_actor("m63_pub_b")
        self.listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=MockLLMProvider(replies=[_SAMPLE_BODY]),
        )
        approve_listing(
            self.listing,
            dealership=self.default,
            approved_by=self.drafter,
        )

    def test_flips_approved_to_published(self):
        result = publish_listing(
            self.listing,
            dealership=self.default,
            published_by=self.publisher,
        )
        self.assertEqual(result.status, VEHICLE_LISTING_STATUS_PUBLISHED)

    def test_persists_published_by_and_published_at(self):
        before = timezone.now()
        result = publish_listing(
            self.listing,
            dealership=self.default,
            published_by=self.publisher,
        )
        self.assertEqual(result.published_by_id, self.publisher.pk)
        self.assertGreaterEqual(result.published_at, before)

    def test_refused_on_non_approved(self):
        publish_listing(
            self.listing,
            dealership=self.default,
            published_by=self.publisher,
        )
        with self.assertRaises(InvalidListingTransitionError):
            publish_listing(
                self.listing,
                dealership=self.default,
                published_by=self.publisher,
            )

    def test_refused_on_draft(self):
        """Cannot publish a draft directly — must approve first."""
        fresh_vehicle = _make_vehicle("M63PB-DRAFT", self.default)
        draft = draft_listing(
            fresh_vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=MockLLMProvider(replies=[_SAMPLE_BODY]),
        )
        with self.assertRaises(InvalidListingTransitionError):
            publish_listing(
                draft,
                dealership=self.default,
                published_by=self.publisher,
            )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-pb")
        with self.assertRaises(CrossTenantListingError):
            publish_listing(
                self.listing,
                dealership=other,
                published_by=self.publisher,
            )


# ---- unpublish_listing ---------------------------------------------------


class UnpublishListing(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M63UN-A", self.default)
        self.drafter = _make_actor("m63_un_a")
        self.unpublisher = _make_actor("m63_un_b")
        self.listing = draft_listing(
            self.vehicle,
            dealership=self.default,
            drafted_by=self.drafter,
            provider=MockLLMProvider(replies=[_SAMPLE_BODY]),
        )
        approve_listing(
            self.listing,
            dealership=self.default,
            approved_by=self.drafter,
        )
        publish_listing(
            self.listing,
            dealership=self.default,
            published_by=self.drafter,
        )
        self.listing.refresh_from_db()

    def test_flips_published_to_unpublished(self):
        result = unpublish_listing(
            self.listing,
            dealership=self.default,
            unpublished_by=self.unpublisher,
            reason="Vehicle sold pending paperwork.",
        )
        self.assertEqual(result.status, VEHICLE_LISTING_STATUS_UNPUBLISHED)

    def test_persists_unpublished_provenance(self):
        result = unpublish_listing(
            self.listing,
            dealership=self.default,
            unpublished_by=self.unpublisher,
            reason="Withdrawn for price adjustment.",
        )
        self.assertEqual(result.unpublished_by_id, self.unpublisher.pk)
        self.assertIsNotNone(result.unpublished_at)
        self.assertEqual(
            result.unpublished_reason, "Withdrawn for price adjustment."
        )

    def test_refused_on_non_published(self):
        unpublish_listing(
            self.listing,
            dealership=self.default,
            unpublished_by=self.unpublisher,
            reason="First unpublish.",
        )
        with self.assertRaises(InvalidListingTransitionError):
            unpublish_listing(
                self.listing,
                dealership=self.default,
                unpublished_by=self.unpublisher,
                reason="Second attempt.",
            )

    def test_refused_on_empty_reason(self):
        with self.assertRaises(ValueError):
            unpublish_listing(
                self.listing,
                dealership=self.default,
                unpublished_by=self.unpublisher,
                reason="",
            )
        with self.assertRaises(ValueError):
            unpublish_listing(
                self.listing,
                dealership=self.default,
                unpublished_by=self.unpublisher,
                reason="   ",
            )

    def test_reason_truncated_at_255(self):
        long_reason = "x" * 300
        result = unpublish_listing(
            self.listing,
            dealership=self.default,
            unpublished_by=self.unpublisher,
            reason=long_reason,
        )
        self.assertEqual(len(result.unpublished_reason), 255)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-un")
        with self.assertRaises(CrossTenantListingError):
            unpublish_listing(
                self.listing,
                dealership=other,
                unpublished_by=self.unpublisher,
                reason="No cross-tenant.",
            )


# ---- Error hierarchy + full lifecycle -----------------------------------


class ErrorHierarchy(TestCase):
    def test_all_errors_subclass_value_error(self):
        self.assertTrue(issubclass(CrossTenantListingError, ValueError))
        self.assertTrue(
            issubclass(InvalidListingTransitionError, ValueError)
        )
        self.assertTrue(issubclass(ListingImmutableError, ValueError))
        self.assertTrue(issubclass(ListingScrubDroppedError, ValueError))
        self.assertTrue(issubclass(EmptyListingDraftError, ValueError))

    def test_error_classes_are_distinct(self):
        classes = {
            CrossTenantListingError,
            InvalidListingTransitionError,
            ListingImmutableError,
            ListingScrubDroppedError,
            EmptyListingDraftError,
        }
        self.assertEqual(len(classes), 5)


class FullLifecycle(TestCase):
    """Walk the full draft → approved → published → unpublished
    ladder in one test to lock the end-to-end shape."""

    def test_full_lifecycle(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M63LC", default)
        actor = _make_actor("m63_lc_actor")

        listing = draft_listing(
            vehicle,
            dealership=default,
            drafted_by=actor,
            provider=MockLLMProvider(replies=[_SAMPLE_BODY]),
        )
        self.assertEqual(listing.status, VEHICLE_LISTING_STATUS_DRAFT)

        listing = approve_listing(
            listing, dealership=default, approved_by=actor
        )
        self.assertEqual(listing.status, VEHICLE_LISTING_STATUS_APPROVED)

        listing = publish_listing(
            listing, dealership=default, published_by=actor
        )
        self.assertEqual(listing.status, VEHICLE_LISTING_STATUS_PUBLISHED)

        listing = unpublish_listing(
            listing,
            dealership=default,
            unpublished_by=actor,
            reason="Sold.",
        )
        self.assertEqual(listing.status, VEHICLE_LISTING_STATUS_UNPUBLISHED)

    def test_no_direct_redraft_after_unpublish(self):
        """After unpublish, ``draft_listing`` still refuses because a
        listing exists (unpublished). The M6.5+ ``revert_to_draft``
        verb is the intended re-draft path (deferred out of M6.3
        scope). This test locks the current shape so a future
        contributor doesn't accidentally loosen the guard."""
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M63LC-NORE", default)
        actor = _make_actor("m63_norere_actor")
        listing = draft_listing(
            vehicle,
            dealership=default,
            drafted_by=actor,
            provider=MockLLMProvider(replies=[_SAMPLE_BODY]),
        )
        approve_listing(listing, dealership=default, approved_by=actor)
        publish_listing(listing, dealership=default, published_by=actor)
        unpublish_listing(
            listing,
            dealership=default,
            unpublished_by=actor,
            reason="Test.",
        )
        with self.assertRaises(ListingImmutableError):
            draft_listing(
                vehicle,
                dealership=default,
                drafted_by=actor,
                provider=MockLLMProvider(replies=["re-draft"]),
            )


# ---- Module surface -----------------------------------------------------


class ModuleSurface(TestCase):
    """The public surface of ``services.vehicle_listing`` is the
    contract downstream milestones (M6.4 rule, M6.5 endpoint) consume.
    Locked here so a rename triggers a test failure."""

    def test_public_verbs_present(self):
        for verb in (
            "draft_listing",
            "approve_listing",
            "publish_listing",
            "unpublish_listing",
            "regenerate_draft",
        ):
            self.assertTrue(
                hasattr(vehicle_listing, verb),
                f"services.vehicle_listing must expose {verb!r}",
            )
