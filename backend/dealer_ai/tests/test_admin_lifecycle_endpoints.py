"""Milestone 5 · Increment 4 (SESSION_078) — admin lifecycle endpoint tests.

Coverage of every endpoint in ``views_lifecycle.py``:

- Permission matrix per endpoint (unauth, no-role, advisor,
  porter, f_and_i_manager, collections, sales_manager,
  recon_manager, dealer_owner).
- Business happy-path flows: dashboard shape, manual transition,
  rule-suggested transition accept.
- Domain-error → HTTP mapping (SESSION_075 §0.a item 5 —
  distinct classes, distinct status codes):
  - CrossTenantLifecycleError → 404.
  - InvalidStageTransitionError → 409.
  - UnauthorizedStageTransitionError → 403 (recon_manager
    refused for commercial/disposition targets — per-transition
    role authority enforced at service layer, not DRF).
  - StageAlreadyCurrentError → 409.
  - ValueError (unknown to_stage / trigger) → 400.
- Cross-tenant fail-closed (URL kwarg pointing at another
  dealership's vehicle yields 404).
- Rule-accept endpoint re-evaluates suggestions at apply time
  and refuses (409) when the predicate has flipped.
- Rule-accept refuses (409) when the matched suggestion has
  unmet_prerequisites (`photography_to_listing` pending M6).
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
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    ROLE_ADVISOR,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_PHOTOGRAPHY,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    VEHICLE_STAGE_WHOLESALE_OUT,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.services.vehicle_lifecycle import (
    advance_stage,
    ensure_current_stage,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


User = get_user_model()


# ---- Fixtures --------------------------------------------------------------


def _vehicle(dealership, stock="M54-V", price="45000.00") -> Vehicle:
    v = Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal(price),
    )
    # M5.5 test-only auto-bootstrap; wipe so M5.4 endpoint tests
    # observe the has_stage=False / auth-matrix defaults explicitly.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


def _completed_report_with_required_finding(vehicle, dealership):
    report = ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="M. Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )
    ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="Endpoint fixture — required finding.",
    )
    return report


def _post(client, url_name, args=(), payload=None):
    url = reverse(f"dealer_ai:{url_name}", args=args)
    if payload is None:
        return client.post(url)
    return client.post(
        url, data=json.dumps(payload), content_type="application/json"
    )


def _get(client, url_name, args=()):
    return client.get(reverse(f"dealer_ai:{url_name}", args=args))


# ============================================================================
# Permission-matrix mixin (reused shape from M4.6)
# ============================================================================


class LifecycleEndpointAuthMatrixBase:
    """Locks the M5.4 permission matrix per endpoint.

    Nine outcomes per endpoint (same shape as M4.6):
    - Unauthenticated → 401/403.
    - Authenticated no-role → 403.
    - advisor only → 403.
    - porter only → 403.
    - f_and_i_manager only → 403.
    - collections only → 403.
    - recon_manager → OK (dashboard + retail-prep transitions
      succeed; commercial transitions still refused at the
      service layer with 403).
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


# --- Per-endpoint permission-matrix subclasses -----------------------------


class LifecycleDashboardAuth(LifecycleEndpointAuthMatrixBase, TestCase):
    method = "GET"
    url_name = "admin-lifecycle-dashboard"

    def setup_tenants(self):
        super().setup_tenants()
        _vehicle(self.dealership_a, stock="AUTH-DASH-M54")

    @property
    def url_args(self):
        return ("AUTH-DASH-M54",)


class LifecycleManualTransitionAuth(LifecycleEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-lifecycle-manual-transition"
    payload = {"to_stage": VEHICLE_STAGE_INSPECTION, "notes": "auth test"}
    expected_ok_status = 200

    def setup_tenants(self):
        super().setup_tenants()
        v = _vehicle(self.dealership_a, stock="AUTH-TRANS-M54")
        ensure_current_stage(
            v,
            dealership=self.dealership_a,
            initial_stage=VEHICLE_STAGE_INCOMING,
        )

    @property
    def url_args(self):
        return ("AUTH-TRANS-M54",)


class LifecycleRuleTransitionAuth(LifecycleEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-lifecycle-rule-transition"
    payload = {"rule_name": "inspection_to_recon"}
    expected_ok_status = 200

    def setup_tenants(self):
        super().setup_tenants()
        v = _vehicle(self.dealership_a, stock="AUTH-RULE-M54")
        ensure_current_stage(
            v,
            dealership=self.dealership_a,
            initial_stage=VEHICLE_STAGE_INSPECTION,
        )
        _completed_report_with_required_finding(v, self.dealership_a)

    @property
    def url_args(self):
        return ("AUTH-RULE-M54",)


# ============================================================================
# Dashboard business flows
# ============================================================================


class LifecycleDashboardShape(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.user = make_user(username="dash-user")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client_ = authenticated_client(self.user)

    def test_returns_has_stage_false_for_unseeded_vehicle(self):
        v = _vehicle(self.dealership, stock="M54-DASH-UNSEEDED")
        res = _get(self.client_, "admin-lifecycle-dashboard", (v.stock_number,))
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["stock_number"], "M54-DASH-UNSEEDED")
        self.assertFalse(body["has_stage"])
        self.assertIsNone(body["current_stage"])
        self.assertEqual(body["recent_events"], [])
        self.assertEqual(body["suggested_transitions"], [])
        self.assertIsNone(body["hold_reserved_return_target"])

    def test_returns_current_stage_and_events_for_seeded_vehicle(self):
        v = _vehicle(self.dealership, stock="M54-DASH-SEEDED")
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_INSPECTION,
        )
        res = _get(self.client_, "admin-lifecycle-dashboard", (v.stock_number,))
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertTrue(body["has_stage"])
        self.assertEqual(body["current_stage"]["value"], "inspection")
        self.assertEqual(body["current_stage"]["label"], "Inspection")
        self.assertEqual(body["current_stage"]["trigger"], "bootstrap")
        self.assertEqual(len(body["recent_events"]), 1)
        self.assertIsNone(body["recent_events"][0]["from_stage"])
        self.assertEqual(body["recent_events"][0]["to_stage"], "inspection")

    def test_returns_suggested_transitions_at_inspection_with_actionable_findings(self):
        v = _vehicle(self.dealership, stock="M54-DASH-SUGGEST")
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_INSPECTION,
        )
        _completed_report_with_required_finding(v, self.dealership)
        res = _get(self.client_, "admin-lifecycle-dashboard", (v.stock_number,))
        body = res.json()
        self.assertEqual(len(body["suggested_transitions"]), 1)
        self.assertEqual(
            body["suggested_transitions"][0]["to_stage"], "recon"
        )
        self.assertEqual(
            body["suggested_transitions"][0]["rule_name"],
            "inspection_to_recon",
        )
        self.assertEqual(
            body["suggested_transitions"][0]["unmet_prerequisites"], []
        )

    def test_returns_photography_prerequisite_at_photography_stage(self):
        v = _vehicle(self.dealership, stock="M54-DASH-PHOTO")
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_PHOTOGRAPHY,
        )
        res = _get(self.client_, "admin-lifecycle-dashboard", (v.stock_number,))
        body = res.json()
        self.assertEqual(len(body["suggested_transitions"]), 1)
        suggestion = body["suggested_transitions"][0]
        self.assertEqual(suggestion["to_stage"], "listing")
        self.assertEqual(suggestion["rule_name"], "photography_to_listing")
        self.assertGreater(len(suggestion["unmet_prerequisites"]), 0)

    def test_returns_hold_reserved_return_target_when_applicable(self):
        v = _vehicle(self.dealership, stock="M54-DASH-HOLD")
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        actor = self.user  # sales_manager
        advance_stage(
            v,
            dealership=self.dealership,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            actor=actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        res = _get(self.client_, "admin-lifecycle-dashboard", (v.stock_number,))
        body = res.json()
        self.assertEqual(
            body["hold_reserved_return_target"], VEHICLE_STAGE_FRONTLINE
        )

    def test_cross_tenant_returns_404(self):
        other = Dealership.objects.create(name="Other", slug="other-dash-m54")
        v = _vehicle(other, stock="M54-DASH-XT")
        # Client is authenticated at the default dealership; the
        # vehicle belongs to `other`. The queryset scoping fails
        # closed.
        res = _get(self.client_, "admin-lifecycle-dashboard", (v.stock_number,))
        self.assertEqual(res.status_code, 404, res.content)

    def test_missing_stock_number_returns_404(self):
        res = _get(
            self.client_, "admin-lifecycle-dashboard", ("NOPE-M54",)
        )
        self.assertEqual(res.status_code, 404, res.content)


# ============================================================================
# Manual transition endpoint
# ============================================================================


class LifecycleManualTransitionFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.sales_manager = make_user(username="manual-sm")
        make_membership(self.sales_manager, self.dealership, ROLE_SALES_MANAGER)
        self.sales_client = authenticated_client(self.sales_manager)

        self.recon_manager = make_user(username="manual-rm")
        make_membership(self.recon_manager, self.dealership, ROLE_RECON_MANAGER)
        self.recon_client = authenticated_client(self.recon_manager)

    def _seed(self, stock: str, initial: str) -> Vehicle:
        v = _vehicle(self.dealership, stock=stock)
        ensure_current_stage(
            v, dealership=self.dealership, initial_stage=initial
        )
        return v

    def test_manual_transition_succeeds(self):
        v = self._seed("M54-MT-OK", VEHICLE_STAGE_INSPECTION)
        res = _post(
            self.sales_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_RECON, "notes": "Findings found."},
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["current_stage"]["value"], "recon")
        self.assertEqual(body["current_stage"]["trigger"], "manual")
        self.assertEqual(
            body["current_stage"]["last_transition_note"], "Findings found."
        )

    def test_manual_transition_structural_refusal_returns_409(self):
        v = self._seed("M54-MT-INV", VEHICLE_STAGE_INCOMING)
        res = _post(
            self.sales_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_FRONTLINE},  # skips pipeline
        )
        self.assertEqual(res.status_code, 409, res.content)

    def test_manual_transition_no_op_returns_409(self):
        v = self._seed("M54-MT-NOOP", VEHICLE_STAGE_RECON)
        res = _post(
            self.sales_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_RECON},
        )
        self.assertEqual(res.status_code, 409, res.content)

    def test_manual_transition_role_refusal_returns_403(self):
        """Recon manager attempting a commercial transition —
        endpoint admits, service refuses via
        UnauthorizedStageTransitionError → HTTP 403. §5.f."""
        v = self._seed("M54-MT-ROLE", VEHICLE_STAGE_FRONTLINE)
        res = _post(
            self.recon_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_HOLD_RESERVED, "notes": "attempt"},
        )
        self.assertEqual(res.status_code, 403, res.content)

    def test_manual_transition_invalid_to_stage_returns_400(self):
        v = self._seed("M54-MT-BADSTAGE", VEHICLE_STAGE_INSPECTION)
        res = _post(
            self.sales_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": "sold"},  # not a shipped stage in M5
        )
        self.assertEqual(res.status_code, 400, res.content)

    def test_manual_transition_cross_tenant_returns_404(self):
        other = Dealership.objects.create(name="Other", slug="other-mt-m54")
        v = _vehicle(other, stock="M54-MT-XT")
        res = _post(
            self.sales_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_INSPECTION},
        )
        self.assertEqual(res.status_code, 404, res.content)

    def test_manual_transition_missing_stock_returns_404(self):
        res = _post(
            self.sales_client,
            "admin-lifecycle-manual-transition",
            ("MISSING-M54",),
            {"to_stage": VEHICLE_STAGE_INSPECTION},
        )
        self.assertEqual(res.status_code, 404, res.content)

    def test_recon_manager_can_do_retail_prep_transition(self):
        """Recon manager IS authorized for retail-preparation
        transitions (§5.f — retail-prep authority set includes
        recon_manager)."""
        v = self._seed("M54-MT-RM-OK", VEHICLE_STAGE_INSPECTION)
        res = _post(
            self.recon_client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_RECON, "notes": "recon manager ok"},
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["current_stage"]["value"], "recon")


# ============================================================================
# Rule-accept endpoint
# ============================================================================


class LifecycleRuleTransitionFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.sales_manager = make_user(username="rule-sm")
        make_membership(self.sales_manager, self.dealership, ROLE_SALES_MANAGER)
        self.client_ = authenticated_client(self.sales_manager)

    def _seed_inspection_with_findings(self, stock: str) -> Vehicle:
        v = _vehicle(self.dealership, stock=stock)
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_INSPECTION,
        )
        _completed_report_with_required_finding(v, self.dealership)
        return v

    def test_rule_accept_succeeds_when_suggestion_fires(self):
        v = self._seed_inspection_with_findings("M54-RA-OK")
        res = _post(
            self.client_,
            "admin-lifecycle-rule-transition",
            (v.stock_number,),
            {"rule_name": "inspection_to_recon"},
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["current_stage"]["value"], "recon")
        self.assertEqual(body["current_stage"]["trigger"], "rule")

    def test_rule_accept_returns_409_when_rule_does_not_fire(self):
        """Vehicle at inspection but with no completed report —
        inspection_to_recon does not fire; endpoint refuses."""
        v = _vehicle(self.dealership, stock="M54-RA-NOFIRE")
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_INSPECTION,
        )
        # No condition report — rule refuses.
        res = _post(
            self.client_,
            "admin-lifecycle-rule-transition",
            (v.stock_number,),
            {"rule_name": "inspection_to_recon"},
        )
        self.assertEqual(res.status_code, 409, res.content)

    def test_rule_accept_returns_409_for_unknown_rule_name(self):
        v = self._seed_inspection_with_findings("M54-RA-BADRULE")
        res = _post(
            self.client_,
            "admin-lifecycle-rule-transition",
            (v.stock_number,),
            {"rule_name": "nonexistent_rule"},
        )
        self.assertEqual(res.status_code, 409, res.content)

    def test_rule_accept_returns_409_when_prerequisites_unmet(self):
        """photography_to_listing always returns a structured
        prerequisite (M6 photo predicate not shipped). Accepting it
        refuses with 409."""
        v = _vehicle(self.dealership, stock="M54-RA-PHOTO")
        ensure_current_stage(
            v,
            dealership=self.dealership,
            initial_stage=VEHICLE_STAGE_PHOTOGRAPHY,
        )
        res = _post(
            self.client_,
            "admin-lifecycle-rule-transition",
            (v.stock_number,),
            {"rule_name": "photography_to_listing"},
        )
        self.assertEqual(res.status_code, 409, res.content)

    def test_rule_accept_cross_tenant_returns_404(self):
        other = Dealership.objects.create(name="Other", slug="other-ra-m54")
        v = _vehicle(other, stock="M54-RA-XT")
        res = _post(
            self.client_,
            "admin-lifecycle-rule-transition",
            (v.stock_number,),
            {"rule_name": "inspection_to_recon"},
        )
        self.assertEqual(res.status_code, 404, res.content)


# ============================================================================
# Cross-cutting regression boundaries
# ============================================================================


class LifecycleEndpointsWriteNoM4Data(TestCase):
    """The M5.4 endpoints must not touch M2 / M4 substrate."""

    def test_manual_transition_writes_no_workorder(self):
        from dealer_ai.models import VehicleCost, WorkOrder

        dealership = get_default_dealership()
        user = make_user(username="reg-user-m54")
        make_membership(user, dealership, ROLE_SALES_MANAGER)
        client = authenticated_client(user)
        v = _vehicle(dealership, stock="M54-REG")
        ensure_current_stage(
            v, dealership=dealership, initial_stage=VEHICLE_STAGE_INSPECTION
        )

        wo_before = WorkOrder.objects.filter(vehicle=v).count()
        vc_before = VehicleCost.objects.filter(vehicle=v).count()

        res = _post(
            client,
            "admin-lifecycle-manual-transition",
            (v.stock_number,),
            {"to_stage": VEHICLE_STAGE_RECON, "notes": "reg test"},
        )
        self.assertEqual(res.status_code, 200, res.content)

        self.assertEqual(
            WorkOrder.objects.filter(vehicle=v).count(), wo_before
        )
        self.assertEqual(
            VehicleCost.objects.filter(vehicle=v).count(), vc_before
        )
