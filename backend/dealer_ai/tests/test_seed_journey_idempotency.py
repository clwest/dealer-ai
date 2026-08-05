"""Milestone 34 · Increment 1 — regression coverage for rerun-safe
seed idempotency across the three shared-DB non-idempotent journeys.

Verifies that each seed command restores its journey's pre-flight
invariants across a **mutate → re-seed** cycle — not merely that
first-run provisioning is correct (which the M20.2 / M20.3 test
files already cover).

Per M34.0 §5.b D6, one test per seed:

- `SalesManagerDailyStartupRerunInvariantTests` — assign a lead to
  the advisor + create a be-back on Lead 2 + create + pause a 1wk
  cadence on Lead 1 + pause the seed 24hr cadence; re-seed;
  assert all four D2 invariants restored.
- `ReconWorkflowRerunInvariantTests` — record a Must-do decision on
  the seeded finding; re-seed; assert `finding.recon_decision` is
  None.
- `OfficeAccountingWorkflowRerunInvariantTests` — freeze a
  TrialBalanceSnapshot; re-seed; assert snapshot count on the
  fixture dealership is 0.

Tests use `django.core.management.call_command()` + direct model
queries + the same fixture selectors the seed commands use.

Per M34.0 §5.b D8 durable lesson (ff): *Acceptance journeys must be
independently rerunnable against shared state; green-on-clean-DB
alone is insufficient evidence of operational reliability.* These
tests are the enforcement mechanism.
"""

from __future__ import annotations

import datetime as dt
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from dealer_ai.management.commands.seed_journey_recon_workflow import (
    FIXTURE_FINDING_TAG as RECON_FIXTURE_FINDING_TAG,
)
from dealer_ai.management.commands.seed_journey_sales_manager_daily_startup import (
    ADVISOR_SLUG,
    FIXTURE_TAG as SM_FIXTURE_TAG,
)
from dealer_ai.models import (
    BE_BACK_REASON_BRING_CO_SIGNER,
    RECON_DECISION_TIER_MUST_DO,
    BeBack,
    ConditionFinding,
    CustomerLead,
    FollowUpCadence,
    ReconDecision,
    Salesperson,
    TrialBalanceSnapshot,
)
from dealer_ai.services.accounting.trial_balance_close import (
    freeze_trial_balance,
)
from dealer_ai.services.be_backs.be_back import record_be_back
from dealer_ai.services.follow_ups.cadence import (
    pause_cadence,
    start_cadence,
)
from dealer_ai.services.recon import record_decision
from dealer_ai.services.tenancy import get_default_dealership


def _run_sm_seed() -> None:
    call_command(
        "seed_journey_sales_manager_daily_startup", stdout=StringIO()
    )


def _run_recon_seed() -> None:
    call_command("seed_journey_recon_workflow", stdout=StringIO())


def _run_office_seed() -> None:
    call_command(
        "seed_journey_office_accounting_workflow", stdout=StringIO()
    )


class SalesManagerDailyStartupRerunInvariantTests(TestCase):
    """M34.1 · D2 — sales-manager seed restores four invariants on rerun.

    The M20.2 + M21.3 journey mutates four kinds of state that the
    seed's create-if-missing path never resets:

    1. `assigned_to` on Lead 1 (assigned to Acceptance Advisor).
    2. BeBack rows on Lead 2 (created via UI).
    3. Non-24hr FollowUpCadence rows on Lead 1 (1wk created + paused).
    4. Seed 24hr FollowUpCadence pause state on Lead 1.

    The M34.1 `_restore_rerun_invariants` method resets all four
    before `_provision_leads`.
    """

    def test_re_seed_unassigns_leads_after_journey_style_assignment(
        self,
    ) -> None:
        _run_sm_seed()
        dealership = get_default_dealership()
        advisor = Salesperson.objects.get(slug=ADVISOR_SLUG)
        leads = list(
            CustomerLead.objects.filter(
                dealership=dealership, notes__startswith=SM_FIXTURE_TAG
            ).order_by("pk")
        )
        self.assertEqual(len(leads), 3)

        # Simulate journey step 4 — assign Lead 1 to Acceptance Advisor.
        lead_one = leads[0]
        lead_one.assigned_to = advisor
        lead_one.save(update_fields=["assigned_to"])
        self.assertIsNotNone(
            CustomerLead.objects.get(pk=lead_one.pk).assigned_to
        )

        # Re-seed. D2 should unassign every fixture-tagged lead.
        _run_sm_seed()

        for lead in CustomerLead.objects.filter(
            dealership=dealership, notes__startswith=SM_FIXTURE_TAG
        ):
            self.assertIsNone(
                lead.assigned_to,
                f"Lead {lead.pk} should be unassigned after re-seed; "
                f"D2 rerun-invariant reset failed.",
            )

    def test_re_seed_deletes_journey_created_be_backs(self) -> None:
        _run_sm_seed()
        dealership = get_default_dealership()
        leads = list(
            CustomerLead.objects.filter(
                dealership=dealership, notes__startswith=SM_FIXTURE_TAG
            ).order_by("pk")
        )

        # Simulate journey line 227 — create a be-back on Lead 2.
        record_be_back(
            dealership=dealership,
            lead=leads[1],
            promised_at=timezone.now() + dt.timedelta(days=1),
            promised_reason=BE_BACK_REASON_BRING_CO_SIGNER,
            notes="[M34.1 D6 regression test] journey-simulated be-back",
        )
        self.assertEqual(
            BeBack.objects.filter(lead__in=leads).count(),
            1,
            "pre-condition: exactly one be-back should exist before re-seed",
        )

        _run_sm_seed()

        self.assertEqual(
            BeBack.objects.filter(lead__in=leads).count(),
            0,
            "D2 should delete all be-backs on seeded leads at re-seed time",
        )

    def test_re_seed_clears_non_24hr_cadences_but_preserves_seed_24hr(
        self,
    ) -> None:
        _run_sm_seed()
        dealership = get_default_dealership()
        leads = list(
            CustomerLead.objects.filter(
                dealership=dealership, notes__startswith=SM_FIXTURE_TAG
            ).order_by("pk")
        )

        # Simulate journey line 265 — create + pause a 1wk cadence on
        # Lead 1. Note: the seed 24hr cadence is already active on
        # Lead 1; adding 1wk is valid because unique-active is scoped
        # to (lead, template). Pause semantics per M11.4 model =
        # is_active=False (no paused_at column).
        cadence_1wk = start_cadence(
            dealership=dealership,
            lead=leads[0],
            template="1wk",
        )
        pause_cadence(dealership=dealership, cadence=cadence_1wk)
        self.assertEqual(
            FollowUpCadence.objects.filter(
                lead=leads[0], template="1wk"
            ).count(),
            1,
        )

        _run_sm_seed()

        # D2: non-24hr cadences on seeded leads deleted.
        self.assertEqual(
            FollowUpCadence.objects.filter(
                lead__in=leads, template="1wk"
            ).count(),
            0,
            "D2 should delete 1wk cadence on seeded leads at re-seed time",
        )

        # D2: seed 24hr cadence still active.
        seed_cadence = FollowUpCadence.objects.get(
            lead=leads[0], template="24hr"
        )
        self.assertTrue(seed_cadence.is_active)

    def test_re_seed_restores_paused_seed_24hr_cadence_to_active(
        self,
    ) -> None:
        _run_sm_seed()
        dealership = get_default_dealership()
        leads = list(
            CustomerLead.objects.filter(
                dealership=dealership, notes__startswith=SM_FIXTURE_TAG
            ).order_by("pk")
        )
        seed_cadence = FollowUpCadence.objects.get(
            lead=leads[0], template="24hr"
        )
        pause_cadence(dealership=dealership, cadence=seed_cadence)
        seed_cadence.refresh_from_db()
        self.assertFalse(seed_cadence.is_active)

        _run_sm_seed()

        seed_cadence.refresh_from_db()
        self.assertTrue(
            seed_cadence.is_active,
            "D2 should re-activate the seed 24hr cadence on re-seed",
        )


class ReconWorkflowRerunInvariantTests(TestCase):
    """M34.1 · D3 — recon seed restores the pre-flight invariant that
    the seeded ConditionFinding has no ReconDecision on rerun.
    """

    def test_re_seed_clears_recon_decision_after_journey_style_click(
        self,
    ) -> None:
        _run_recon_seed()
        dealership = get_default_dealership()
        finding = ConditionFinding.objects.get(
            dealership=dealership,
            description__startswith=RECON_FIXTURE_FINDING_TAG,
        )
        self.assertFalse(
            hasattr(finding, "recon_decision")
            and finding.recon_decision is not None,
            "pre-condition: fixture finding should start with no decision",
        )

        # Simulate journey step 4 — Must-do click via the M4.2 service.
        record_decision(
            finding=finding,
            dealership=dealership,
            tier=RECON_DECISION_TIER_MUST_DO,
            notes="[M34.1 D6 regression test] journey-simulated decision",
        )
        self.assertEqual(
            ReconDecision.objects.filter(finding=finding).count(), 1
        )

        _run_recon_seed()

        # D3: ReconDecision on the seeded finding deleted.
        finding.refresh_from_db()
        self.assertEqual(
            ReconDecision.objects.filter(finding=finding).count(),
            0,
            "D3 should delete ReconDecision on the seeded finding at re-seed",
        )


class OfficeAccountingWorkflowRerunInvariantTests(TestCase):
    """M34.1 · D4 — accounting seed restores the pre-flight invariant
    that TrialBalanceSnapshot count on the fixture dealership is 0
    on rerun.

    Scoped-wipe safety is enforced by the M20_ACCEPTANCE_DB env-guard
    in production usage; the test relies on Django's per-test
    transactional isolation so no shipped snapshot on any real DB is
    at risk.
    """

    def test_re_seed_deletes_snapshots_on_fixture_dealership(self) -> None:
        _run_office_seed()
        dealership = get_default_dealership()

        # Simulate journey step 3 — freeze via the M17.1 service.
        freeze_trial_balance(
            dealership=dealership,
            as_of=timezone.now(),
        )
        self.assertEqual(
            TrialBalanceSnapshot.objects.filter(
                dealership=dealership
            ).count(),
            1,
            "pre-condition: exactly one snapshot should exist before re-seed",
        )

        _run_office_seed()

        # D4: all snapshots on the fixture dealership deleted.
        self.assertEqual(
            TrialBalanceSnapshot.objects.filter(
                dealership=dealership
            ).count(),
            0,
            "D4 should delete all TrialBalanceSnapshots on the fixture "
            "dealership at re-seed time",
        )
