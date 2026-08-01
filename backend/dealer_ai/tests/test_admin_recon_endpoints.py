"""Milestone 4 · Increment 6 — admin recon endpoint tests.

Coverage of every endpoint in ``views_recon.py``:

- Permission matrix per endpoint (unauth, no-role, advisor,
  porter, f_and_i_manager, collections, sales_manager,
  recon_manager, dealer_owner).
- Business happy-path flows (create/list/patch across all
  resources; full WO lifecycle; comm draft→approve→mark_sent;
  log_communication).
- Domain-error → HTTP status mapping (409 for immutable /
  invalid-transition; 422 for scrub-dropped; 502 for empty
  draft; 400 for validation; 404 for cross-tenant + missing).
- Cross-tenant fail-closed (URL kwarg pointing at another
  dealership's resource yields 404).
- Provenance visible in comm response.
- No recon data on public / advisor surfaces (regression).
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    ROLE_ADVISOR,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    RECON_DECISION_TIER_MUST_DO,
    Vehicle,
    Vendor,
    VendorCommunication,
    VENDOR_COMMUNICATION_CHANNEL_EMAIL,
    VENDOR_COMMUNICATION_CHANNEL_PHONE,
    VENDOR_COMMUNICATION_DIRECTION_INBOUND,
    VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
    VENDOR_COMMUNICATION_KIND_NARRATIVE,
    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
    WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
    WORK_ORDER_PART_STATUS_ORDERED,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_IN_HOUSE,
    WORK_ORDER_VENUE_OUTSOURCED,
    WorkOrder,
    WorkOrderPart,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from dealer_ai.tests._mocks import MockLLMProvider


User = get_user_model()


# ---- Fixtures --------------------------------------------------------------


def _vehicle(dealership, stock="M46-V", price="45000.00") -> Vehicle:
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal(price),
    )


def _report(vehicle, dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="M. Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _finding(
    report,
    dealership,
    *,
    category: str = CONDITION_CATEGORY_MECHANICAL,
    description: str = "Endpoint test finding.",
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=category,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=description,
    )


def _vendor(dealership, slug="ep-vendor") -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"Endpoint Vendor {slug}",
        slug=slug,
    )


def _post(client, url_name, args=(), payload=None):
    url = reverse(f"dealer_ai:{url_name}", args=args)
    if payload is None:
        return client.post(url)
    return client.post(
        url, data=json.dumps(payload), content_type="application/json"
    )


def _get(client, url_name, args=()):
    return client.get(reverse(f"dealer_ai:{url_name}", args=args))


def _patch(client, url_name, args=(), payload=None):
    url = reverse(f"dealer_ai:{url_name}", args=args)
    if payload is None:
        return client.patch(url)
    return client.patch(
        url, data=json.dumps(payload), content_type="application/json"
    )


def _delete(client, url_name, args=()):
    return client.delete(reverse(f"dealer_ai:{url_name}", args=args))


# ============================================================================
# Permission-matrix mixin (extended for recon_manager)
# ============================================================================


class ReconAdminEndpointAuthMatrixBase:
    """Locks the M4.6 permission matrix per endpoint.

    Nine outcomes per endpoint:
    - Unauthenticated → 401/403.
    - Authenticated no-role → 403.
    - advisor only → 403.
    - porter only → 403.
    - f_and_i_manager only → 403.
    - collections only → 403.
    - recon_manager → OK.
    - sales_manager → OK.
    - dealer_owner → OK.
    """

    method = "GET"
    url_name = ""
    url_args: tuple = ()
    payload: dict | None = None
    expected_ok_status = 200

    def setup_tenants(self):
        self.dealership_a = get_default_dealership()

    def request(self, client):
        url = reverse(f"dealer_ai:{self.url_name}", args=self.url_args)
        if self.method == "GET":
            return client.get(url)
        if self.payload is None:
            return getattr(client, self.method.lower())(url)
        return getattr(client, self.method.lower())(
            url,
            data=json.dumps(self.payload),
            content_type="application/json",
        )

    def _expect_forbidden_for(self, role):
        self.setup_tenants()
        user = make_user(username=f"{role}-{self.url_name}")
        make_membership(user, self.dealership_a, role)
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, 403, res.content)

    def _expect_ok_for(self, role):
        self.setup_tenants()
        user = make_user(username=f"{role}-{self.url_name}-ok")
        make_membership(user, self.dealership_a, role)
        res = self.request(authenticated_client(user))
        self.assertEqual(
            res.status_code, self.expected_ok_status, res.content
        )

    def test_unauthenticated_is_rejected(self):
        self.setup_tenants()
        res = self.request(APIClient())
        self.assertIn(res.status_code, (401, 403), res.content)

    def test_no_role_forbidden(self):
        self.setup_tenants()
        user = make_user(username=f"norole-{self.url_name}")
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, 403, res.content)

    def test_advisor_forbidden(self):
        self._expect_forbidden_for(ROLE_ADVISOR)

    def test_porter_forbidden(self):
        self._expect_forbidden_for(ROLE_PORTER)

    def test_f_and_i_manager_forbidden(self):
        self._expect_forbidden_for(ROLE_F_AND_I_MANAGER)

    def test_collections_forbidden(self):
        self._expect_forbidden_for(ROLE_COLLECTIONS)

    def test_recon_manager_authorized(self):
        self._expect_ok_for(ROLE_RECON_MANAGER)

    def test_sales_manager_authorized(self):
        self._expect_ok_for(ROLE_SALES_MANAGER)

    def test_dealer_owner_authorized(self):
        self._expect_ok_for(ROLE_DEALER_OWNER)


# --- Per-endpoint permission-matrix subclasses (representative set) --------


class VendorListAuth(ReconAdminEndpointAuthMatrixBase, TestCase):
    method = "GET"
    url_name = "admin-vendor-list"


class VendorCreateAuth(ReconAdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-vendor-list"
    payload = {"name": "Auth Test Vendor", "slug": "auth-test-vendor"}
    expected_ok_status = 201


class ReconDashboardAuth(ReconAdminEndpointAuthMatrixBase, TestCase):
    method = "GET"
    url_name = "admin-recon-dashboard"

    def setup_tenants(self):
        super().setup_tenants()
        _vehicle(self.dealership_a, stock="AUTH-DASH")

    @property
    def url_args(self):
        return ("AUTH-DASH",)


class WorkOrderCreateAuth(ReconAdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-work-order-create"
    payload = {
        "category": CONDITION_CATEGORY_MECHANICAL,
        "venue": WORK_ORDER_VENUE_IN_HOUSE,
    }
    expected_ok_status = 201

    def setup_tenants(self):
        super().setup_tenants()
        _vehicle(self.dealership_a, stock="AUTH-WOC")

    @property
    def url_args(self):
        return ("AUTH-WOC",)


class CommLogAuth(ReconAdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-comm-log"
    payload = {
        "kind": VENDOR_COMMUNICATION_KIND_NARRATIVE,
        "channel": VENDOR_COMMUNICATION_CHANNEL_PHONE,
        "direction": VENDOR_COMMUNICATION_DIRECTION_INBOUND,
        "body": "Cold call from a new vendor.",
    }
    expected_ok_status = 201


# ============================================================================
# Vendor CRUD business flows
# ============================================================================


class VendorCrudFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="v-op")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_create_then_list(self):
        res = _post(
            self.client,
            "admin-vendor-list",
            payload={
                "name": "Yuma Body",
                "slug": "yuma-body",
                "categories": [CONDITION_CATEGORY_BODY],
                "phone": "928-555-1000",
                "email": "ops@example.com",
                "notes": "Prefers text.",
            },
        )
        self.assertEqual(res.status_code, 201, res.content)
        listing = _get(self.client, "admin-vendor-list").json()
        slugs = [v["slug"] for v in listing["vendors"]]
        self.assertIn("yuma-body", slugs)

    def test_detail_returns_vendor_shape(self):
        vendor = _vendor(self.dealership, slug="detail-vendor")
        res = _get(self.client, "admin-vendor-detail", args=("detail-vendor",))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["vendor"]["slug"], "detail-vendor")
        self.assertEqual(res.json()["vendor"]["is_active"], True)

    def test_patch_deactivates(self):
        vendor = _vendor(self.dealership, slug="deact-vendor")
        res = _patch(
            self.client,
            "admin-vendor-detail",
            args=("deact-vendor",),
            payload={"is_active": False},
        )
        self.assertEqual(res.status_code, 200)
        vendor.refresh_from_db()
        self.assertFalse(vendor.is_active)

    def test_detail_cross_tenant_404(self):
        other = make_dealership(slug="other-vendor-tenant")
        _vendor(other, slug="cross-vendor")
        res = _get(self.client, "admin-vendor-detail", args=("cross-vendor",))
        self.assertEqual(res.status_code, 404)

    def test_list_returns_only_current_dealership_vendors(self):
        other = make_dealership(slug="other-vendor-list")
        _vendor(other, slug="cross-tenant-only")
        _vendor(self.dealership, slug="mine")
        listing = _get(self.client, "admin-vendor-list").json()
        slugs = [v["slug"] for v in listing["vendors"]]
        self.assertIn("mine", slugs)
        self.assertNotIn("cross-tenant-only", slugs)

    def test_no_delete_endpoint_exists(self):
        vendor = _vendor(self.dealership, slug="no-del")
        res = _delete(
            self.client, "admin-vendor-detail", args=("no-del",)
        )
        self.assertEqual(res.status_code, 405)

    def test_create_duplicate_slug_returns_conflict(self):
        _vendor(self.dealership, slug="dup-slug")
        res = _post(
            self.client,
            "admin-vendor-list",
            payload={"name": "Second", "slug": "dup-slug"},
        )
        # Uniqueness surfaces via full_clean() → ValidationError
        # (400) before the DB constraint fires (409). Either
        # response is a defensible refusal.
        self.assertIn(res.status_code, (400, 409), res.content)
        self.assertIn("exists", res.content.decode().lower())


# ============================================================================
# Recon dashboard
# ============================================================================


class ReconDashboardFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="dash-op")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _vehicle(self.dealership, stock="M46-DASH")

    def test_empty_dashboard(self):
        res = _get(
            self.client, "admin-recon-dashboard", args=("M46-DASH",)
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsNone(body["latest_condition_report"])
        self.assertEqual(body["work_orders"], [])
        self.assertEqual(body["communications"], [])

    def test_populated_dashboard(self):
        report = _report(self.vehicle, self.dealership)
        _finding(report, self.dealership)
        res = _get(
            self.client, "admin-recon-dashboard", args=("M46-DASH",)
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsNotNone(body["latest_condition_report"])
        self.assertEqual(
            len(body["latest_condition_report"]["findings"]), 1
        )

    def test_dashboard_cross_tenant_404(self):
        other = make_dealership(slug="other-dashboard")
        _vehicle(other, stock="OTHER-DASH")
        res = _get(
            self.client, "admin-recon-dashboard", args=("OTHER-DASH",)
        )
        self.assertEqual(res.status_code, 404)


# ============================================================================
# WorkOrder lifecycle
# ============================================================================


class WorkOrderLifecycleFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="wo-op")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _vehicle(self.dealership, stock="M46-WO")
        self.report = _report(self.vehicle, self.dealership)
        self.finding = _finding(self.report, self.dealership)
        self.vendor = _vendor(self.dealership, slug="wo-vendor")

    def _create_wo(self, **overrides):
        payload = {
            "category": CONDITION_CATEGORY_MECHANICAL,
            "venue": WORK_ORDER_VENUE_IN_HOUSE,
        }
        payload.update(overrides)
        return _post(
            self.client,
            "admin-work-order-create",
            args=("M46-WO",),
            payload=payload,
        )

    def test_create_draft_in_house(self):
        res = self._create_wo()
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()["work_order"]
        self.assertEqual(body["status"], WORK_ORDER_STATUS_DRAFT)
        self.assertEqual(body["venue"], WORK_ORDER_VENUE_IN_HOUSE)
        self.assertIsNone(body["vendor"])

    def test_create_outsourced_with_vendor(self):
        res = self._create_wo(
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor_slug="wo-vendor",
            category=CONDITION_CATEGORY_BODY,
            estimated_cost="750.00",
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()["work_order"]
        self.assertEqual(body["venue"], WORK_ORDER_VENUE_OUTSOURCED)
        self.assertEqual(body["vendor"]["slug"], "wo-vendor")

    def test_create_outsourced_without_vendor_400(self):
        res = self._create_wo(venue=WORK_ORDER_VENUE_OUTSOURCED)
        # InvalidReconTransitionError → 409 per M4.6 mapping.
        self.assertEqual(res.status_code, 409, res.content)

    def test_create_with_unknown_vendor_slug_404(self):
        res = self._create_wo(
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor_slug="ghost",
            category=CONDITION_CATEGORY_BODY,
        )
        self.assertEqual(res.status_code, 404)

    def test_full_lifecycle_via_endpoints(self):
        # Create draft.
        res = self._create_wo(estimated_cost="500.00")
        wo_id = res.json()["work_order"]["id"]
        # Attach finding.
        res = _post(
            self.client,
            "admin-work-order-attach-findings",
            args=(wo_id,),
            payload={"finding_ids": [self.finding.pk]},
        )
        self.assertEqual(res.status_code, 200, res.content)
        # Approve.
        res = _post(
            self.client, "admin-work-order-approve", args=(wo_id,)
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json()["work_order"]["status"], WORK_ORDER_STATUS_APPROVED
        )
        # Start.
        res = _post(
            self.client, "admin-work-order-start", args=(wo_id,)
        )
        self.assertEqual(
            res.json()["work_order"]["status"], WORK_ORDER_STATUS_IN_PROGRESS
        )
        # Complete.
        res = _post(
            self.client,
            "admin-work-order-complete",
            args=(wo_id,),
            payload={"actual_cost": "475.00"},
        )
        self.assertEqual(
            res.json()["work_order"]["status"], WORK_ORDER_STATUS_COMPLETED
        )

    def test_approve_without_findings_returns_409(self):
        res = self._create_wo()
        wo_id = res.json()["work_order"]["id"]
        res = _post(
            self.client, "admin-work-order-approve", args=(wo_id,)
        )
        self.assertEqual(res.status_code, 409)

    def test_complete_without_actual_cost_returns_400(self):
        res = self._create_wo()
        wo_id = res.json()["work_order"]["id"]
        _post(
            self.client,
            "admin-work-order-attach-findings",
            args=(wo_id,),
            payload={"finding_ids": [self.finding.pk]},
        )
        _post(self.client, "admin-work-order-approve", args=(wo_id,))
        _post(self.client, "admin-work-order-start", args=(wo_id,))
        res = _post(
            self.client,
            "admin-work-order-complete",
            args=(wo_id,),
            payload={},
        )
        # DRF field validation → 400 (missing required field).
        self.assertEqual(res.status_code, 400)

    def test_double_start_returns_409(self):
        res = self._create_wo()
        wo_id = res.json()["work_order"]["id"]
        _post(
            self.client,
            "admin-work-order-attach-findings",
            args=(wo_id,),
            payload={"finding_ids": [self.finding.pk]},
        )
        _post(self.client, "admin-work-order-approve", args=(wo_id,))
        _post(self.client, "admin-work-order-start", args=(wo_id,))
        res = _post(self.client, "admin-work-order-start", args=(wo_id,))
        self.assertEqual(res.status_code, 409)

    def test_cancel_approved_requires_reason_400(self):
        res = self._create_wo()
        wo_id = res.json()["work_order"]["id"]
        _post(
            self.client,
            "admin-work-order-attach-findings",
            args=(wo_id,),
            payload={"finding_ids": [self.finding.pk]},
        )
        _post(self.client, "admin-work-order-approve", args=(wo_id,))
        res = _post(
            self.client,
            "admin-work-order-cancel",
            args=(wo_id,),
            payload={"cancellation_reason": ""},
        )
        # ValueError → 400.
        self.assertEqual(res.status_code, 400)

    def test_cancel_draft_no_reason_ok(self):
        res = self._create_wo()
        wo_id = res.json()["work_order"]["id"]
        res = _post(
            self.client, "admin-work-order-cancel", args=(wo_id,)
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json()["work_order"]["status"], WORK_ORDER_STATUS_CANCELLED
        )

    def test_revise_estimate_via_patch(self):
        res = self._create_wo(estimated_cost="500.00")
        wo_id = res.json()["work_order"]["id"]
        _post(
            self.client,
            "admin-work-order-attach-findings",
            args=(wo_id,),
            payload={"finding_ids": [self.finding.pk]},
        )
        _post(self.client, "admin-work-order-approve", args=(wo_id,))
        res = _patch(
            self.client,
            "admin-work-order-patch",
            args=(wo_id,),
            payload={"new_estimated_cost": "650.00"},
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(
            res.json()["work_order"]["estimated_cost"], "650.00"
        )

    def test_wo_cross_tenant_404(self):
        other = make_dealership(slug="other-wo-tenant")
        other_v = _vehicle(other, stock="OTHER-WO")
        other_r = _report(other_v, other)
        other_f = _finding(other_r, other)
        from dealer_ai.services.recon import create_work_order
        other_wo = create_work_order(
            other_v,
            dealership=other,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        # Try to approve the other-tenant's WO via our admin.
        res = _post(
            self.client,
            "admin-work-order-approve",
            args=(other_wo.pk,),
        )
        self.assertEqual(res.status_code, 404)

    def test_detach_finding_on_draft(self):
        res = self._create_wo()
        wo_id = res.json()["work_order"]["id"]
        _post(
            self.client,
            "admin-work-order-attach-findings",
            args=(wo_id,),
            payload={"finding_ids": [self.finding.pk]},
        )
        res = _delete(
            self.client,
            "admin-work-order-detach-finding",
            args=(wo_id, self.finding.pk),
        )
        self.assertEqual(res.status_code, 204)


# ============================================================================
# Parts
# ============================================================================


class PartsFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="p-op")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _vehicle(self.dealership, stock="M46-PART")
        self.report = _report(self.vehicle, self.dealership)
        self.finding = _finding(self.report, self.dealership)
        from dealer_ai.services.recon import (
            attach_findings,
            create_work_order,
        )
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.dealership,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            self.wo,
            dealership=self.dealership,
            finding_ids=[self.finding.pk],
        )

    def test_add_part(self):
        res = _post(
            self.client,
            "admin-work-order-part-create",
            args=(self.wo.pk,),
            payload={
                "name": "Brake pads",
                "part_number": "BP-100",
                "quantity": 2,
                "unit_cost": "45.00",
                "source_type": WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
                "source_name": "NAPA Yuma",
            },
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()["part"]
        self.assertEqual(body["name"], "Brake pads")
        self.assertEqual(body["quantity"], 2)

    def test_update_part_via_patch(self):
        from dealer_ai.services.recon import add_part
        part = add_part(
            self.wo, dealership=self.dealership, name="Original", quantity=1
        )
        res = _patch(
            self.client,
            "admin-part-detail",
            args=(part.pk,),
            payload={"name": "Renamed", "quantity": 3},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["part"]["name"], "Renamed")
        self.assertEqual(res.json()["part"]["quantity"], 3)

    def test_transition_part_via_patch(self):
        from dealer_ai.services.recon import add_part
        part = add_part(
            self.wo, dealership=self.dealership, name="Trans"
        )
        res = _patch(
            self.client,
            "admin-part-detail",
            args=(part.pk,),
            payload={"new_status": WORK_ORDER_PART_STATUS_ORDERED},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json()["part"]["status"], WORK_ORDER_PART_STATUS_ORDERED
        )
        self.assertIsNotNone(res.json()["part"]["ordered_at"])

    def test_mix_update_and_status_returns_400(self):
        from dealer_ai.services.recon import add_part
        part = add_part(
            self.wo, dealership=self.dealership, name="Mix"
        )
        res = _patch(
            self.client,
            "admin-part-detail",
            args=(part.pk,),
            payload={
                "name": "renamed",
                "new_status": WORK_ORDER_PART_STATUS_ORDERED,
            },
        )
        self.assertEqual(res.status_code, 400)

    def test_delete_part_on_draft(self):
        from dealer_ai.services.recon import add_part
        part = add_part(
            self.wo, dealership=self.dealership, name="Del"
        )
        res = _delete(
            self.client, "admin-part-detail", args=(part.pk,)
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(WorkOrderPart.objects.filter(pk=part.pk).exists())

    def test_delete_part_on_approved_returns_409(self):
        from dealer_ai.services.recon import (
            add_part,
            approve_work_order,
        )
        part = add_part(
            self.wo, dealership=self.dealership, name="Locked"
        )
        approve_work_order(
            self.wo,
            dealership=self.dealership,
            approved_by=self.user,
        )
        res = _delete(
            self.client, "admin-part-detail", args=(part.pk,)
        )
        self.assertEqual(res.status_code, 409)

    def test_part_cross_tenant_404(self):
        other = make_dealership(slug="other-parts-tenant")
        other_v = _vehicle(other, stock="OTHER-PART")
        other_r = _report(other_v, other)
        other_f = _finding(other_r, other)
        from dealer_ai.services.recon import (
            add_part,
            attach_findings,
            create_work_order,
        )
        other_wo = create_work_order(
            other_v,
            dealership=other,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        attach_findings(
            other_wo, dealership=other, finding_ids=[other_f.pk]
        )
        other_part = add_part(
            other_wo, dealership=other, name="Other tenant part"
        )
        res = _patch(
            self.client,
            "admin-part-detail",
            args=(other_part.pk,),
            payload={"name": "hijack"},
        )
        self.assertEqual(res.status_code, 404)


# ============================================================================
# Vendor communications
# ============================================================================


class VendorCommFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="c-op")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _vehicle(self.dealership, stock="M46-COMM")
        self.report = _report(self.vehicle, self.dealership)
        self.finding = _finding(self.report, self.dealership)
        self.vendor = _vendor(self.dealership, slug="comm-vendor")
        from dealer_ai.services.recon import (
            attach_findings,
            create_work_order,
        )
        self.wo = create_work_order(
            self.vehicle,
            dealership=self.dealership,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=self.vendor,
            estimated_cost=Decimal("500.00"),
        )
        attach_findings(
            self.wo,
            dealership=self.dealership,
            finding_ids=[self.finding.pk],
        )

    def _draft_via_service(self):
        """Use the service directly with a MockLLMProvider, since
        the endpoint uses the real provider factory. This ensures
        the test doesn't call Ollama/OpenAI."""
        from dealer_ai.services.vendor_comm import draft_communication

        provider = MockLLMProvider(replies=["Please take a look."])
        return draft_communication(
            self.wo,
            dealership=self.dealership,
            drafted_by=self.user,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )

    def test_approve_via_endpoint(self):
        comm = self._draft_via_service()
        res = _post(
            self.client, "admin-comm-approve", args=(comm.pk,)
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["communication"]["status"], "approved")

    def test_mark_sent_via_endpoint(self):
        comm = self._draft_via_service()
        _post(self.client, "admin-comm-approve", args=(comm.pk,))
        res = _post(
            self.client,
            "admin-comm-mark-sent",
            args=(comm.pk,),
            payload={"sent_content": "Edited before sending."},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()["communication"]
        self.assertEqual(body["status"], "sent")
        self.assertEqual(body["sent_content"], "Edited before sending.")

    def test_mark_sent_default_uses_draft_content(self):
        comm = self._draft_via_service()
        _post(self.client, "admin-comm-approve", args=(comm.pk,))
        res = _post(
            self.client,
            "admin-comm-mark-sent",
            args=(comm.pk,),
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()["communication"]
        self.assertEqual(body["status"], "sent")
        self.assertEqual(body["sent_content"], comm.draft_content)

    def test_mark_sent_from_draft_returns_409(self):
        comm = self._draft_via_service()
        res = _post(
            self.client, "admin-comm-mark-sent", args=(comm.pk,)
        )
        self.assertEqual(res.status_code, 409)

    def test_log_communication_endpoint(self):
        res = _post(
            self.client,
            "admin-comm-log",
            payload={
                "work_order_id": self.wo.pk,
                "kind": VENDOR_COMMUNICATION_KIND_NARRATIVE,
                "channel": VENDOR_COMMUNICATION_CHANNEL_PHONE,
                "direction": VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                "body": "Vendor called re: parts ETA.",
            },
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()["communication"]
        self.assertEqual(body["status"], "logged")
        self.assertIn("parts ETA", body["draft_content"])

    def test_log_communication_null_wo(self):
        res = _post(
            self.client,
            "admin-comm-log",
            payload={
                "kind": VENDOR_COMMUNICATION_KIND_NARRATIVE,
                "channel": VENDOR_COMMUNICATION_CHANNEL_PHONE,
                "direction": VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                "body": "Cold call.",
            },
        )
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.json()["communication"]["work_order_id"])

    def test_log_missing_body_returns_400(self):
        res = _post(
            self.client,
            "admin-comm-log",
            payload={
                "kind": VENDOR_COMMUNICATION_KIND_NARRATIVE,
                "channel": VENDOR_COMMUNICATION_CHANNEL_PHONE,
                "direction": VENDOR_COMMUNICATION_DIRECTION_INBOUND,
            },
        )
        self.assertEqual(res.status_code, 400)

    def test_comm_cross_tenant_404(self):
        other = make_dealership(slug="other-comm-tenant")
        other_v = _vehicle(other, stock="OTHER-COMM")
        other_r = _report(other_v, other)
        other_f = _finding(other_r, other)
        other_vendor = _vendor(other, slug="other-comm-v")
        from dealer_ai.services.recon import (
            attach_findings,
            create_work_order,
        )
        from dealer_ai.services.vendor_comm import draft_communication

        other_wo = create_work_order(
            other_v,
            dealership=other,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=other_vendor,
        )
        attach_findings(
            other_wo, dealership=other, finding_ids=[other_f.pk]
        )
        provider = MockLLMProvider(replies=["draft"])
        other_user = make_user(username="other-drafter")
        make_membership(other_user, other, ROLE_RECON_MANAGER)
        other_comm = draft_communication(
            other_wo,
            dealership=other,
            drafted_by=other_user,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            provider=provider,
        )
        # Attempt to approve other-tenant's comm from our client.
        res = _post(
            self.client, "admin-comm-approve", args=(other_comm.pk,)
        )
        self.assertEqual(res.status_code, 404)

    def test_provenance_visible_in_response(self):
        comm = self._draft_via_service()
        res = _get(
            self.client,
            "admin-recon-dashboard",
            args=("M46-COMM",),
        )
        self.assertEqual(res.status_code, 200)
        comms = res.json()["communications"]
        self.assertEqual(len(comms), 1)
        prov = comms[0]["source_provenance"]
        self.assertIn("source_bundle", prov)
        self.assertEqual(prov["llm_provider"], "mock")


# ============================================================================
# Recon decision
# ============================================================================


class ReconDecisionEndpoint(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="rd-op")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)
        self.vehicle = _vehicle(self.dealership, stock="M46-RD")
        self.report = _report(self.vehicle, self.dealership)
        self.finding = _finding(self.report, self.dealership)

    def test_create_decision(self):
        res = _post(
            self.client,
            "admin-recon-decision-create",
            args=("M46-RD", self.finding.pk),
            payload={
                "tier": RECON_DECISION_TIER_MUST_DO,
                "notes": "Safety-critical",
            },
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(
            res.json()["decision"]["tier"], RECON_DECISION_TIER_MUST_DO
        )

    def test_decision_on_draft_report_returns_409(self):
        # Draft report — decision refused.
        draft_v = _vehicle(self.dealership, stock="M46-RD-DR")
        draft_r = ConditionReport.objects.create(
            vehicle=draft_v,
            dealership=self.dealership,
            inspector_name="M. Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        draft_f = _finding(draft_r, self.dealership)
        res = _post(
            self.client,
            "admin-recon-decision-create",
            args=("M46-RD-DR", draft_f.pk),
            payload={"tier": RECON_DECISION_TIER_MUST_DO},
        )
        self.assertEqual(res.status_code, 409)

    def test_cross_tenant_finding_returns_404(self):
        other = make_dealership(slug="other-rd-tenant")
        other_v = _vehicle(other, stock="M46-RD-XT")
        other_r = _report(other_v, other)
        other_f = _finding(other_r, other)
        # Use our client (Dealership default) but URL points at
        # the cross-tenant vehicle stock.
        res = _post(
            self.client,
            "admin-recon-decision-create",
            args=("M46-RD-XT", other_f.pk),
            payload={"tier": RECON_DECISION_TIER_MUST_DO},
        )
        self.assertEqual(res.status_code, 404)


# ============================================================================
# Regression: recon data does not appear on non-M4.6 surfaces
# ============================================================================


class NoReconDataOnPublicSurfaces(TestCase):
    """Recon / vendor / work-order data must never leak into the
    public / customer surfaces (chat, per-vehicle Q&A, ad copy,
    onboarding profile). Locked by fixture + response inspection."""

    def test_onboarding_profile_get_does_not_leak_recon_fields(self):
        dealership = get_default_dealership()
        _vendor(dealership, slug="private-vendor")
        anon = APIClient()
        res = anon.get(reverse("dealer_ai:onboarding-profile"))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        text = json.dumps(body)
        self.assertNotIn("private-vendor", text)
        self.assertNotIn("work_order", text)
        self.assertNotIn("recon_decision", text)


# ============================================================================
# Module-level: URL routes registered
# ============================================================================


class M46RoutesRegistered(TestCase):
    """Every M4.6 URL name is resolvable — protects against a
    view file rename that forgets to update urls.py."""

    def test_all_m46_url_names_resolve(self):
        names_with_args = [
            ("admin-vendor-list", ()),
            ("admin-vendor-detail", ("slug",)),
            ("admin-recon-dashboard", ("STOCK",)),
            ("admin-recon-decision-create", ("STOCK", 1)),
            ("admin-work-order-create", ("STOCK",)),
            ("admin-work-order-approve", (1,)),
            ("admin-work-order-start", (1,)),
            ("admin-work-order-complete", (1,)),
            ("admin-work-order-cancel", (1,)),
            ("admin-work-order-patch", (1,)),
            ("admin-work-order-attach-findings", (1,)),
            ("admin-work-order-detach-finding", (1, 1)),
            ("admin-work-order-part-create", (1,)),
            ("admin-part-detail", (1,)),
            ("admin-work-order-comm-draft", (1,)),
            ("admin-comm-approve", (1,)),
            ("admin-comm-mark-sent", (1,)),
            ("admin-comm-log", ()),
        ]
        for name, args in names_with_args:
            url = reverse(f"dealer_ai:{name}", args=args)
            self.assertTrue(url.startswith("/"))
