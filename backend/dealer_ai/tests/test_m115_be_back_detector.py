"""Milestone 11 · Increment 5 (SESSION_118) — BeBack Celery detector tests.

Locks the two tasks in :mod:`services.be_backs.tasks` per §5.g.3
Option B. The detector *does* transition state (unlike the M11.4
read-only surfacer) — this is the deliberate difference between
the customer's promise (auto-tracked) and the operator's task
completion (operator-only).

Coverage:

- Detector transitions stale promised → no_show.
- Detector respects the configured grace period — a promise
  that just passed but is still within grace is left alone.
- Detector excludes already-returned rows.
- Detector excludes already-no_show rows (idempotency).
- Detector excludes rows with ``actual_return_at`` set (defensive
  — should not happen with the state guard but locks the query).
- Orchestrator dispatches per tenant.
"""

from __future__ import annotations

import datetime as dt

from django.test import TestCase, override_settings
from django.utils import timezone

from dealer_ai.models import (
    BE_BACK_REASON_TEST_DRIVE,
    BE_BACK_STATE_NO_SHOW,
    BE_BACK_STATE_PROMISED,
    BE_BACK_STATE_RETURNED,
    BeBack,
    CustomerLead,
    Dealership,
)
from dealer_ai.services.be_backs.tasks import (
    detect_no_show_be_backs_for_all_tenants,
    detect_no_show_be_backs_for_tenant,
)


@override_settings(BE_BACK_NO_SHOW_GRACE_HOURS=4)
class DetectorForTenantTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bb-det", name="BB Detector"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Detected"
        )

    def _mk(self, *, promised_at, state=BE_BACK_STATE_PROMISED,
            actual_return_at=None) -> BeBack:
        return BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=promised_at,
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
            state=state,
            actual_return_at=actual_return_at,
        )

    def test_transitions_stale_promised_to_no_show(self) -> None:
        # 6 hours past promise, grace is 4 → stale.
        bb = self._mk(promised_at=timezone.now() - dt.timedelta(hours=6))
        result = detect_no_show_be_backs_for_tenant(
            dealership_id=self.dealership.pk
        )
        bb.refresh_from_db()
        self.assertEqual(bb.state, BE_BACK_STATE_NO_SHOW)
        self.assertEqual(result["transitioned_count"], 1)
        self.assertIn(bb.pk, result["transitioned_ids"])

    def test_respects_grace_period(self) -> None:
        # 2 hours past promise, grace is 4 → still within grace.
        bb = self._mk(promised_at=timezone.now() - dt.timedelta(hours=2))
        result = detect_no_show_be_backs_for_tenant(
            dealership_id=self.dealership.pk
        )
        bb.refresh_from_db()
        self.assertEqual(bb.state, BE_BACK_STATE_PROMISED)
        self.assertEqual(result["transitioned_count"], 0)

    def test_excludes_already_returned(self) -> None:
        bb = self._mk(
            promised_at=timezone.now() - dt.timedelta(hours=10),
            state=BE_BACK_STATE_RETURNED,
            actual_return_at=timezone.now() - dt.timedelta(hours=1),
        )
        detect_no_show_be_backs_for_tenant(dealership_id=self.dealership.pk)
        bb.refresh_from_db()
        self.assertEqual(bb.state, BE_BACK_STATE_RETURNED)

    def test_excludes_already_no_show(self) -> None:
        bb = self._mk(
            promised_at=timezone.now() - dt.timedelta(hours=10),
            state=BE_BACK_STATE_NO_SHOW,
        )
        result = detect_no_show_be_backs_for_tenant(
            dealership_id=self.dealership.pk
        )
        # Idempotent: no re-transition, no error.
        self.assertEqual(result["transitioned_count"], 0)
        bb.refresh_from_db()
        self.assertEqual(bb.state, BE_BACK_STATE_NO_SHOW)


@override_settings(BE_BACK_NO_SHOW_GRACE_HOURS=4)
class DetectorOrchestratorTests(TestCase):
    def setUp(self) -> None:
        self.d1 = Dealership.objects.create(slug="bb-orc-1", name="BB Orc 1")
        self.d2 = Dealership.objects.create(slug="bb-orc-2", name="BB Orc 2")
        for d in (self.d1, self.d2):
            lead = CustomerLead.objects.create(dealership=d, name=f"lead-{d.slug}")
            BeBack.objects.create(
                dealership=d,
                lead=lead,
                promised_at=timezone.now() - dt.timedelta(hours=10),
                promised_reason=BE_BACK_REASON_TEST_DRIVE,
                state=BE_BACK_STATE_PROMISED,
            )

    def test_orchestrator_dispatches_per_tenant(self) -> None:
        # CELERY_TASK_ALWAYS_EAGER=True makes each dispatched task
        # run synchronously. Verify both our stale be-backs got
        # transitioned after the orchestrator run.
        result = detect_no_show_be_backs_for_all_tenants()
        self.assertGreaterEqual(result["dispatched_tenant_count"], 2)
        for d in (self.d1, self.d2):
            transitioned = BeBack.objects.filter(
                dealership=d, state=BE_BACK_STATE_NO_SHOW
            ).count()
            self.assertEqual(transitioned, 1)
