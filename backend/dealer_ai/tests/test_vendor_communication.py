"""Milestone 4 · Increment 1 — VendorCommunication model tests.

Persistence-layer coverage only. AI drafting, source-provenance
recording, send / SMS wiring, and state-transition workflow all land
at M4.5 per ``MILESTONE_4_PLANNING.md`` §7 M4.5.

Locked invariants:

- Kind + channel + direction + status enum vocabularies (all four).
- ``vendor`` FK uses PROTECT — referenced Vendor cannot be
  hard-deleted (verified in ``test_vendor.py``).
- ``vendor.dealership`` matches self.dealership when set.
- ``work_order.dealership`` matches self.dealership when set.
- Cross-tenant vendor + WO pairing rejected.
- ``status='sent'`` requires nonblank sent_content + approved_by +
  approved_at + sent_by + sent_at.
- ``status='approved'`` requires approved_by + approved_at.
- ``status='logged'`` requires nonblank draft_content + sent_by +
  sent_at (NO approved_by required — SESSION_066 refinement).
- ``source_provenance`` defaults to empty dict.
- No LLM / send side effects on model save.
- Cascade / SET_NULL / PROTECT behaviors match the contract.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    Dealership,
    VENDOR_COMMUNICATION_CHANNEL_CHOICES,
    VENDOR_COMMUNICATION_CHANNEL_EMAIL,
    VENDOR_COMMUNICATION_CHANNEL_INTERNAL_NOTE,
    VENDOR_COMMUNICATION_CHANNEL_IN_PERSON,
    VENDOR_COMMUNICATION_CHANNEL_PHONE,
    VENDOR_COMMUNICATION_CHANNEL_SMS,
    VENDOR_COMMUNICATION_DIRECTION_CHOICES,
    VENDOR_COMMUNICATION_DIRECTION_INBOUND,
    VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
    VENDOR_COMMUNICATION_KIND_CHOICES,
    VENDOR_COMMUNICATION_KIND_NARRATIVE,
    VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
    VENDOR_COMMUNICATION_STATUS_APPROVED,
    VENDOR_COMMUNICATION_STATUS_CHOICES,
    VENDOR_COMMUNICATION_STATUS_DRAFT,
    VENDOR_COMMUNICATION_STATUS_LOGGED,
    VENDOR_COMMUNICATION_STATUS_SENT,
    Vehicle,
    Vendor,
    VendorCommunication,
    WORK_ORDER_VENUE_OUTSOURCED,
    WorkOrder,
)


User = get_user_model()


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("48000.00"),
        dealership=dealership,
    )


def _make_vendor(dealership: Dealership, slug: str = "vc-vendor") -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"VC Vendor {slug}",
        slug=slug,
    )


def _make_wo(vehicle: Vehicle, vendor: Vendor, dealership: Dealership) -> WorkOrder:
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        vendor=vendor,
    )


def _make_user(username: str = "vc-user") -> "User":
    return User.objects.create_user(username=username, password="test-pass")


# ============================================================================
# Enum vocabularies
# ============================================================================


class VendorCommunicationKindVocabulary(TestCase):
    def test_choices_contain_expected_kinds(self):
        keys = {key for key, _ in VENDOR_COMMUNICATION_KIND_CHOICES}
        self.assertEqual(
            keys,
            {
                VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
                VENDOR_COMMUNICATION_KIND_NARRATIVE,
            },
        )


class VendorCommunicationChannelVocabulary(TestCase):
    def test_choices_contain_expected_channels(self):
        keys = {key for key, _ in VENDOR_COMMUNICATION_CHANNEL_CHOICES}
        self.assertEqual(
            keys,
            {
                VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                VENDOR_COMMUNICATION_CHANNEL_SMS,
                VENDOR_COMMUNICATION_CHANNEL_PHONE,
                VENDOR_COMMUNICATION_CHANNEL_IN_PERSON,
                VENDOR_COMMUNICATION_CHANNEL_INTERNAL_NOTE,
            },
        )
        self.assertEqual(len(VENDOR_COMMUNICATION_CHANNEL_CHOICES), 5)


class VendorCommunicationDirectionVocabulary(TestCase):
    def test_choices_contain_two_directions(self):
        keys = {key for key, _ in VENDOR_COMMUNICATION_DIRECTION_CHOICES}
        self.assertEqual(
            keys,
            {
                VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
                VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            },
        )
        self.assertEqual(len(VENDOR_COMMUNICATION_DIRECTION_CHOICES), 2)


class VendorCommunicationStatusVocabulary(TestCase):
    """Four canonical status values — no ``failed`` in M4.1 (retry /
    bounce handling deferred to prod-readiness pass)."""

    def test_choices_contain_exactly_four_canonical_statuses(self):
        keys = {key for key, _ in VENDOR_COMMUNICATION_STATUS_CHOICES}
        self.assertEqual(
            keys,
            {
                VENDOR_COMMUNICATION_STATUS_DRAFT,
                VENDOR_COMMUNICATION_STATUS_APPROVED,
                VENDOR_COMMUNICATION_STATUS_SENT,
                VENDOR_COMMUNICATION_STATUS_LOGGED,
            },
        )
        self.assertEqual(len(VENDOR_COMMUNICATION_STATUS_CHOICES), 4)


# ============================================================================
# Field-shape smokes + defaults
# ============================================================================


class VendorCommunicationDraftCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41VC-DRAFT", self.default)
        self.vendor = _make_vendor(self.default, slug="draft-vendor")
        self.wo = _make_wo(self.vehicle, self.vendor, self.default)
        self.user = _make_user("vc-drafter")

    def test_draft_round_trip(self):
        comm = VendorCommunication.objects.create(
            dealership=self.default,
            vendor=self.vendor,
            work_order=self.wo,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
            status=VENDOR_COMMUNICATION_STATUS_DRAFT,
            draft_content="Hi Bob, could you take a look at the F-150...",
            drafted_by=self.user,
            drafted_at=timezone.now(),
        )
        fetched = VendorCommunication.objects.get(pk=comm.pk)
        self.assertEqual(fetched.status, VENDOR_COMMUNICATION_STATUS_DRAFT)
        self.assertIn("F-150", fetched.draft_content)
        # Approved / sent provenance all null at draft stage.
        self.assertIsNone(fetched.approved_by)
        self.assertIsNone(fetched.approved_at)
        self.assertIsNone(fetched.sent_by)
        self.assertIsNone(fetched.sent_at)
        # source_provenance defaults to empty dict.
        self.assertEqual(fetched.source_provenance, {})

    def test_source_provenance_default_empty_dict(self):
        comm = VendorCommunication.objects.create(
            dealership=self.default,
            vendor=self.vendor,
            kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
            channel=VENDOR_COMMUNICATION_CHANNEL_INTERNAL_NOTE,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
        )
        self.assertEqual(comm.source_provenance, {})


# ============================================================================
# Status-invariant matrix (SESSION_066 refinement)
# ============================================================================


class VendorCommunicationApprovedStateRequirements(TestCase):
    """status='approved' requires approved_by + approved_at."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.user = _make_user("vc-approver")
        self.now = timezone.now()

    def _base(self, **overrides):
        base = dict(
            dealership=self.default,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
            status=VENDOR_COMMUNICATION_STATUS_APPROVED,
            draft_content="Body.",
        )
        base.update(overrides)
        return VendorCommunication(**base)

    def test_approved_without_approved_by_rejected(self):
        comm = self._base(approved_at=self.now)
        with self.assertRaises(ValidationError):
            comm.full_clean()

    def test_approved_without_approved_at_rejected(self):
        comm = self._base(approved_by=self.user)
        with self.assertRaises(ValidationError):
            comm.full_clean()

    def test_approved_with_both_fields_passes(self):
        comm = self._base(approved_by=self.user, approved_at=self.now)
        comm.full_clean()


class VendorCommunicationSentStateRequirements(TestCase):
    """status='sent' requires nonblank sent_content + approved_by +
    approved_at + sent_by + sent_at."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.approver = _make_user("vc-sent-approver")
        self.sender = _make_user("vc-sent-sender")
        self.now = timezone.now()

    def _base(self, **overrides):
        base = dict(
            dealership=self.default,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
            status=VENDOR_COMMUNICATION_STATUS_SENT,
            draft_content="Draft body.",
            sent_content="Final sent body.",
            approved_by=self.approver,
            approved_at=self.now,
            sent_by=self.sender,
            sent_at=self.now,
        )
        base.update(overrides)
        return VendorCommunication(**base)

    def test_sent_with_all_fields_passes(self):
        self._base().full_clean()

    def test_sent_without_sent_content_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(sent_content="").full_clean()

    def test_sent_with_whitespace_only_sent_content_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(sent_content="   \n  ").full_clean()

    def test_sent_without_approved_by_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(approved_by=None).full_clean()

    def test_sent_without_sent_by_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(sent_by=None).full_clean()

    def test_sent_without_sent_at_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(sent_at=None).full_clean()


class VendorCommunicationLoggedStateRequirements(TestCase):
    """SESSION_066 refinement: logged is a separate workflow from
    sent. Requires nonblank draft_content (recorded body) + sent_by
    (human actor) + sent_at (timestamp). NO approved_by / approved_at
    required — operator-recorded phone / in-person comms have no
    approval step."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.operator = _make_user("vc-log-operator")
        self.now = timezone.now()

    def _base(self, **overrides):
        base = dict(
            dealership=self.default,
            kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
            channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
            direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            status=VENDOR_COMMUNICATION_STATUS_LOGGED,
            draft_content="Called Bob at 2pm; parts ETA is Friday.",
            sent_by=self.operator,
            sent_at=self.now,
        )
        base.update(overrides)
        return VendorCommunication(**base)

    def test_logged_without_approval_fields_passes(self):
        """The load-bearing SESSION_066 assertion — logged must NOT
        require the prior approval step that sent requires."""
        comm = self._base()
        # Deliberately no approved_by / approved_at supplied.
        comm.full_clean()

    def test_logged_without_draft_content_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(draft_content="").full_clean()

    def test_logged_without_sent_by_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(sent_by=None).full_clean()

    def test_logged_without_sent_at_rejected(self):
        with self.assertRaises(ValidationError):
            self._base(sent_at=None).full_clean()

    def test_logged_with_only_approved_fields_still_rejected(self):
        """Supplying approved_by/approved_at without the required
        sent_by/sent_at + draft_content does not satisfy the logged
        contract."""
        approver = _make_user("vc-log-approver")
        with self.assertRaises(ValidationError):
            self._base(
                sent_by=None,
                sent_at=None,
                approved_by=approver,
                approved_at=self.now,
            ).full_clean()


# ============================================================================
# Tenant guards
# ============================================================================


class VendorCommunicationCrossTenantGuards(TestCase):
    """Three cross-tenant guards: (1) vendor.dealership matches;
    (2) work_order.dealership matches; (3) when both are set, they
    match each other."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-vc"
        )
        self.vehicle_at_a = _make_vehicle("M41VC-XT-A", self.dealership_a)
        self.vehicle_at_b = _make_vehicle("M41VC-XT-B", self.dealership_b)
        self.vendor_at_a = _make_vendor(self.dealership_a, slug="xt-a")
        self.vendor_at_b = _make_vendor(self.dealership_b, slug="xt-b")
        self.wo_at_a = _make_wo(
            self.vehicle_at_a, self.vendor_at_a, self.dealership_a
        )
        self.wo_at_b = _make_wo(
            self.vehicle_at_b, self.vendor_at_b, self.dealership_b
        )

    def test_vendor_dealership_mismatch_rejected(self):
        comm = VendorCommunication(
            dealership=self.dealership_a,
            vendor=self.vendor_at_b,  # cross-tenant vendor
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
        )
        with self.assertRaises(ValidationError) as ctx:
            comm.full_clean()
        self.assertIn("vendor", ctx.exception.message_dict)

    def test_work_order_dealership_mismatch_rejected(self):
        comm = VendorCommunication(
            dealership=self.dealership_a,
            work_order=self.wo_at_b,  # cross-tenant WO
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
        )
        with self.assertRaises(ValidationError) as ctx:
            comm.full_clean()
        self.assertIn("work_order", ctx.exception.message_dict)

    def test_vendor_and_work_order_dealership_mismatch_rejected(self):
        # Both vendor and WO exist but belong to different dealerships.
        # dealership on the row itself matches vendor, but the vendor
        # and WO belong to different dealerships → the third guard
        # rejects.
        comm = VendorCommunication(
            dealership=self.dealership_a,
            vendor=self.vendor_at_a,
            work_order=self.wo_at_b,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
        )
        with self.assertRaises(ValidationError) as ctx:
            comm.full_clean()
        # The WO tenancy guard fires first — either message key is
        # acceptable since both invariants are violated.
        self.assertTrue(
            "work_order" in ctx.exception.message_dict
            or "vendor" in ctx.exception.message_dict
        )

    def test_matching_all_passes(self):
        comm = VendorCommunication(
            dealership=self.dealership_a,
            vendor=self.vendor_at_a,
            work_order=self.wo_at_a,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
        )
        comm.full_clean()


class VendorCommunicationVendorNullable(TestCase):
    """Nullable vendor — inbound calls / logged rows may precede
    vendor identification."""

    def test_null_vendor_permitted_on_inbound_logged_row(self):
        default = Dealership.objects.get(slug="default")
        operator = _make_user("vc-null-vendor")
        comm = VendorCommunication.objects.create(
            dealership=default,
            vendor=None,
            kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
            channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
            direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            status=VENDOR_COMMUNICATION_STATUS_LOGGED,
            draft_content="Anonymous vendor callback re: F-150.",
            sent_by=operator,
            sent_at=timezone.now(),
        )
        comm.full_clean()  # must not raise on null vendor at logged status


# ============================================================================
# SET_NULL / cascade behaviors
# ============================================================================


class VendorCommunicationWorkOrderSetNullOnDelete(TestCase):
    """work_order FK is SET_NULL — deleting the WO leaves the comm
    row intact with work_order_id=NULL. Contrast with vendor which
    is PROTECT."""

    def test_deleting_work_order_sets_null_on_comm(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41VC-WOSN", default)
        vendor = _make_vendor(default, slug="wosn-vendor")
        wo = _make_wo(vehicle, vendor, default)
        comm = VendorCommunication.objects.create(
            dealership=default,
            vendor=vendor,
            work_order=wo,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
        )
        wo.delete()
        fetched = VendorCommunication.objects.get(pk=comm.pk)
        self.assertIsNone(fetched.work_order_id)


class VendorCommunicationDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            VendorCommunication._meta.get_field("dealership").null
        )
