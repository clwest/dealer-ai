"""Milestone 35 · Increment 1 (SESSION_217) — nested-annotation
``latest_lender_submission_status`` regression tests.

Locks the M35.1 D2 backend surface per
``MILESTONE_35_PLANNING.md`` §5.b D2 + §5.c R11.

The D2 annotation on ``list_credit_applications`` layers a second
subquery on top of the M33.1 ``latest_deal_structure_id``
annotation, correlating on
``OuterRef("latest_deal_structure_id")``. Django generates ANSI-
standard correlated subqueries that compile + execute on both
SQLite (verified M35.0 §4.8) and Postgres (verified M35.1 §0.a).

Eight-case R11 regression matrix (per user directive #7 at M35.0):

1. No DealStructure → status = None
2. DealStructure with no submissions → status = None
3. One submission (pending) → status = "pending"
4. Multiple submissions (latest = approved) → status = "approved"
5. Shared ``submitted_at`` → tie-break on ``created_at`` DESC
6. Shared ``submitted_at`` + ``created_at`` → tie-break on ``pk`` DESC
7. Multiple DealStructures where older has approved submission
   but latest has none → status = None (proves current-iteration
   semantic — the latest DealStructure defines the deal;
   submissions on prior structures do not project through)
8. Cross-tenant rows via direct ORM bypass → excluded (belt-and-
   suspenders per M33.1 pattern)

Also covers the CA-list projection extension (D3) — the endpoint
projection carries the new ``latest_lender_submission_status``
field alongside the M33.1 fields.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    LENDER_SUBMISSION_STATUS_APPROVED,
    LENDER_SUBMISSION_STATUS_COUNTER,
    LENDER_SUBMISSION_STATUS_DECLINED,
    LENDER_SUBMISSION_STATUS_PENDING,
    ROLE_F_AND_I_MANAGER,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    list_credit_applications,
    record_deal_structure,
    record_lender_submission,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


LIST_ENDPOINT = "dealer_ai:admin-credit-application-list"


# ---------------------------------------------------------------------------
# Fixture helpers (local, matching M33.1 pattern)
# ---------------------------------------------------------------------------


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("40000.00"),
        dealership=dealership,
    )


def _make_credit_app(dealership: Dealership, *, name: str = "Alice") -> CreditApplication:
    lead = CustomerLead.objects.create(dealership=dealership, name=name)
    captured = timezone.now()
    return CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name=name,
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
    )


def _make_deal_structure(
    dealership: Dealership,
    credit_app: CreditApplication,
    vehicle: Vehicle,
) -> DealStructure:
    return record_deal_structure(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=Decimal("30000.00"),
        amount_financed=Decimal("25000.00"),
        apr=Decimal("9.9900"),
        term_months=72,
        monthly_payment=Decimal("500.00"),
    )


def _make_lender_program(
    dealership: Dealership, name: str = "M35 Bank"
) -> LenderProgram:
    return LenderProgram.objects.create(
        dealership=dealership, name=name, is_active=True
    )


def _fandi_client_at(dealership: Dealership, username: str) -> APIClient:
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


# ---------------------------------------------------------------------------
# Service layer — D2 annotation R11 regression matrix
# ---------------------------------------------------------------------------


class LenderSubmissionStatusAnnotationTests(TestCase):
    """R11 8-case matrix on the D2 nested-annotation subquery.

    The subquery correlates on the D1 annotation
    (``OuterRef("latest_deal_structure_id")``) — the first
    codebase occurrence of correlation-on-annotation. Live-tested
    on SQLite at M35.0 §4.8 and Postgres at M35.1 §0.a; these
    tests lock the behavior against future regression."""

    def setUp(self) -> None:
        self.d = Dealership.objects.create(slug="m351-a", name="M35.1 A")

    def test_case1_no_deal_structure_returns_none(self) -> None:
        """Case 1 — CA with no DealStructure → status = None."""
        _make_credit_app(self.d, name="Incoming")
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].latest_deal_structure_id)
        self.assertIsNone(rows[0].latest_lender_submission_status)

    def test_case2_deal_structure_no_submissions_returns_none(self) -> None:
        """Case 2 — DealStructure exists but no LenderSubmission on
        it → status = None (M33 In progress state)."""
        ca = _make_credit_app(self.d, name="Structured")
        ds = _make_deal_structure(self.d, ca, _make_vehicle(self.d, "S-1"))
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(rows[0].latest_deal_structure_id, ds.pk)
        self.assertIsNone(rows[0].latest_lender_submission_status)

    def test_case3_one_pending_submission_returns_pending(self) -> None:
        """Case 3 — one LenderSubmission (pending) → status =
        "pending"."""
        ca = _make_credit_app(self.d, name="Pending")
        ds = _make_deal_structure(self.d, ca, _make_vehicle(self.d, "P-1"))
        lp = _make_lender_program(self.d)
        record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_PENDING,
        )
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(
            rows[0].latest_lender_submission_status,
            LENDER_SUBMISSION_STATUS_PENDING,
        )

    def test_case4_multiple_submissions_latest_wins(self) -> None:
        """Case 4 — multiple submissions on the same DealStructure;
        latest by ``-submitted_at`` wins (approved)."""
        ca = _make_credit_app(self.d, name="Multi")
        ds = _make_deal_structure(self.d, ca, _make_vehicle(self.d, "M-1"))
        lp = _make_lender_program(self.d)
        # Older submission — declined
        s_old = record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_DECLINED,
        )
        # Newer submission — approved
        s_new = record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
        )
        # Force explicit ordering — s_new is newer.
        LenderSubmission.objects.filter(pk=s_old.pk).update(
            submitted_at=timezone.now() - timedelta(seconds=10)
        )
        LenderSubmission.objects.filter(pk=s_new.pk).update(
            submitted_at=timezone.now() + timedelta(seconds=10)
        )
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(
            rows[0].latest_lender_submission_status,
            LENDER_SUBMISSION_STATUS_APPROVED,
        )

    def test_case5_shared_submitted_at_tiebreaks_on_created_at(self) -> None:
        """Case 5 — two submissions with identical ``submitted_at`` —
        tie-break on ``created_at`` DESC. Force distinct
        ``created_at`` on rows with matching ``submitted_at``."""
        ca = _make_credit_app(self.d, name="TieSubmitted")
        ds = _make_deal_structure(self.d, ca, _make_vehicle(self.d, "TS-1"))
        lp = _make_lender_program(self.d)
        s1 = record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_DECLINED,
        )
        s2 = record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
        )
        shared_ts = timezone.now()
        LenderSubmission.objects.filter(pk__in=[s1.pk, s2.pk]).update(
            submitted_at=shared_ts
        )
        # Distinct created_at — s2 is newer.
        LenderSubmission.objects.filter(pk=s1.pk).update(
            created_at=timezone.now() - timedelta(seconds=10)
        )
        LenderSubmission.objects.filter(pk=s2.pk).update(
            created_at=timezone.now() + timedelta(seconds=10)
        )
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(
            rows[0].latest_lender_submission_status,
            LENDER_SUBMISSION_STATUS_APPROVED,
        )

    def test_case6_shared_submitted_at_and_created_at_tiebreaks_on_pk(
        self,
    ) -> None:
        """Case 6 — two submissions with identical ``submitted_at``
        AND ``created_at`` — tie-break on ``pk`` DESC (higher pk
        wins). Absolute deterministic fallback per D2 lock."""
        ca = _make_credit_app(self.d, name="TieAll")
        ds = _make_deal_structure(self.d, ca, _make_vehicle(self.d, "TA-1"))
        lp = _make_lender_program(self.d)
        s1 = record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_DECLINED,
        )
        s2 = record_lender_submission(
            dealership=self.d,
            deal_structure=ds,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_COUNTER,
        )
        # Force identical timestamps on both.
        shared_ts = timezone.now()
        LenderSubmission.objects.filter(pk__in=[s1.pk, s2.pk]).update(
            submitted_at=shared_ts, created_at=shared_ts
        )
        # Higher pk (s2) wins — status = counter.
        rows = list_credit_applications(dealership=self.d)
        expected = (
            LENDER_SUBMISSION_STATUS_COUNTER
            if s2.pk > s1.pk
            else LENDER_SUBMISSION_STATUS_DECLINED
        )
        self.assertEqual(rows[0].latest_lender_submission_status, expected)

    def test_case7_older_ds_approved_latest_ds_no_submission_returns_none(
        self,
    ) -> None:
        """Case 7 — CRITICAL current-iteration semantic proof.

        CA has two DealStructures: DS1 (older, has approved
        LenderSubmission) + DS2 (newer, no LenderSubmission). The
        derived state must reflect the LATEST DealStructure's
        latest submission — which is None. This proves the D2
        correlation on ``latest_deal_structure_id`` is intentional
        (the deal is defined by the latest desking iteration; prior
        approvals on abandoned structures do not project through)."""
        ca = _make_credit_app(self.d, name="Iteration")
        v1 = _make_vehicle(self.d, "IT-1")
        v2 = _make_vehicle(self.d, "IT-2")
        ds1 = _make_deal_structure(self.d, ca, v1)
        ds2 = _make_deal_structure(self.d, ca, v2)
        lp = _make_lender_program(self.d)
        # DS1 (older) has an approved submission.
        record_lender_submission(
            dealership=self.d,
            deal_structure=ds1,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
        )
        # Force DS2 to be the latest.
        DealStructure.objects.filter(pk=ds1.pk).update(
            created_at=timezone.now() - timedelta(seconds=10)
        )
        DealStructure.objects.filter(pk=ds2.pk).update(
            created_at=timezone.now() + timedelta(seconds=10)
        )
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(rows[0].latest_deal_structure_id, ds2.pk)
        # Latest DS (ds2) has no submissions → status = None even
        # though ds1 has approved submission. Current-iteration
        # semantic locked.
        self.assertIsNone(rows[0].latest_lender_submission_status)

    def test_case8_cross_tenant_submission_does_not_leak(self) -> None:
        """Case 8 — belt-over-suspenders. If a bug elsewhere ever
        created a cross-tenant LenderSubmission targeting an own-
        tenant DealStructure (which the model ``clean()`` +
        service ``CrossTenantLenderSubmissionError`` would already
        refuse), the annotation still must not project it. Bypass
        the guards via direct ORM create."""
        other = Dealership.objects.create(slug="m351-o", name="Other")
        ca = _make_credit_app(self.d, name="Own")
        ds = _make_deal_structure(self.d, ca, _make_vehicle(self.d, "X-1"))
        cross_lp = _make_lender_program(other, name="Cross Bank")
        # Bypass service + model clean() via direct ORM create with
        # a mismatched dealership on the submission.
        LenderSubmission.objects.create(
            dealership=other,
            deal_structure=ds,
            lender_program=cross_lp,
            submitted_at=timezone.now(),
            status=LENDER_SUBMISSION_STATUS_APPROVED,
        )
        # Own-tenant list must not project the cross-tenant status.
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(rows[0].latest_deal_structure_id, ds.pk)
        self.assertIsNone(rows[0].latest_lender_submission_status)


# ---------------------------------------------------------------------------
# Endpoint layer — CA list projection extension (D3)
# ---------------------------------------------------------------------------


class CreditApplicationListProjectionM35Tests(TestCase):
    """D3 projection extension — CA list rows carry the new
    ``latest_lender_submission_status`` field alongside M33's
    ``has_deal_structure`` + ``latest_deal_structure_id``."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        self.client = _fandi_client_at(self.d, "m351-proj")

    def test_projection_incoming_row_has_null_submission_status(self) -> None:
        _make_credit_app(self.d, name="Empty")
        resp = self.client.get(reverse(LIST_ENDPOINT))
        row = resp.json()["credit_applications"][0]
        self.assertIn("latest_lender_submission_status", row)
        self.assertIsNone(row["latest_lender_submission_status"])

    def test_projection_in_progress_row_has_null_submission_status(
        self,
    ) -> None:
        """DealStructure exists but no submission → new field is
        null; M33 fields carry the DS state."""
        ca = _make_credit_app(self.d, name="Structured")
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "SP-1")
        )
        resp = self.client.get(reverse(LIST_ENDPOINT))
        rows = resp.json()["credit_applications"]
        row = next(r for r in rows if r["id"] == ca.pk)
        self.assertTrue(row["has_deal_structure"])
        self.assertEqual(row["latest_deal_structure_id"], deal.pk)
        self.assertIsNone(row["latest_lender_submission_status"])

    def test_projection_submitted_row_has_pending_status(self) -> None:
        ca = _make_credit_app(self.d, name="Submitted")
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "SB-1")
        )
        lp = _make_lender_program(self.d, name="Projection Bank")
        record_lender_submission(
            dealership=self.d,
            deal_structure=deal,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_PENDING,
        )
        resp = self.client.get(reverse(LIST_ENDPOINT))
        rows = resp.json()["credit_applications"]
        row = next(r for r in rows if r["id"] == ca.pk)
        self.assertEqual(
            row["latest_lender_submission_status"],
            LENDER_SUBMISSION_STATUS_PENDING,
        )

    def test_projection_approved_row_has_approved_status(self) -> None:
        ca = _make_credit_app(self.d, name="Approved")
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "AP-1")
        )
        lp = _make_lender_program(self.d, name="Approved Bank")
        record_lender_submission(
            dealership=self.d,
            deal_structure=deal,
            lender_program=lp,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
        )
        resp = self.client.get(reverse(LIST_ENDPOINT))
        rows = resp.json()["credit_applications"]
        row = next(r for r in rows if r["id"] == ca.pk)
        self.assertEqual(
            row["latest_lender_submission_status"],
            LENDER_SUBMISSION_STATUS_APPROVED,
        )
