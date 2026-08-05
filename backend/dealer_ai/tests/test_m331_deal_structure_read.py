"""Milestone 33 · Increment 1 (SESSION_211) — DealStructure read
endpoint + CA-list M33.1 annotations tests.

Locks the M33.1 backend surface per ``MILESTONE_33_PLANNING.md``
§5.b D1 + D2 + D3 + §5.e M33.1.

One new endpoint gated on
``IsFinanceManagerOrOwnerAtActiveDealership`` (reuses M10.7 class
— zero-drift streak preserved at 37):

- ``GET /admin/deal-structures/<int:pk>/`` — tenant-scoped read.
  404 on unknown or cross-tenant pk (never leaks).

Two new tenant-scoped subquery annotations on the M32.1
``list_credit_applications`` queryset (drive M33.2 UI):

- ``has_deal_structure`` (Boolean) — drives the intake-row chip.
- ``latest_deal_structure_id`` (nullable int) — drives the
  "Open structure" action; deterministic ordering
  ``("-created_at", "-pk")`` disambiguates microsecond-shared
  timestamps.

Coverage:

- Annotation with 0 / 1 / N=3 DealStructures.
- Deterministic tie-break under shared ``created_at``.
- Tenant-scoped subquery guard (cross-tenant row does not leak).
- CA list projection includes both new fields (Incoming + In
  progress cases; null when Incoming).
- Read endpoint permission matrix — five negative cases + two
  positive.
- Read endpoint 200 own-tenant / 404 unknown / 404 cross-tenant.
- Read endpoint projection matches shipped
  ``_project_deal_structure`` shape verbatim.
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
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_SALES_MANAGER,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    list_credit_applications,
    record_deal_structure,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


LIST_ENDPOINT = "dealer_ai:admin-credit-application-list"
READ_ENDPOINT = "dealer_ai:admin-deal-structure-read"


# ---------------------------------------------------------------------------
# Fixture helpers (kept local — M33.1 does not need a shared factory
# module beyond the M32.1 pattern).
# ---------------------------------------------------------------------------


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("40000.00"),
        dealership=dealership,
    )


def _make_credit_app(
    dealership: Dealership,
    *,
    name: str = "Alice",
    income=None,
    existing_debt=None,
) -> CreditApplication:
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
        gross_monthly_income=income,
        existing_monthly_debt=existing_debt,
    )


def _make_deal_structure(
    dealership: Dealership,
    credit_app: CreditApplication,
    vehicle: Vehicle,
    *,
    sale_price: Decimal = Decimal("30000.00"),
    monthly_payment: Decimal = Decimal("500.00"),
) -> DealStructure:
    return record_deal_structure(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=sale_price,
        amount_financed=Decimal("25000.00"),
        apr=Decimal("9.9900"),
        term_months=72,
        monthly_payment=monthly_payment,
    )


def _fandi_client_at(dealership: Dealership, username: str) -> APIClient:
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


# ---------------------------------------------------------------------------
# Service layer — list_credit_applications annotation behavior
# ---------------------------------------------------------------------------


class ListCreditApplicationsAnnotationTests(TestCase):
    """M33.1 D1 + D3 subquery annotations. Both explicitly tenant-
    scoped (subquery filters by ``dealership=dealership``) — belt
    over the model ``clean()`` + service
    ``CrossTenantDealStructureError`` suspenders."""

    def setUp(self) -> None:
        self.d = Dealership.objects.create(slug="m331-a", name="M33.1 A")

    def test_has_deal_structure_false_when_zero_structures(self) -> None:
        _make_credit_app(self.d, name="Incoming")
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].has_deal_structure)
        self.assertIsNone(rows[0].latest_deal_structure_id)

    def test_has_deal_structure_true_when_one_structure(self) -> None:
        ca = _make_credit_app(self.d, name="In-progress")
        vehicle = _make_vehicle(self.d, "M-1")
        deal = _make_deal_structure(self.d, ca, vehicle)
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].has_deal_structure)
        self.assertEqual(rows[0].latest_deal_structure_id, deal.pk)

    def test_latest_deal_structure_id_returns_most_recent_of_n(
        self,
    ) -> None:
        """M-to-1 iteration semantic — CA can carry multiple
        DealStructures (M10.2 domain preserved). Latest by
        ``-created_at`` wins."""
        ca = _make_credit_app(self.d, name="Iter")
        v1 = _make_vehicle(self.d, "IT-1")
        v2 = _make_vehicle(self.d, "IT-2")
        v3 = _make_vehicle(self.d, "IT-3")
        # Force distinct created_at ordering via explicit timestamps.
        d1 = _make_deal_structure(self.d, ca, v1)
        d2 = _make_deal_structure(self.d, ca, v2)
        d3 = _make_deal_structure(self.d, ca, v3)
        # Rewrite created_at so d3 is oldest and d1 is newest — the
        # subquery must pick the newest regardless of pk ordering.
        DealStructure.objects.filter(pk=d1.pk).update(
            created_at=timezone.now() + timedelta(seconds=3)
        )
        DealStructure.objects.filter(pk=d2.pk).update(
            created_at=timezone.now() + timedelta(seconds=1)
        )
        DealStructure.objects.filter(pk=d3.pk).update(
            created_at=timezone.now() - timedelta(seconds=1)
        )
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].has_deal_structure)
        self.assertEqual(rows[0].latest_deal_structure_id, d1.pk)

    def test_deterministic_tie_break_prefers_higher_pk_at_shared_created_at(
        self,
    ) -> None:
        """D3 deterministic ordering ``("-created_at", "-pk")``.
        Two structures with identical ``created_at`` at microsecond
        granularity — subquery selects the higher pk."""
        ca = _make_credit_app(self.d, name="Tie")
        v1 = _make_vehicle(self.d, "T-1")
        v2 = _make_vehicle(self.d, "T-2")
        d1 = _make_deal_structure(self.d, ca, v1)
        d2 = _make_deal_structure(self.d, ca, v2)
        # Force identical timestamps.
        shared_ts = timezone.now()
        DealStructure.objects.filter(pk__in=[d1.pk, d2.pk]).update(
            created_at=shared_ts
        )
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(rows[0].latest_deal_structure_id, max(d1.pk, d2.pk))

    def test_annotation_tenant_scoped_cross_tenant_row_does_not_leak(
        self,
    ) -> None:
        """R5 belt-over-suspenders — the subquery explicitly filters
        by ``dealership=dealership``. If a bug elsewhere ever created
        a cross-tenant DealStructure targeting an own-tenant CA
        (which the model ``clean()`` + service error would already
        refuse), the annotation still must not project it."""
        other = Dealership.objects.create(slug="m331-o", name="Other")
        ca = _make_credit_app(self.d, name="Own")
        cross_vehicle = _make_vehicle(other, "X-1")
        # Bypass service + model clean() via direct ORM create with
        # a mismatched dealership. Represents the "bug elsewhere"
        # hypothetical.
        DealStructure.objects.create(
            dealership=other,
            credit_application=ca,
            vehicle=cross_vehicle,
            sale_price=Decimal("10000.00"),
            amount_financed=Decimal("9000.00"),
            apr=Decimal("8.0000"),
            term_months=60,
            monthly_payment=Decimal("200.00"),
        )
        # Own-tenant list still shows the CA as Incoming — the
        # cross-tenant DealStructure is filtered out by the subquery
        # tenant scope.
        rows = list_credit_applications(dealership=self.d)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].has_deal_structure)
        self.assertIsNone(rows[0].latest_deal_structure_id)

    def test_annotation_composes_with_intake_filter(self) -> None:
        """Annotation composability check — ``intake=True`` filter
        still works alongside the new annotations, and the two
        annotations correctly distinguish structuring status across
        rows that all pass the intake filter (both structured and
        unstructured CAs are pre-contract)."""
        ca_with = _make_credit_app(self.d, name="Both")
        _make_deal_structure(
            self.d, ca_with, _make_vehicle(self.d, "C-1")
        )
        ca_without = _make_credit_app(self.d, name="Solo")

        rows = list_credit_applications(dealership=self.d, intake=True)
        by_pk = {r.pk: r for r in rows}
        # Both survive intake filter — neither has a Contract.
        self.assertEqual(set(by_pk.keys()), {ca_with.pk, ca_without.pk})
        # But the annotation distinguishes structuring status.
        self.assertTrue(by_pk[ca_with.pk].has_deal_structure)
        self.assertFalse(by_pk[ca_without.pk].has_deal_structure)


# ---------------------------------------------------------------------------
# Endpoint layer — CA list projection extension
# ---------------------------------------------------------------------------


class CreditApplicationListProjectionM33Tests(TestCase):
    """§5.b D1 + D3 projection fields on the M32.1 CA list rows."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        self.client = _fandi_client_at(self.d, "m331-proj")

    def test_projection_incoming_row_has_null_latest_and_false_flag(
        self,
    ) -> None:
        _make_credit_app(self.d, name="Empty")
        resp = self.client.get(reverse(LIST_ENDPOINT))
        row = resp.json()["credit_applications"][0]
        self.assertIn("has_deal_structure", row)
        self.assertIn("latest_deal_structure_id", row)
        self.assertFalse(row["has_deal_structure"])
        self.assertIsNone(row["latest_deal_structure_id"])

    def test_projection_in_progress_row_has_latest_id_and_true_flag(
        self,
    ) -> None:
        ca = _make_credit_app(self.d, name="Structured")
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "S-1")
        )
        resp = self.client.get(reverse(LIST_ENDPOINT))
        rows = resp.json()["credit_applications"]
        row = next(r for r in rows if r["id"] == ca.pk)
        self.assertTrue(row["has_deal_structure"])
        self.assertEqual(row["latest_deal_structure_id"], deal.pk)


# ---------------------------------------------------------------------------
# Endpoint layer — GET /admin/deal-structures/<int:pk>/ auth matrix
# ---------------------------------------------------------------------------


class DealStructureReadEndpointAuthTests(TestCase):
    """Same permission class as M10.2 create (``_M101_PERMS``) —
    grants ``f_and_i_manager`` + ``dealer_owner``; blocks everyone
    else. Zero-drift streak preserved (36 → 37 at M33.1 close)."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        ca = _make_credit_app(self.d, name="Auth")
        self.deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "A-1")
        )
        self.url = reverse(READ_ENDPOINT, kwargs={"pk": self.deal.pk})

    def test_unauthenticated_returns_401_or_403(self) -> None:
        resp = APIClient().get(self.url)
        self.assertIn(resp.status_code, (401, 403))

    def test_no_membership_returns_403(self) -> None:
        user = make_user(username="dsr-nomem")
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_advisor_returns_403(self) -> None:
        user = make_user(username="dsr-adv")
        make_membership(user, self.d, ROLE_ADVISOR)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_sales_manager_returns_403(self) -> None:
        # F&I-gated; sales_manager does NOT grant F&I admin access.
        user = make_user(username="dsr-sm")
        make_membership(user, self.d, ROLE_SALES_MANAGER)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_porter_returns_403(self) -> None:
        user = make_user(username="dsr-porter")
        make_membership(user, self.d, ROLE_PORTER)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_f_and_i_manager_returns_200(self) -> None:
        resp = _fandi_client_at(self.d, "dsr-fandi").get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_dealer_owner_returns_200(self) -> None:
        user = make_user(username="dsr-owner")
        make_membership(user, self.d, ROLE_DEALER_OWNER)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Endpoint layer — read behavior + projection shape
# ---------------------------------------------------------------------------


class DealStructureReadEndpointBehaviorTests(TestCase):
    """Happy path + fail-closed cross-tenant/unknown + projection
    shape parity with M10.2 create response."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        self.client = _fandi_client_at(self.d, "dsr-b")

    def test_read_returns_own_tenant_deal_structure(self) -> None:
        ca = _make_credit_app(self.d, name="Own")
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "OT-1")
        )
        resp = self.client.get(
            reverse(READ_ENDPOINT, kwargs={"pk": deal.pk})
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["deal_structure"]
        self.assertEqual(body["id"], deal.pk)
        self.assertEqual(body["credit_application_id"], ca.pk)

    def test_read_returns_404_for_unknown_pk(self) -> None:
        resp = self.client.get(
            reverse(READ_ENDPOINT, kwargs={"pk": 9_999_999})
        )
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["detail"].lower())

    def test_read_returns_404_for_cross_tenant_pk_never_leaks(
        self,
    ) -> None:
        """Cross-tenant → 404 fail-closed. Same shape as M9.1 /
        M10.1 / M10.2. Never leaks existence to unauthorized tenant."""
        other = Dealership.objects.create(slug="dsr-o", name="DSR O")
        other_ca = _make_credit_app(other, name="Other")
        other_deal = _make_deal_structure(
            other, other_ca, _make_vehicle(other, "OD-1")
        )
        resp = self.client.get(
            reverse(READ_ENDPOINT, kwargs={"pk": other_deal.pk})
        )
        self.assertEqual(resp.status_code, 404)

    def test_read_projection_shape_matches_create_response(self) -> None:
        """The read view reuses ``_project_deal_structure`` verbatim
        — the response body under ``deal_structure`` must carry the
        same key set as the M10.2 create response."""
        ca = _make_credit_app(
            self.d,
            name="Shape",
            income=Decimal("5000.00"),
            existing_debt=Decimal("1000.00"),
        )
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "SH-1")
        )
        resp = self.client.get(
            reverse(READ_ENDPOINT, kwargs={"pk": deal.pk})
        )
        body = resp.json()["deal_structure"]
        expected_keys = {
            "id",
            "credit_application_id",
            "vehicle_stock",
            "sale_price",
            "down_payment",
            "trade_allowance",
            "trade_payoff",
            "taxes",
            "fees",
            "amount_financed",
            "apr",
            "term_months",
            "monthly_payment",
            "back_end_products",
            "ltv_pct",
            "pti_pct",
            "dti_pct",
            "created_at",
            "updated_at",
        }
        self.assertEqual(set(body.keys()), expected_keys)
        # Ratios stringified when populated; PTI/DTI populated because
        # this fixture set income + existing_debt on the CA.
        self.assertEqual(body["ltv_pct"], "83.33")
        self.assertIsNotNone(body["pti_pct"])
        self.assertIsNotNone(body["dti_pct"])

    def test_read_projection_null_ratios_when_ca_lacks_income(
        self,
    ) -> None:
        """M10.1-era CA without income captured → PTI/DTI project as
        ``null`` (not zero). NULL-safe contract preserved."""
        ca = _make_credit_app(self.d, name="NoInc")  # no income
        deal = _make_deal_structure(
            self.d, ca, _make_vehicle(self.d, "NI-1")
        )
        resp = self.client.get(
            reverse(READ_ENDPOINT, kwargs={"pk": deal.pk})
        )
        body = resp.json()["deal_structure"]
        # LTV computable (sale_price > 0); PTI + DTI null.
        self.assertIsNotNone(body["ltv_pct"])
        self.assertIsNone(body["pti_pct"])
        self.assertIsNone(body["dti_pct"])
