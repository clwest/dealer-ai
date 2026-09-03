"""SESSION_230 finding 12 — the queue card's missing list.

Locks the ``recon_list`` payload the needs-authorization queue
card now carries: every WO on the car bucketed by status +
every finding on the car bucketed by decision tier, so a manager
who is asked to approve going over the cap can see WHAT the cap
is being spent on.

The load-bearing invariants:

- ``spent + committed + this_wo + other_queued == prior_spend + this_wo``
  — the two ways of counting committed money must agree.
- The overage stays byte-identical to what SESSION_228 shipped —
  pending inspector estimates ARE surfaced but do NOT enter
  ``overage_for`` or ``recon_budget_for``.
- Query count per row is bounded (Part 4 in the brief).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    DealerOnboardingProfile,
    RECON_DECISION_TIER_MUST_DO,
    RECON_DECISION_TIER_SHOULD_DO,
    RECON_DECISION_TIER_WONT_DO,
    ROLE_DEALER_OWNER,
    ReconDecision,
    UserDealershipRole,
    Vehicle,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_VENUE_IN_HOUSE,
)
from dealer_ai.services import recon as recon_service
from dealer_ai.services import recon_budget as recon_budget_service

User = get_user_model()


def _vehicle(stock, dealership, *, price=Decimal("10000.00")) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="F-150",
        price=price,
        dealership=dealership,
    )


def _report(vehicle, dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Chris",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _finding(report, dealership, *, est=Decimal("500.00"), desc="F"):
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=desc,
        estimated_cost=est,
    )


def _decide(finding, dealership, tier, user):
    return ReconDecision.objects.create(
        finding=finding,
        dealership=dealership,
        tier=tier,
        decided_by=user,
        decided_at=timezone.now(),
    )


def _set_budget_mode(dealership, *, default=Decimal("1200.00")):
    profile, _ = DealerOnboardingProfile.objects.get_or_create(
        dealership=dealership,
        defaults=dict(
            recon_authorization_mode=(
                DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_BUDGET
            ),
            recon_budget_default=default,
        ),
    )
    profile.recon_authorization_mode = (
        DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_BUDGET
    )
    profile.recon_budget_default = default
    profile.recon_budget_bands = []
    profile.save()
    return profile


def _owner_client(dealership):
    owner = User.objects.create_user(username="s230-owner", password="pw")
    UserDealershipRole.objects.create(
        user=owner, dealership=dealership, role=ROLE_DEALER_OWNER
    )
    client = APIClient()
    client.force_authenticate(owner)
    return client, owner


QUEUE_URL = "/api/dealer-ai/admin/recon/needs-authorization/"


class ReconListShape(TestCase):
    """The payload shape — every bucket present, with total + items."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("1000.00"))
        self.vehicle = _vehicle(
            "S230-A", self.default, price=Decimal("8000.00")
        )
        self.report = _report(self.vehicle, self.default)
        # One over-budget finding backs the queued WO.
        self.big = _finding(
            self.report, self.default, est=Decimal("1600"), desc="Big"
        )
        self.client, self.owner = _owner_client(self.default)
        # Create the over-budget WO via the service (it queues).
        self.wo = recon_service.create_work_order_from_finding(
            self.big,
            dealership=self.default,
            created_by=self.owner,
        )
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.status, WORK_ORDER_STATUS_DRAFT)

    def test_row_carries_recon_list_with_every_bucket(self):
        res = self.client.get(QUEUE_URL)
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["queue"]
        self.assertEqual(len(rows), 1)
        rl = rows[0]["recon_list"]
        for bucket in (
            "spent",
            "committed",
            "this_wo",
            "other_queued",
            "decided_pending",
            "proposed",
            "undecided",
            "declined",
        ):
            self.assertIn(bucket, rl, f"missing bucket {bucket}")
            self.assertIn("total", rl[bucket])
            self.assertIn("items", rl[bucket])
        # This WO shows up in its own bucket.
        self.assertEqual(len(rl["this_wo"]["items"]), 1)
        self.assertEqual(rl["this_wo"]["items"][0]["work_order_id"], self.wo.pk)


class ReconciliationInvariant(TestCase):
    """spent + committed + this_wo + other_queued == prior_spend + this_wo.

    A car with one completed WO, one approved WO, one other draft WO
    (and this one being reviewed) plus a set of findings — the two
    ways of counting committed money must agree.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("500.00"))
        self.vehicle = _vehicle(
            "S230-B", self.default, price=Decimal("8000.00")
        )
        self.report = _report(self.vehicle, self.default)
        self.client, self.owner = _owner_client(self.default)
        # A completed WO — actual $200.
        f1 = _finding(
            self.report, self.default, est=Decimal("300"), desc="Done"
        )
        self.completed_wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("200"),
        )
        recon_service.attach_findings(
            self.completed_wo,
            dealership=self.default,
            finding_ids=[f1.pk],
        )
        recon_service.approve_work_order(
            self.completed_wo,
            dealership=self.default,
            approved_by=self.owner,
        )
        recon_service.start_work_order(
            self.completed_wo,
            dealership=self.default,
            started_by=self.owner,
        )
        recon_service.complete_work_order(
            self.completed_wo,
            dealership=self.default,
            completed_by=self.owner,
            actual_cost=Decimal("200"),
        )
        # An approved (committed) WO — estimate $150.
        f2 = _finding(
            self.report, self.default, est=Decimal("150"), desc="Approved"
        )
        self.approved_wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("150"),
        )
        recon_service.attach_findings(
            self.approved_wo,
            dealership=self.default,
            finding_ids=[f2.pk],
        )
        recon_service.approve_work_order(
            self.approved_wo,
            dealership=self.default,
            approved_by=self.owner,
        )
        # Another draft WO on the same car — estimate $100.
        f3 = _finding(
            self.report, self.default, est=Decimal("100"), desc="OtherDraft"
        )
        self.other_draft = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("100"),
        )
        recon_service.attach_findings(
            self.other_draft,
            dealership=self.default,
            finding_ids=[f3.pk],
        )
        # The queued WO — estimate $400, pushes the total over $500.
        f4 = _finding(
            self.report, self.default, est=Decimal("400"), desc="ThisOne"
        )
        self.this_wo = recon_service.create_work_order_from_finding(
            f4, dealership=self.default, created_by=self.owner
        )
        self.this_wo.refresh_from_db()
        self.assertEqual(self.this_wo.status, WORK_ORDER_STATUS_DRAFT)

    def test_bucket_sum_equals_prior_spend(self):
        res = self.client.get(QUEUE_URL)
        self.assertEqual(res.status_code, 200, res.content)
        rows = res.json()["queue"]
        # There may be more than one queued row on this car if the
        # other draft is also under-budget-alone; pick ours.
        rl = None
        prior_spend = None
        this_wo_estimate = None
        for row in rows:
            if row["work_order"]["id"] == self.this_wo.pk:
                rl = row["recon_list"]
                prior_spend = Decimal(row["prior_spend"])
                this_wo_estimate = Decimal(rl["this_wo"]["total"])
                break
        self.assertIsNotNone(rl, "queued WO missing from queue")
        assert rl is not None  # type checker
        spent = Decimal(rl["spent"]["total"])
        committed = Decimal(rl["committed"]["total"])
        this_wo = Decimal(rl["this_wo"]["total"])
        other_queued = Decimal(rl["other_queued"]["total"])
        # The invariant.
        self.assertEqual(
            spent + committed + this_wo + other_queued,
            (prior_spend or Decimal("0")) + (this_wo_estimate or Decimal("0")),
        )
        # And the components make sense.
        self.assertEqual(spent, Decimal("200.00"))
        self.assertEqual(committed, Decimal("150.00"))
        self.assertEqual(other_queued, Decimal("100.00"))
        self.assertEqual(this_wo, Decimal("400.00"))


class EveryBucketAtOnce(TestCase):
    """A car with a finding in every bucket at once.

    Sets up: 1 completed WO, 1 approved WO, 1 in_progress WO,
    1 cancelled WO (invisible), 1 other draft WO, 1 queued WO
    being reviewed; plus 4 findings NOT attached to any WO — one
    must-do, one should-do, one undecided, one won't-do.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("400.00"))
        self.vehicle = _vehicle(
            "S230-C", self.default, price=Decimal("8000.00")
        )
        self.report = _report(self.vehicle, self.default)
        self.client, self.owner = _owner_client(self.default)

        # Attached findings feed the WOs.
        for i, desc in enumerate(
            ["done", "approved", "inprogress", "cancelled", "otherdraft"]
        ):
            _finding(
                self.report,
                self.default,
                est=Decimal("100"),
                desc=f"wo-{desc}",
            )
        attached = list(
            ConditionFinding.objects.filter(
                report=self.report,
                description__startswith="wo-",
            ).order_by("pk")
        )

        def _mk_wo(finding, est):
            wo = recon_service.create_work_order(
                self.vehicle,
                dealership=self.default,
                category=CONDITION_CATEGORY_MECHANICAL,
                venue=WORK_ORDER_VENUE_IN_HOUSE,
                estimated_cost=est,
            )
            recon_service.attach_findings(
                wo,
                dealership=self.default,
                finding_ids=[finding.pk],
            )
            return wo

        # Completed WO — actual $50.
        wo_done = _mk_wo(attached[0], Decimal("50"))
        recon_service.approve_work_order(
            wo_done, dealership=self.default, approved_by=self.owner
        )
        recon_service.start_work_order(
            wo_done, dealership=self.default, started_by=self.owner
        )
        recon_service.complete_work_order(
            wo_done,
            dealership=self.default,
            completed_by=self.owner,
            actual_cost=Decimal("50"),
        )
        # Approved WO — $60.
        wo_appr = _mk_wo(attached[1], Decimal("60"))
        recon_service.approve_work_order(
            wo_appr, dealership=self.default, approved_by=self.owner
        )
        # In-progress WO — $70.
        wo_inp = _mk_wo(attached[2], Decimal("70"))
        recon_service.approve_work_order(
            wo_inp, dealership=self.default, approved_by=self.owner
        )
        recon_service.start_work_order(
            wo_inp, dealership=self.default, started_by=self.owner
        )
        # Cancelled WO — $80 (must NOT count).
        wo_can = _mk_wo(attached[3], Decimal("80"))
        recon_service.cancel_work_order(
            wo_can,
            dealership=self.default,
            cancelled_by=self.owner,
            cancellation_reason="not this one",
        )
        # Other draft WO — $90 (other_queued).
        self.other_draft = _mk_wo(attached[4], Decimal("90"))

        # Free-floating findings — one per bucket. Skip won't-do
        # attachment; every finding is unattached.
        self.must = _finding(
            self.report, self.default, est=Decimal("11"), desc="must"
        )
        _decide(
            self.must, self.default, RECON_DECISION_TIER_MUST_DO, self.owner
        )
        self.should = _finding(
            self.report, self.default, est=Decimal("22"), desc="should"
        )
        _decide(
            self.should, self.default, RECON_DECISION_TIER_SHOULD_DO, self.owner
        )
        self.undecided_f = _finding(
            self.report, self.default, est=Decimal("33"), desc="undecided"
        )
        self.wont = _finding(
            self.report, self.default, est=Decimal("44"), desc="wont"
        )
        _decide(
            self.wont, self.default, RECON_DECISION_TIER_WONT_DO, self.owner
        )

        # The queued WO under review — big enough to be over-budget.
        f_this = _finding(
            self.report, self.default, est=Decimal("500"), desc="reviewing"
        )
        self.this_wo = recon_service.create_work_order_from_finding(
            f_this, dealership=self.default, created_by=self.owner
        )
        self.this_wo.refresh_from_db()

    def test_every_bucket_populated(self):
        res = self.client.get(QUEUE_URL)
        self.assertEqual(res.status_code, 200, res.content)
        row = next(
            r
            for r in res.json()["queue"]
            if r["work_order"]["id"] == self.this_wo.pk
        )
        rl = row["recon_list"]
        # WO buckets — completed goes to spent (actual), approved
        # & in-progress go to committed, other draft goes to
        # other_queued, this WO is in this_wo. Cancelled invisible.
        self.assertEqual(Decimal(rl["spent"]["total"]), Decimal("50.00"))
        self.assertEqual(
            Decimal(rl["committed"]["total"]), Decimal("130.00")
        )  # 60 + 70
        self.assertEqual(
            Decimal(rl["other_queued"]["total"]), Decimal("90.00")
        )
        self.assertEqual(
            Decimal(rl["this_wo"]["total"]), Decimal("500.00")
        )
        # Finding buckets — one free-floating item each with the
        # estimated_cost, plus the cancelled WO's finding falls
        # into undecided (its only WO is cancelled, so the work is
        # not being addressed — it's correctly surfaced as pending).
        self.assertEqual(len(rl["decided_pending"]["items"]), 1)
        self.assertEqual(
            Decimal(rl["decided_pending"]["total"]), Decimal("11.00")
        )
        self.assertEqual(len(rl["proposed"]["items"]), 1)
        self.assertEqual(
            Decimal(rl["proposed"]["total"]), Decimal("22.00")
        )
        # Two undecided: the free-floating $33 finding + the
        # cancelled-WO's finding ($100 est on the finding).
        self.assertEqual(len(rl["undecided"]["items"]), 2)
        self.assertEqual(
            Decimal(rl["undecided"]["total"]), Decimal("133.00")
        )
        self.assertEqual(len(rl["declined"]["items"]), 1)
        self.assertEqual(
            Decimal(rl["declined"]["total"]), Decimal("44.00")
        )
        # A finding already tracked by a live WO does NOT show up
        # again in the finding buckets.
        seen_finding_descs = {
            it["description"]
            for bucket in (
                "decided_pending",
                "proposed",
                "undecided",
                "declined",
            )
            for it in rl[bucket]["items"]
        }
        self.assertNotIn("wo-done", seen_finding_descs)
        self.assertNotIn("wo-approved", seen_finding_descs)
        self.assertNotIn("wo-inprogress", seen_finding_descs)
        self.assertNotIn("wo-otherdraft", seen_finding_descs)


class OverageUnchanged(TestCase):
    """The regression that matters — the overage is byte-identical
    before and after this change when pending findings exist. The
    breakdown is display-only; pending money never enters
    ``overage_for`` or ``recon_budget_for``.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("600.00"))
        self.vehicle = _vehicle(
            "S230-D", self.default, price=Decimal("8000.00")
        )
        self.report = _report(self.vehicle, self.default)
        self.client, self.owner = _owner_client(self.default)
        # Queued WO — $900 estimate, cap $600 → overage $300.
        f = _finding(
            self.report, self.default, est=Decimal("900"), desc="over"
        )
        self.wo = recon_service.create_work_order_from_finding(
            f, dealership=self.default, created_by=self.owner
        )
        self.wo.refresh_from_db()
        # Now pile on pending findings — a $2000 undecided,
        # $5000 must-do, $700 should-do. None have WOs. If any of
        # these leaked into the overage math, overage would change.
        _finding(
            self.report, self.default, est=Decimal("2000"), desc="pend1"
        )
        f_must = _finding(
            self.report, self.default, est=Decimal("5000"), desc="pend2"
        )
        _decide(
            f_must, self.default, RECON_DECISION_TIER_MUST_DO, self.owner
        )
        f_should = _finding(
            self.report, self.default, est=Decimal("700"), desc="pend3"
        )
        _decide(
            f_should,
            self.default,
            RECON_DECISION_TIER_SHOULD_DO,
            self.owner,
        )

    def test_overage_untouched_by_pending_findings(self):
        # Service layer — unchanged from SESSION_228.
        service_overage = recon_budget_service.overage_for(
            self.wo, dealership=self.default
        )
        self.assertEqual(service_overage, Decimal("300.00"))
        # View payload — same number.
        res = self.client.get(QUEUE_URL)
        self.assertEqual(res.status_code, 200, res.content)
        row = res.json()["queue"][0]
        self.assertEqual(row["overage"], "300.00")
        # And the budget the payload reports still comes from the
        # cap alone (no pending-finding inflation).
        self.assertEqual(row["budget"], "600.00")


class QueueQueryCountBounded(TestCase):
    """Part 4 — for a queue of three rows, the request runs a
    bounded number of queries. Two things matter:
      1. It does NOT scale linearly with the number of findings /
         WOs per car (that would be an N*M explosion in the queue view).
      2. It does not blow past the previously-shipped query budget
         by an order of magnitude when we add the recon_list.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("300.00"))
        self.client, self.owner = _owner_client(self.default)
        self.rows = []
        for i in range(3):
            v = _vehicle(
                f"S230-Q{i}", self.default, price=Decimal("8000")
            )
            report = _report(v, self.default)
            f_big = _finding(
                report, self.default, est=Decimal("700"), desc=f"big-{i}"
            )
            # Add a handful of extra findings per car to give the
            # recon_list something to iterate.
            for j in range(3):
                _finding(
                    report,
                    self.default,
                    est=Decimal("20"),
                    desc=f"extra-{i}-{j}",
                )
            wo = recon_service.create_work_order_from_finding(
                f_big, dealership=self.default, created_by=self.owner
            )
            wo.refresh_from_db()
            self.rows.append(wo)

    def test_query_count_is_bounded(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        # Warm the auth / dealership caches.
        self.client.get(QUEUE_URL)
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get(QUEUE_URL)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.json()["queue"]), 3)
        # A per-row cost of ~12-15 queries (ledger_totals + WO scan
        # + findings + overrides + budget) times 3 rows plus fixed
        # overhead lands well under 100. The bound is generous;
        # the test is guarding against runaway N+1, not policing
        # exact counts.
        self.assertLess(
            len(ctx.captured_queries),
            100,
            f"queue took {len(ctx.captured_queries)} queries; "
            "check for N+1 regression in the queue view / recon_list",
        )
