"""Manager Phase 1: handoff/triage queue filter tests.

The existing GET /admin/leads/ endpoint gains optional query params:
``handed_off``, ``urgency``, ``since``, ``ordering``. All are optional
and backward-compatible — no params = pre-Phase-1 behavior.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import CustomerLead
from dealer_ai.tests._auth_helpers import sales_manager_client_at_default


def _make_lead(
    *,
    name: str,
    urgency: str = "",
    handed_off: bool = False,
    target_monthly_payment: Decimal | None = None,
    created_at_offset_hours: float | None = None,
) -> CustomerLead:
    lead = CustomerLead.objects.create(
        name=name,
        urgency=urgency,
        handed_off=handed_off,
        target_monthly_payment=target_monthly_payment,
    )
    if created_at_offset_hours is not None:
        # Force a specific created_at for since-filter tests.
        CustomerLead.objects.filter(pk=lead.pk).update(
            created_at=timezone.now() - timedelta(hours=created_at_offset_hours)
        )
        lead.refresh_from_db()
    return lead


class AdminLeadListFilterTests(TestCase):
    """Optional handoff/urgency/since/ordering query params filter the
    existing /admin/leads/ endpoint without breaking back-compat."""

    def setUp(self):
        self.client = sales_manager_client_at_default()
        # 4 leads spanning urgencies + handoff status + age.
        self.lead_immediate_open = _make_lead(
            name="Alice Buyer",
            urgency="immediate",
            handed_off=False,
            created_at_offset_hours=1,
        )
        self.lead_this_week_open = _make_lead(
            name="Bob Browse",
            urgency="this_week",
            handed_off=False,
            created_at_offset_hours=12,
        )
        self.lead_this_month_handed = _make_lead(
            name="Cara Closed",
            urgency="this_month",
            handed_off=True,
            created_at_offset_hours=48,
        )
        self.lead_researching_old = _make_lead(
            name="Dan Distant",
            urgency="researching",
            handed_off=False,
            created_at_offset_hours=24 * 10,  # 10 days old
        )

    def _get(self, **params) -> dict:
        url = reverse("dealer_ai:admin-lead-list")
        res = self.client.get(url, params)
        self.assertEqual(res.status_code, 200)
        return res.json()

    # ---- Backward compatibility -----------------------------------------

    def test_no_params_returns_all_leads(self):
        body = self._get()
        names = [r["name"] for r in body["results"]]
        self.assertEqual(set(names), {
            "Alice Buyer", "Bob Browse", "Cara Closed", "Dan Distant"
        })
        self.assertEqual(body["count"], 4)

    # ---- handed_off filter ----------------------------------------------

    def test_handed_off_false_returns_only_open(self):
        body = self._get(handed_off="false")
        names = {r["name"] for r in body["results"]}
        self.assertEqual(names, {"Alice Buyer", "Bob Browse", "Dan Distant"})
        self.assertEqual(body["count"], 3)

    def test_handed_off_true_returns_only_closed(self):
        body = self._get(handed_off="true")
        names = {r["name"] for r in body["results"]}
        self.assertEqual(names, {"Cara Closed"})
        self.assertEqual(body["count"], 1)

    def test_handed_off_garbage_value_falls_back_to_all(self):
        body = self._get(handed_off="maybe")
        self.assertEqual(body["count"], 4)

    # ---- urgency filter -------------------------------------------------

    def test_urgency_single_value(self):
        body = self._get(urgency="immediate")
        names = {r["name"] for r in body["results"]}
        self.assertEqual(names, {"Alice Buyer"})
        self.assertEqual(body["count"], 1)

    def test_urgency_multiple_values_csv(self):
        body = self._get(urgency="immediate,this_week")
        names = {r["name"] for r in body["results"]}
        self.assertEqual(names, {"Alice Buyer", "Bob Browse"})
        self.assertEqual(body["count"], 2)

    def test_urgency_garbage_value_silently_ignored(self):
        body = self._get(urgency="garbage")
        # No valid tokens → filter not applied → all 4 leads.
        self.assertEqual(body["count"], 4)

    def test_urgency_partial_garbage_keeps_valid_tokens(self):
        body = self._get(urgency="immediate,garbage")
        names = {r["name"] for r in body["results"]}
        self.assertEqual(names, {"Alice Buyer"})

    # ---- since filter ---------------------------------------------------

    def test_since_24h_excludes_older_leads(self):
        body = self._get(since="24h")
        names = {r["name"] for r in body["results"]}
        # Alice (1h) and Bob (12h) survive; Cara (48h) and Dan (240h) cut.
        self.assertEqual(names, {"Alice Buyer", "Bob Browse"})

    def test_since_7d_excludes_only_oldest(self):
        body = self._get(since="7d")
        names = {r["name"] for r in body["results"]}
        # Dan (10 days) cut; everyone else (1h, 12h, 48h) survives.
        self.assertEqual(
            names, {"Alice Buyer", "Bob Browse", "Cara Closed"}
        )

    def test_since_30d_includes_everyone(self):
        body = self._get(since="30d")
        self.assertEqual(body["count"], 4)

    def test_since_garbage_silently_ignored(self):
        body = self._get(since="99x")
        self.assertEqual(body["count"], 4)

    # ---- ordering=urgency ----------------------------------------------

    def test_ordering_urgency_orders_by_severity_desc(self):
        body = self._get(ordering="urgency")
        names = [r["name"] for r in body["results"]]
        # immediate(4) → this_week(3) → this_month(2) → researching(1)
        self.assertEqual(
            names,
            ["Alice Buyer", "Bob Browse", "Cara Closed", "Dan Distant"],
        )

    def test_ordering_urgency_with_handed_off_filter_still_severity_sorted(self):
        body = self._get(ordering="urgency", handed_off="false")
        names = [r["name"] for r in body["results"]]
        self.assertEqual(
            names, ["Alice Buyer", "Bob Browse", "Dan Distant"]
        )

    def test_default_ordering_is_created_at_desc(self):
        body = self._get()
        names = [r["name"] for r in body["results"]]
        # Most recent first: Alice(1h) → Bob(12h) → Cara(48h) → Dan(240h)
        self.assertEqual(
            names,
            ["Alice Buyer", "Bob Browse", "Cara Closed", "Dan Distant"],
        )

    # ---- Combined filters -----------------------------------------------

    def test_handed_off_false_plus_urgency_immediate_plus_since_24h(self):
        body = self._get(
            handed_off="false", urgency="immediate", since="24h"
        )
        names = {r["name"] for r in body["results"]}
        self.assertEqual(names, {"Alice Buyer"})
        self.assertEqual(body["count"], 1)

    def test_combined_filters_can_yield_zero_results(self):
        body = self._get(
            handed_off="true", urgency="immediate"
        )
        # No handed-off + immediate leads exist.
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["results"], [])

    # ---- Limit interaction ----------------------------------------------

    def test_limit_caps_results_after_filter(self):
        body = self._get(handed_off="false", limit=2)
        self.assertLessEqual(len(body["results"]), 2)
        # count reflects the filtered total before limit.
        self.assertEqual(body["count"], 3)
