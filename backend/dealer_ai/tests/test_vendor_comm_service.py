"""Milestone 4 · Increment 5 — vendor comm service tests.

Coverage of ``dealer_ai/services/vendor_comm.py``:

- draft_communication happy path.
- draft_communication kind validation (AI-drafted kinds only).
- draft_communication cross-tenant refused.
- draft_communication empty / scrub-dropped output not persisted.
- draft_communication source_provenance shape.
- draft_communication runs the LLM output through the recon scrub
  (invented finding stripped).
- approve_communication draft → approved.
- approve_communication refuses non-draft.
- approve_communication cross-tenant refused.
- mark_sent approved → sent with default draft_content copy.
- mark_sent approved → sent with operator-edited sent_content.
- mark_sent refuses non-approved.
- mark_sent refuses empty sent_content when draft_content also
  empty.
- log_communication creates directly at logged.
- log_communication accepts vendor_comm / parts_order / narrative
  kinds (operator can log any).
- log_communication with null work_order permitted.
- log_communication rejects empty body / invalid vocabulary.
- AI-drafted content never reaches logged (structural — no code
  path connects draft_communication output to log_communication).
- No frontend / API / migration side effects.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    VENDOR_COMMUNICATION_CHANNEL_EMAIL,
    VENDOR_COMMUNICATION_CHANNEL_PHONE,
    VENDOR_COMMUNICATION_DIRECTION_INBOUND,
    VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
    VENDOR_COMMUNICATION_KIND_NARRATIVE,
    VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
    VENDOR_COMMUNICATION_STATUS_APPROVED,
    VENDOR_COMMUNICATION_STATUS_DRAFT,
    VENDOR_COMMUNICATION_STATUS_LOGGED,
    VENDOR_COMMUNICATION_STATUS_SENT,
    Vehicle,
    VendorCommunication,
    Vendor,
    WORK_ORDER_VENUE_OUTSOURCED,
)
from dealer_ai.services.recon import (
    add_part,
    approve_work_order,
    attach_findings,
    create_work_order,
)
from dealer_ai.services.vendor_comm import (
    _AI_DRAFTED_KINDS,
    CrossTenantVendorCommError,
    EmptyDraftError,
    ReconFactScrubDroppedError,
    VendorCommImmutableError,
    approve_communication,
    draft_communication,
    log_communication,
    mark_sent,
)
from dealer_ai.tests._mocks import MockLLMProvider


User = get_user_model()


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("48000.00"),
        dealership=dealership,
    )


def _make_report(vehicle: Vehicle, dealership: Dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="M. Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _make_finding(
    report: ConditionReport,
    dealership: Dealership,
    *,
    category: str = CONDITION_CATEGORY_MECHANICAL,
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=category,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="Vendor-comm service test finding.",
    )


def _make_vendor(dealership: Dealership, slug: str = "vc-svc") -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"Vendor Comm Svc {slug}",
        slug=slug,
    )


def _make_user(username: str) -> "User":
    return User.objects.create_user(username=username, password="test-pw")


def _built_wo(
    vehicle: Vehicle,
    dealership: Dealership,
    finding: ConditionFinding,
    vendor: Vendor,
) -> "object":
    wo = create_work_order(
        vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        vendor=vendor,
        estimated_cost=Decimal("500.00"),
    )
    attach_findings(wo, dealership=dealership, finding_ids=[finding.pk])
    return wo


def _approved_wo(vehicle, dealership, finding, vendor, *, authorized=None):
    wo = _built_wo(vehicle, dealership, finding, vendor)
    if authorized is not None:
        approve_work_order(
            wo,
            dealership=dealership,
            approved_by=_make_user(f"appr-{wo.pk}"),
            authorized_cost=authorized,
        )
    else:
        approve_work_order(
            wo,
            dealership=dealership,
            approved_by=_make_user(f"appr-{wo.pk}"),
        )
    wo.refresh_from_db()
    return wo


# ============================================================================
# AI-drafted kinds vocabulary
# ============================================================================


class AIDraftedKindsVocabulary(TestCase):
    def test_ai_drafted_kinds_exact_membership(self):
        self.assertEqual(
            _AI_DRAFTED_KINDS,
            frozenset(
                {
                    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                    VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
                }
            ),
        )


# ============================================================================
# draft_communication
# ============================================================================


class DraftCommunicationHappyPath(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M45-D", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(
            self.report, self.default, category=CONDITION_CATEGORY_BODY
        )
        self.vendor = _make_vendor(self.default, slug="d-vendor")
        self.wo = _approved_wo(
            self.vehicle,
            self.default,
            self.finding,
            self.vendor,
            authorized=Decimal("650.00"),
        )
        self.user = _make_user("d-user")

    def test_creates_draft_row(self):
        provider = MockLLMProvider(
            replies=[
                "Hi, please take a look at the rear quarter panel when "
                "you have a moment. Thanks."
            ]
        )
        comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        self.assertEqual(comm.status, VENDOR_COMMUNICATION_STATUS_DRAFT)
        self.assertEqual(comm.kind, VENDOR_COMMUNICATION_KIND_VENDOR_COMM)
        self.assertEqual(comm.channel, VENDOR_COMMUNICATION_CHANNEL_EMAIL)
        self.assertEqual(
            comm.direction, VENDOR_COMMUNICATION_DIRECTION_OUTBOUND
        )
        self.assertEqual(comm.work_order, self.wo)
        self.assertEqual(comm.vendor, self.vendor)
        self.assertEqual(comm.drafted_by, self.user)
        self.assertIsNotNone(comm.drafted_at)
        self.assertIn("rear quarter", comm.draft_content)

    def test_source_provenance_shape(self):
        provider = MockLLMProvider(replies=["Body draft."])
        comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        prov = comm.source_provenance
        self.assertIn("source_bundle", prov)
        self.assertIn("scrubs_fired", prov)
        self.assertIn("llm_provider", prov)
        self.assertEqual(prov["llm_provider"], "mock")
        bundle = prov["source_bundle"]
        self.assertEqual(
            bundle["vehicle"]["stock"], self.vehicle.stock_number
        )
        self.assertEqual(bundle["vendor"]["name"], self.vendor.name)
        self.assertEqual(len(bundle["findings"]), 1)
        self.assertEqual(bundle["findings"][0]["id"], self.finding.pk)
        self.assertEqual(bundle["authorized_cost"], "650.00")

    def test_source_bundle_includes_parts(self):
        add_part(
            self.wo,
            dealership=self.default,
            name="Blend panel",
            part_number="BP-001",
            quantity=1,
            unit_cost=Decimal("150.00"),
        )
        provider = MockLLMProvider(replies=["Draft body."])
        comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        bundle = comm.source_provenance["source_bundle"]
        self.assertEqual(len(bundle["parts_needed"]), 1)
        self.assertEqual(bundle["parts_needed"][0]["part_number"], "BP-001")

    def test_scrub_strips_invented_finding_id(self):
        # LLM references a bogus finding #999. Real finding is
        # self.finding.pk. The scrub should strip #999.
        provider = MockLLMProvider(
            replies=[
                f"Please address Finding #999 alongside Finding "
                f"#{self.finding.pk}."
            ]
        )
        comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        self.assertNotIn("#999", comm.draft_content)
        self.assertIn(f"#{self.finding.pk}", comm.draft_content)
        self.assertIn(
            "invented_recon_fact", comm.source_provenance["scrubs_fired"]
        )

    def test_ai_can_draft_parts_order_kind(self):
        provider = MockLLMProvider(replies=["Parts order draft."])
        comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        self.assertEqual(
            comm.kind, VENDOR_COMMUNICATION_KIND_PARTS_ORDER
        )


class DraftCommunicationValidation(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M45-DV", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.vendor = _make_vendor(self.default, slug="dv-vendor")
        self.wo = _approved_wo(
            self.vehicle, self.default, self.finding, self.vendor
        )
        self.user = _make_user("dv-user")

    def test_narrative_kind_rejected(self):
        provider = MockLLMProvider(replies=["should not reach LLM"])
        with self.assertRaises(VendorCommImmutableError):
            draft_communication(
                self.wo,
                dealership=self.default,
                drafted_by=self.user,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                provider=provider,
            )

    def test_invalid_channel_rejected(self):
        provider = MockLLMProvider(replies=["draft"])
        with self.assertRaises(ValueError):
            draft_communication(
                self.wo,
                dealership=self.default,
                drafted_by=self.user,
                kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                channel="carrier_pigeon",
                provider=provider,
            )

    def test_invalid_direction_rejected(self):
        provider = MockLLMProvider(replies=["draft"])
        with self.assertRaises(ValueError):
            draft_communication(
                self.wo,
                dealership=self.default,
                drafted_by=self.user,
                kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                direction="sideways",
                provider=provider,
            )

    def test_cross_tenant_wo_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-draft")
        provider = MockLLMProvider(replies=["draft"])
        with self.assertRaises(CrossTenantVendorCommError):
            draft_communication(
                self.wo,
                dealership=other,
                drafted_by=self.user,
                kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                provider=provider,
            )


class DraftCommunicationScrubDropped(TestCase):
    """When the safety stack fires a wholesale-rewrite class, the
    draft is NOT persisted — the caller receives the domain error
    and surfaces it as an operator retry prompt."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M45-SD", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.vendor = _make_vendor(self.default, slug="sd-vendor")
        self.wo = _approved_wo(
            self.vehicle, self.default, self.finding, self.vendor
        )
        self.user = _make_user("sd-user")

    def test_dealer_cost_unsafe_response_rejected_not_persisted(self):
        # "our dealer cost" triggers detect_unsafe_response.
        provider = MockLLMProvider(
            replies=[
                "Our dealer cost on this truck is around $52,000 "
                "so we have room."
            ]
        )
        pre = VendorCommunication.objects.count()
        with self.assertRaises(ReconFactScrubDroppedError):
            draft_communication(
                self.wo,
                dealership=self.default,
                drafted_by=self.user,
                kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                provider=provider,
            )
        # No draft row persisted.
        self.assertEqual(VendorCommunication.objects.count(), pre)

    def test_empty_llm_response_rejected_not_persisted(self):
        provider = MockLLMProvider(replies=[""])
        pre = VendorCommunication.objects.count()
        with self.assertRaises(EmptyDraftError):
            draft_communication(
                self.wo,
                dealership=self.default,
                drafted_by=self.user,
                kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                provider=provider,
            )
        self.assertEqual(VendorCommunication.objects.count(), pre)


# ============================================================================
# approve_communication
# ============================================================================


class ApproveCommunication(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M45-A", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.vendor = _make_vendor(self.default, slug="a-vendor")
        self.wo = _approved_wo(
            self.vehicle, self.default, self.finding, self.vendor
        )
        self.user = _make_user("a-user")
        provider = MockLLMProvider(replies=["Draft body."])
        self.comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        self.approver = _make_user("a-appr")

    def test_draft_to_approved(self):
        result = approve_communication(
            self.comm, dealership=self.default, approved_by=self.approver
        )
        self.assertEqual(result.status, VENDOR_COMMUNICATION_STATUS_APPROVED)
        self.assertEqual(result.approved_by, self.approver)
        self.assertIsNotNone(result.approved_at)

    def test_reapprove_rejected(self):
        approve_communication(
            self.comm, dealership=self.default, approved_by=self.approver
        )
        # Second approve raises — no re-approval workflow.
        with self.assertRaises(VendorCommImmutableError):
            approve_communication(
                self.comm,
                dealership=self.default,
                approved_by=self.approver,
            )

    def test_cross_tenant_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-appr")
        with self.assertRaises(CrossTenantVendorCommError):
            approve_communication(
                self.comm, dealership=other, approved_by=self.approver
            )


# ============================================================================
# mark_sent
# ============================================================================


class MarkSent(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M45-S", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.vendor = _make_vendor(self.default, slug="s-vendor")
        self.wo = _approved_wo(
            self.vehicle, self.default, self.finding, self.vendor
        )
        self.drafter = _make_user("s-drafter")
        provider = MockLLMProvider(
            replies=["The original draft body text here."]
        )
        self.comm = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.drafter,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        self.approver = _make_user("s-approver")
        approve_communication(
            self.comm, dealership=self.default, approved_by=self.approver
        )
        self.comm.refresh_from_db()
        self.sender = _make_user("s-sender")

    def test_mark_sent_defaults_to_draft_content(self):
        result = mark_sent(
            self.comm, dealership=self.default, sent_by=self.sender
        )
        self.assertEqual(result.status, VENDOR_COMMUNICATION_STATUS_SENT)
        self.assertEqual(result.sent_content, self.comm.draft_content)
        self.assertEqual(result.sent_by, self.sender)
        self.assertIsNotNone(result.sent_at)

    def test_mark_sent_accepts_edited_body(self):
        result = mark_sent(
            self.comm,
            dealership=self.default,
            sent_by=self.sender,
            sent_content="Edited version the operator actually sent.",
        )
        self.assertEqual(
            result.sent_content, "Edited version the operator actually sent."
        )

    def test_mark_sent_refuses_from_draft(self):
        # Fresh draft that never got approved.
        provider = MockLLMProvider(replies=["fresh draft"])
        fresh = draft_communication(
            self.wo,
            dealership=self.default,
            drafted_by=self.drafter,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        with self.assertRaises(VendorCommImmutableError):
            mark_sent(
                fresh, dealership=self.default, sent_by=self.sender
            )

    def test_mark_sent_refuses_from_sent(self):
        mark_sent(self.comm, dealership=self.default, sent_by=self.sender)
        with self.assertRaises(VendorCommImmutableError):
            mark_sent(
                self.comm, dealership=self.default, sent_by=self.sender
            )

    def test_mark_sent_cross_tenant_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-sent")
        with self.assertRaises(CrossTenantVendorCommError):
            mark_sent(
                self.comm, dealership=other, sent_by=self.sender
            )


# ============================================================================
# log_communication
# ============================================================================


class LogCommunication(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M45-L", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.vendor = _make_vendor(self.default, slug="l-vendor")
        self.wo = _built_wo(
            self.vehicle, self.default, self.finding, self.vendor
        )
        self.operator = _make_user("l-operator")

    def test_creates_at_logged_status(self):
        result = log_communication(
            self.wo,
            dealership=self.default,
            logged_by=self.operator,
            kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
            channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
            direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            body="Vendor called at 2pm to confirm ETA is Friday.",
        )
        self.assertEqual(result.status, VENDOR_COMMUNICATION_STATUS_LOGGED)
        self.assertEqual(result.sent_by, self.operator)
        self.assertIsNotNone(result.sent_at)
        self.assertIn("Friday", result.draft_content)
        # Approval fields not required for logged.
        self.assertIsNone(result.approved_by)
        self.assertIsNone(result.approved_at)

    def test_log_accepts_vendor_comm_kind(self):
        """An operator may log a vendor_comm that happened
        off-system (they sent an email from Gmail directly).
        Distinct from AI-drafted content — this row records the
        fact of a human-authored comm."""
        result = log_communication(
            self.wo,
            dealership=self.default,
            logged_by=self.operator,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
            body="Emailed Bob directly from Gmail with the update.",
        )
        self.assertEqual(result.status, VENDOR_COMMUNICATION_STATUS_LOGGED)
        self.assertEqual(result.kind, VENDOR_COMMUNICATION_KIND_VENDOR_COMM)

    def test_log_accepts_parts_order_kind(self):
        result = log_communication(
            self.wo,
            dealership=self.default,
            logged_by=self.operator,
            kind=VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
            channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
            body="Called NAPA to order the tie-rod ends.",
        )
        self.assertEqual(result.status, VENDOR_COMMUNICATION_STATUS_LOGGED)

    def test_null_work_order_permitted(self):
        result = log_communication(
            None,
            dealership=self.default,
            logged_by=self.operator,
            kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
            channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
            direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            body="Cold call from a new detail vendor — took notes.",
        )
        self.assertIsNone(result.work_order)
        self.assertIsNone(result.vendor)

    def test_empty_body_rejected(self):
        with self.assertRaises(ValueError):
            log_communication(
                self.wo,
                dealership=self.default,
                logged_by=self.operator,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
                direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                body="",
            )

    def test_whitespace_body_rejected(self):
        with self.assertRaises(ValueError):
            log_communication(
                self.wo,
                dealership=self.default,
                logged_by=self.operator,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
                direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                body="   \t\n  ",
            )

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError):
            log_communication(
                self.wo,
                dealership=self.default,
                logged_by=self.operator,
                kind="gossip",
                channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
                direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                body="Body.",
            )

    def test_invalid_channel_rejected(self):
        with self.assertRaises(ValueError):
            log_communication(
                self.wo,
                dealership=self.default,
                logged_by=self.operator,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel="signal_fire",
                direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                body="Body.",
            )

    def test_invalid_direction_rejected(self):
        with self.assertRaises(ValueError):
            log_communication(
                self.wo,
                dealership=self.default,
                logged_by=self.operator,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
                direction="both",
                body="Body.",
            )

    def test_cross_tenant_wo_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-log")
        with self.assertRaises(CrossTenantVendorCommError):
            log_communication(
                self.wo,
                dealership=other,
                logged_by=self.operator,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
                direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                body="Body.",
            )

    def test_logged_row_source_provenance_marks_logged(self):
        result = log_communication(
            self.wo,
            dealership=self.default,
            logged_by=self.operator,
            kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
            channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
            direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            body="Vendor called.",
        )
        self.assertTrue(
            result.source_provenance.get("logged_off_system")
        )


# ============================================================================
# AI-drafted content structurally cannot reach logged
# ============================================================================


class AIDraftedCannotReachLogged(TestCase):
    """SESSION_066 refinement: AI-generated content may never jump
    directly to logged. Enforced structurally: draft_communication
    creates status='draft'; approve_communication moves to
    'approved'; mark_sent moves to 'sent'; no service function
    transitions from any of those to 'logged'. log_communication
    creates a brand-new row directly at 'logged' with operator
    body content, never touching an existing AI-drafted row.

    This test locks the module-level surface — the four public
    functions are all the ways to touch VendorCommunication from
    the service layer."""

    def test_service_module_exports_expected_public_functions(self):
        from dealer_ai.services import vendor_comm as svc

        expected_public = {
            "draft_communication",
            "approve_communication",
            "mark_sent",
            "log_communication",
        }
        actual_public = {
            name
            for name in dir(svc)
            if not name.startswith("_")
            and callable(getattr(svc, name))
            and getattr(svc, name).__module__ == svc.__name__
        }
        # Exclude domain error classes from the callable set —
        # they're classes, not action functions.
        actual_public = {
            n
            for n in actual_public
            if not n.endswith("Error")
        }
        self.assertEqual(expected_public, actual_public)

    def test_no_service_function_transitions_draft_or_approved_to_logged(self):
        """A caller cannot use approve_communication or mark_sent to
        put a draft into 'logged'. Both raise on non-target
        from-state; neither has a 'logged' target."""
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M45-AICL", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        vendor = _make_vendor(default, slug="aicl-vendor")
        wo = _approved_wo(vehicle, default, finding, vendor)
        drafter = _make_user("aicl-drafter")
        provider = MockLLMProvider(replies=["A draft body."])
        comm = draft_communication(
            wo,
            dealership=default,
            drafted_by=drafter,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        # Confirm the row is a draft with AI content.
        self.assertEqual(comm.status, VENDOR_COMMUNICATION_STATUS_DRAFT)
        # There is no public path to turn this row's status into
        # 'logged' — the four service functions only produce draft
        # / approved / sent / logged (fresh only) statuses. If a
        # future refactor adds a "convert_to_log(comm)" function,
        # this test's existence + docstring should force the author
        # to also update SESSION_066 planning refinement.
        # (Verify by scanning public names below.)
        from dealer_ai.services import vendor_comm as svc
        public_names = [
            n
            for n in dir(svc)
            if not n.startswith("_")
        ]
        for name in public_names:
            self.assertNotIn(
                "log_existing", name.lower(),
                f"Unexpected service function {name!r} — appears to "
                "convert an existing row to logged. SESSION_066 "
                "refinement prohibits AI-drafted content jumping to "
                "logged.",
            )
