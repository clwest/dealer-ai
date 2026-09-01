"""TASK C1.1 (2026-09-01) — regression coverage for the 1,745-line
``seed_copper_canyon_auto_demo`` management command.

The seed is a fixture. This file is the instrument.

Locks the four invariants the C1 review kept discovering by hand
(TASK_c11-demo-seed-truthfulness.md item 3):

- Every :class:`Sale` has positive ``gross_realized``, and the stored
  value equals the recompute through
  :func:`services.sale.computation.gross_realized`. The C1 review
  found negative gross across the retail sales because the archetype
  double-posts an "Acquisition basis for X" :class:`VehicleCost`;
  :func:`_normalize_sale_gross` in the seed papers over that. This
  test prevents a regression that removes the workaround before the
  product-code fix (tracked in ``TASK_archetype_acquisition_double_
  count.md``) lands.
- At least two :class:`WorkOrder` rows sit in ``draft`` with a non-
  null ``estimated_cost`` and a null ``approved_at`` — the "awaiting
  authorization / over budget" pitch screen the review's original
  implementation had accidentally advanced to ``approved``.
- No lifecycle event log runs out of order — for every vehicle, the
  latest :class:`VehicleStageEvent` (by ``entered_at``) has a
  ``to_stage`` matching the vehicle's current
  :attr:`VehicleStage.current_stage`. The seed's
  :func:`_distribute_lifecycle_stages` explicitly protects this
  invariant by backdating bootstrap events; the assertion catches a
  regression that lets a bootstrap event stamped ``entered_at=now``
  post-date a manually-transitioned stage row.
- No lifecycle stage's aging snapshots are stuck all at zero — every
  stage with at least one snapshot has at least one non-zero
  ``p50_days`` reading across the 15-day backfill. Frontline was
  flat-at-zero pre-fix because ``_distribute_lifecycle_stages``
  short-circuits when ``previous_stage == stage_key``; the new
  :func:`_backdate_frontline_stage_aging` step spreads
  ``VehicleStage.entered_at`` on the five frontline units before
  :func:`_seed_stage_aging_snapshots` runs.

Plus idempotency: the seed runs from empty, runs twice without
duplicating rows, provisions its own dealership, and leaves the
default tenant alone.

Per M34 planning (idempotent seeds + rerun-safe acceptance
journeys): every other seed in the repo ships with a test file; this
one now does too.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_copper_canyon_auto_demo import (
    STORE_SLUG,
    _DELIBERATE_LOSER_STOCKS,
    _MAX_LOSER_LOSS,
)
from dealer_ai.models import (
    VEHICLE_STAGE_CHOICES,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_OFF_MARKET,
    WORK_ORDER_STATUS_DRAFT,
    Dealership,
    Delivery,
    Sale,
    SlaBreachRecord,
    StageAgingSnapshot,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
    WorkOrder,
)
from dealer_ai.services.sale.computation import gross_realized
from dealer_ai.services.tenancy import get_default_dealership


def _run_seed() -> None:
    call_command(
        "seed_copper_canyon_auto_demo", stdout=StringIO()
    )


def _demo_dealership() -> Dealership:
    return Dealership.objects.get(slug=STORE_SLUG)


class CopperCanyonAutoSeedFreshRunTests(TestCase):
    """The four TASK_c11-demo-seed-truthfulness assertions plus the
    baseline provisioning shape.
    """

    def setUp(self) -> None:
        _run_seed()

    def test_seed_provisions_the_copper_canyon_dealership(self) -> None:
        dealership = _demo_dealership()
        self.assertTrue(dealership.is_demo)
        self.assertEqual(dealership.slug, STORE_SLUG)

    def test_seed_does_not_touch_the_default_tenant(self) -> None:
        default = get_default_dealership()
        self.assertNotEqual(default.slug, STORE_SLUG)
        # Sanity: no seed data lands on the default dealership.
        self.assertEqual(
            Vehicle.objects.filter(dealership=default).count(),
            0,
        )
        self.assertEqual(
            Sale.objects.filter(dealership=default).count(), 0
        )

    def test_every_sale_has_positive_gross_realized(self) -> None:
        """Assertion 1 — signed gross with a bounded loser set.

        Reshaped by TASK_losing-deals-and-the-inventory-page
        (2026-09-01) — the pre-2026-09-01 shape asserted that
        *every* sale had positive gross, which caught the
        archetype's acquisition-basis double-count but ruled out
        deliberate losers a real dealer needs on the demo. This
        version does both jobs:

        - Every stock in :data:`_DELIBERATE_LOSER_STOCKS` has
          negative gross. A loser that quietly flipped positive is
          as much a bug as the reverse.
        - Every other sale has positive gross. That is the archetype
          double-count guard: if the workaround
          (:func:`_normalize_sale_gross`) regresses, every non-loser
          would flip negative and this fails loudly.
        - The aggregate is positive — the store as a whole makes
          money. A demo of a lot losing money is a different demo.
        - No single loss is deeper than :data:`_MAX_LOSER_LOSS`.
          The ceiling is what separates a deliberate wholesale
          disposal from the archetype double-count reappearing —
          the double-count produces losses in the multi-thousand
          range (roughly the whole purchase price), which a
          plain "some sales negative" check would miss. Removing
          the ceiling is how the original defect would sneak back.
        - :attr:`Sale.gross_realized` equals a fresh recompute via
          :func:`services.sale.computation.gross_realized`, so the
          denormalized column can't drift from the truth.
        """
        dealership = _demo_dealership()
        sales = list(
            Sale.objects.filter(dealership=dealership).select_related(
                "vehicle"
            )
        )
        self.assertGreaterEqual(
            len(sales), 5,
            "seed should produce at least the 5 archetype sales",
        )
        observed_losers: dict[str, Decimal] = {}
        aggregate = Decimal("0")
        for sale in sales:
            stock = sale.vehicle.stock_number
            aggregate += sale.gross_realized
            if stock in _DELIBERATE_LOSER_STOCKS:
                self.assertLess(
                    sale.gross_realized,
                    Decimal("0"),
                    f"Sale pk={sale.pk} (stock={stock}) is a declared "
                    f"loser but gross_realized="
                    f"{sale.gross_realized} — the loser injection in "
                    "_extend_sales_history has drifted.",
                )
                observed_losers[stock] = sale.gross_realized
            else:
                self.assertGreater(
                    sale.gross_realized,
                    Decimal("0"),
                    f"Sale pk={sale.pk} (stock={stock}) has non-"
                    f"positive gross_realized={sale.gross_realized} "
                    f"but is NOT a declared loser. Either it belongs "
                    f"in _DELIBERATE_LOSERS or the archetype-double-"
                    "count workaround has regressed.",
                )
            recomputed = gross_realized(sale)
            self.assertEqual(
                sale.gross_realized,
                recomputed,
                f"Sale pk={sale.pk} stored gross_realized="
                f"{sale.gross_realized} disagrees with fresh recompute="
                f"{recomputed}; the denormalized column is stale.",
            )
        # Every declared loser must appear as a sale.
        missing_losers = _DELIBERATE_LOSER_STOCKS - observed_losers.keys()
        self.assertEqual(
            missing_losers,
            set(),
            f"declared losers not booked as sales: {sorted(missing_losers)}. "
            "The extension range in _extend_sales_history no longer "
            "covers these stocks; move them or fix the range.",
        )
        # Aggregate positive — store makes money overall.
        self.assertGreater(
            aggregate,
            Decimal("0"),
            f"aggregate gross across {len(sales)} sales = {aggregate}. "
            "The demo store must be profitable at the aggregate; a "
            "negative total is a different demo, not this one.",
        )
        # Bounded loss — the guard against the archetype-double-count
        # bug reappearing as a "deliberate loser."
        deepest_loss = min(observed_losers.values())
        self.assertGreaterEqual(
            deepest_loss,
            -_MAX_LOSER_LOSS,
            f"deepest single loss = {deepest_loss}, exceeds the "
            f"_MAX_LOSER_LOSS ceiling of -{_MAX_LOSER_LOSS}. A loss "
            "that deep is almost certainly the archetype's "
            "acquisition-basis double-count reappearing, not a "
            "business decision — see TASK_archetype_acquisition_"
            "double_count.md.",
        )

    def test_at_least_two_work_orders_await_authorization(self) -> None:
        """Assertion 2 — draft WOs with estimated_cost and no approved_at.

        The "awaiting authorization / over budget" pitch screen. The
        C1 review's first pass at :func:`_seed_awaiting_authorization_
        wos` advanced these to ``approved`` before writing them, which
        told the opposite story.
        """
        dealership = _demo_dealership()
        draft_awaiting = WorkOrder.objects.filter(
            dealership=dealership,
            status=WORK_ORDER_STATUS_DRAFT,
            estimated_cost__isnull=False,
            approved_at__isnull=True,
        )
        self.assertGreaterEqual(
            draft_awaiting.count(),
            2,
            "expected at least 2 draft WOs awaiting authorization "
            f"(with estimated_cost and null approved_at); got "
            f"{draft_awaiting.count()}",
        )

    def test_no_vehicle_lifecycle_log_runs_backwards(self) -> None:
        """Assertion 3 — every vehicle's stage-event log ends at its
        current stage.

        Sorted by ``entered_at``, the latest event's ``to_stage``
        equals :attr:`VehicleStage.current_stage`. Guards the
        invariant :func:`_distribute_lifecycle_stages` protects by
        backdating bootstrap events.
        """
        dealership = _demo_dealership()
        stage_by_vehicle_pk = {
            row["vehicle_id"]: row["current_stage"]
            for row in VehicleStage.objects.filter(
                dealership=dealership
            ).values("vehicle_id", "current_stage")
        }
        vehicles = Vehicle.objects.filter(dealership=dealership)
        checked = 0
        for vehicle in vehicles:
            events = list(
                VehicleStageEvent.objects.filter(
                    vehicle=vehicle
                ).order_by("entered_at", "pk")
            )
            if not events:
                # A vehicle with no stage events has no log to be out
                # of order — bootstrap should always create one, so
                # note the absence explicitly rather than skipping
                # silently.
                self.fail(
                    f"vehicle stock={vehicle.stock_number} has zero "
                    "VehicleStageEvent rows; bootstrap should always "
                    "create one."
                )
            last_event = events[-1]
            current_stage = stage_by_vehicle_pk.get(vehicle.pk)
            self.assertEqual(
                last_event.to_stage,
                current_stage,
                f"vehicle stock={vehicle.stock_number} has a stage-event "
                f"log that runs out of order: latest event "
                f"to_stage={last_event.to_stage!r} but "
                f"VehicleStage.current_stage={current_stage!r}.",
            )
            checked += 1
        self.assertGreater(checked, 0)

    def test_no_stage_has_uniformly_zero_aging_snapshots(self) -> None:
        """Assertion 4 — every populated stage shows real aging signal.

        For each stage with at least one :class:`StageAgingSnapshot`
        row, at least one snapshot has ``p50_days > 0``. Frontline was
        the flagged stage pre-fix — it read flat at zero across all 15
        snapshots because the five frontline units still carried
        ``VehicleStage.entered_at`` at bootstrap time. The new
        :func:`_backdate_frontline_stage_aging` step ensures the
        aging board's most-looked-at column reads real distribution.
        """
        dealership = _demo_dealership()
        stages_with_snapshots = (
            StageAgingSnapshot.objects.filter(dealership=dealership)
            .values_list("stage", flat=True)
            .distinct()
        )
        self.assertGreater(
            stages_with_snapshots.count(),
            0,
            "expected the seed to backfill some stage-aging snapshots",
        )
        for stage in stages_with_snapshots:
            p50s = list(
                StageAgingSnapshot.objects.filter(
                    dealership=dealership, stage=stage
                ).values_list("p50_days", flat=True)
            )
            self.assertTrue(
                any(v > 0 for v in p50s),
                f"stage={stage!r} has all-zero p50_days across "
                f"{len(p50s)} snapshot(s); aging read is flat at zero.",
            )

    def test_sla_breach_record_materialized_for_stale_wo(self) -> None:
        """The seed calls :func:`detect_sla_breaches` after
        :func:`_seed_sla_stale_wo` so :class:`SlaBreachRecord` rows
        exist for the ``/admin/analytics/sla-breach-patterns/``
        endpoint to read. The verb is idempotent
        (``get_or_create`` on ``(work_order, kind, detected_at_date)``),
        but calling it at all is what was missing pre-fix.
        """
        dealership = _demo_dealership()
        breaches = SlaBreachRecord.objects.filter(dealership=dealership)
        self.assertGreaterEqual(
            breaches.count(),
            1,
            "expected at least one SlaBreachRecord row (the stale "
            "outsourced WO seeded by _seed_sla_stale_wo).",
        )

    def test_frontline_stage_row_entered_at_is_spread(self) -> None:
        """The frontline VehicleStage rows should carry ``entered_at``
        values spread across a plausible range — specifically, not
        all at seed-time (~now).

        This is the direct read of the fix
        :func:`_backdate_frontline_stage_aging` performs. Kept as a
        separate assertion from the snapshot check above because a
        future change that skips the snapshot backfill but leaves the
        stage rows correct would still be a useful demo.
        """
        dealership = _demo_dealership()
        rows = list(
            VehicleStage.objects.filter(
                dealership=dealership,
                current_stage=VEHICLE_STAGE_FRONTLINE,
            ).values_list("entered_at", flat=True)
        )
        self.assertGreaterEqual(
            len(rows), 1,
            "expected at least one frontline VehicleStage row",
        )
        distinct_dates = {ts.date() for ts in rows}
        self.assertGreater(
            len(distinct_dates),
            1,
            f"expected frontline entered_at values spread across "
            f"multiple dates; got {len(distinct_dates)} distinct "
            f"date(s) across {len(rows)} row(s).",
        )

    def test_no_frontline_vehicle_has_a_sale(self) -> None:
        """A sold unit must not sit on the front line.

        ``services/sale/computation.py::record_sale`` transitions
        ``frontline → hold_reserved`` on its own; the extension
        helper ``_originate_bhph_sale_and_note`` mirrors the same
        transition for its model-direct writes. Any frontline
        vehicle with a Sale would mean one of those hooks did not
        fire — the exact bug the sale-lifecycle rework fixed.
        """
        dealership = _demo_dealership()
        sold_on_frontline = list(
            Vehicle.objects.filter(
                dealership=dealership,
                stage__current_stage=VEHICLE_STAGE_FRONTLINE,
                sale__isnull=False,
            ).values_list("stock_number", flat=True)
        )
        self.assertEqual(
            sold_on_frontline,
            [],
            "sold vehicles found on the front line: "
            f"{sold_on_frontline}. record_sale + "
            "_originate_bhph_sale_and_note must advance the vehicle "
            "off frontline.",
        )

    # -------------------------------------------------------------------
    # Part 2 shape assertions (TASK_c2c3-lot-shape-and-demo-script.md,
    # 2026-09-01). The prior four assertions guarded truthfulness of
    # what the aging board *reads*; these four guard the *shape of the
    # lot itself* — every time the mechanics have changed, the shape
    # has regressed, and the demo script depends on the shape holding.
    # -------------------------------------------------------------------

    def test_every_lifecycle_stage_has_at_least_one_vehicle(self) -> None:
        """Assertion 5 — the aging board is a twelve-column story.

        Before this shape lock, sold vehicles moving to
        ``hold_reserved`` en masse silently emptied ``detail``,
        ``photography`` and ``wholesale_out``. Every stage in
        :data:`VEHICLE_STAGE_CHOICES` must carry at least one resident
        so the aging board reads with no blank columns.
        """
        dealership = _demo_dealership()
        expected_stages = {key for key, _label in VEHICLE_STAGE_CHOICES}
        populated = set(
            VehicleStage.objects.filter(dealership=dealership)
            .values_list("current_stage", flat=True)
            .distinct()
        )
        missing = sorted(expected_stages - populated)
        self.assertEqual(
            missing,
            [],
            f"lifecycle stages with zero vehicles: {missing!r}. "
            f"The seed must land at least one vehicle in every one of "
            f"the {len(expected_stages)} canonical stages so the aging "
            f"board reads as a full twelve-column story.",
        )

    def test_frontline_holds_more_than_a_token_count(self) -> None:
        """Assertion 6 — the front line reads like a real lot at the
        persona's sales pace, not a display case.

        Chris's rule (TASK_c2c3, 2026-09-01 answers): *"If you want
        to sell 50 cars in a month you need 50ish on the lot for
        sale and another 25-30 in recon waiting to hit the lot."*
        The Copper Canyon persona sits in that band. A frontline
        under 40 cars stops looking like a working store; the aging
        board thins out and the demo starts describing a lot that
        would be going under, not one at pace.

        The floor here is 40 — Chris's number minus a few for
        wiggle room across seed re-runs. The expansion imports
        enough CC-#### stock (see
        :data:`_EXPANSION_TARGET_UNSOLD_COUNT` in the seed) that
        the residual after prep-stage moves and extension sales
        lands ~50 at frontline.
        """
        dealership = _demo_dealership()
        frontline_count = VehicleStage.objects.filter(
            dealership=dealership,
            current_stage=VEHICLE_STAGE_FRONTLINE,
        ).count()
        self.assertGreaterEqual(
            frontline_count,
            40,
            f"frontline has {frontline_count} vehicle(s); a lot "
            f"selling at Chris's target pace needs ~50 for-sale "
            f"units on hand — floor is 40 with wiggle room.",
        )

    def test_some_sales_delivered_some_still_held(self) -> None:
        """Assertion 7 — the sold pool splits cleanly across delivered
        (``off_market``) and awaiting-funding (``hold_reserved``).

        The lot has to demo both states side by side: the delivered
        column proves the sale-to-delivery hook fires end to end, and
        the hold_reserved column is the "sold, awaiting funding" screen
        that every independent dealer has staffed live right now. A
        seed that lands all sales in one bucket loses one of the two
        stories.
        """
        dealership = _demo_dealership()
        delivered_count = (
            Sale.objects.filter(dealership=dealership)
            .filter(vehicle__stage__current_stage=VEHICLE_STAGE_OFF_MARKET)
            .count()
        )
        held_count = (
            Sale.objects.filter(dealership=dealership)
            .filter(vehicle__stage__current_stage=VEHICLE_STAGE_HOLD_RESERVED)
            .count()
        )
        self.assertGreaterEqual(
            delivered_count,
            1,
            "no delivered sales landed at off_market — "
            "_deliver_five_sales did not run, or the delivery hook did "
            "not advance the stage.",
        )
        self.assertGreaterEqual(
            held_count,
            1,
            "no sales remain at hold_reserved — the seed delivered "
            "everything and the sold-awaiting-funding screen has no "
            "resident to demo.",
        )
        # Deliveries themselves must exist for the delivered ones; the
        # stage counting alone would pass if some other seed advanced
        # a vehicle to off_market without recording a Delivery.
        self.assertEqual(
            Delivery.objects.filter(dealership=dealership).count(),
            delivered_count,
            "delivered off_market count does not match Delivery rows; "
            "one of the stage transitions ran without record_delivery.",
        )


class CopperCanyonAutoSeedIdempotencyTests(TestCase):
    """Rerun-safe: second seed leaves row counts identical."""

    def test_second_run_does_not_duplicate_rows(self) -> None:
        _run_seed()
        dealership_first = _demo_dealership()
        counts_first = {
            "vehicles": Vehicle.objects.filter(
                dealership=dealership_first
            ).count(),
            "sales": Sale.objects.filter(
                dealership=dealership_first
            ).count(),
            "work_orders": WorkOrder.objects.filter(
                dealership=dealership_first
            ).count(),
            "vehicle_stage_events": VehicleStageEvent.objects.filter(
                dealership=dealership_first
            ).count(),
            "stage_aging_snapshots": StageAgingSnapshot.objects.filter(
                dealership=dealership_first
            ).count(),
            "sla_breaches": SlaBreachRecord.objects.filter(
                dealership=dealership_first
            ).count(),
        }

        _run_seed()
        dealership_second = _demo_dealership()
        # Dealership row PK stays stable across re-runs (idempotency
        # contract from _provision_store's docstring).
        self.assertEqual(dealership_first.pk, dealership_second.pk)
        counts_second = {
            "vehicles": Vehicle.objects.filter(
                dealership=dealership_second
            ).count(),
            "sales": Sale.objects.filter(
                dealership=dealership_second
            ).count(),
            "work_orders": WorkOrder.objects.filter(
                dealership=dealership_second
            ).count(),
            "vehicle_stage_events": VehicleStageEvent.objects.filter(
                dealership=dealership_second
            ).count(),
            "stage_aging_snapshots": StageAgingSnapshot.objects.filter(
                dealership=dealership_second
            ).count(),
            "sla_breaches": SlaBreachRecord.objects.filter(
                dealership=dealership_second
            ).count(),
        }
        self.assertEqual(
            counts_first,
            counts_second,
            "row counts drifted across re-seed — seed is not "
            "idempotent.",
        )
