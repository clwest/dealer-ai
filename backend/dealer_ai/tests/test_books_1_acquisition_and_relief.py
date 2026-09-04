"""SESSION_241 books-1 guards — acquisition posts, sale relieves inventory.

Per ``docs/_internal/TASK_books-1-acquisition-and-relief.md`` §6:

- A test that fails if any sale booking credits 122000 Recon WIP for
  the full basis (the pre-fix pattern that drove RWIP to -$379,854
  on the demo trial balance).
- A test that an acquisition without a posting cannot exist — enforced
  via the ``post_save`` receiver on :class:`VehicleAcquisition`
  registered in :func:`dealer_ai.apps.DealerAiConfig.ready`.

Both guards target real business state through the shipped service
verbs, not implementation details.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_PARTS,
    SALE_FINANCE_TYPE_CASH,
    SOURCE_AUCTION,
    SOURCE_TRADE,
    Dealership,
    FloorPlanCompany,
    JournalEntry,
    Sale,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from dealer_ai.services.accounting import (
    CASH_ACCOUNT_CODE,
    FLOOR_PLAN_PAYABLE_ACCOUNT_CODE,
    RECON_WIP_ACCOUNT_CODE,
    USED_VEHICLE_INVENTORY_ACCOUNT_CODE,
    compute_trial_balance,
    post_vehicle_cost_journal,
    seed_default_coa,
)
from dealer_ai.services.sale import record_sale


def _mk_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        make="Chevrolet",
        model="Silverado",
        price=Decimal("18000.00"),
        dealership=dealership,
    )


def _mk_acquisition(
    dealership: Dealership,
    vehicle: Vehicle,
    *,
    price: str = "12000.00",
    source: str = SOURCE_AUCTION,
    is_floored: bool = False,
    floor_plan_company: FloorPlanCompany | None = None,
) -> VehicleAcquisition:
    # SESSION_243 books-2 — ``is_floored`` is now derived from the FK
    # inside ``VehicleAcquisition.save``. Legacy callers that passed
    # ``is_floored=True`` without a company get one lazily so the JE
    # still lands on 210000 Floor Plan Payable.
    if is_floored and floor_plan_company is None:
        floor_plan_company, _ = FloorPlanCompany.objects.get_or_create(
            dealership=dealership,
            name="Books-1 legacy test panel",
            defaults={
                "code": "TEST",
                "apr": Decimal("0.0900"),
            },
        )
    return VehicleAcquisition.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        source=source,
        purchase_price=Decimal(price),
        purchase_date=dt.date(2026, 8, 1),
        floor_plan_company=floor_plan_company,
    )


class AcquisitionSignalPostsJournalTests(TestCase):
    """Every acquisition on a COA-seeded tenant posts its journal."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="b1-acq-signal", name="Books-1 Acquisition Signal"
        )
        seed_default_coa(self.dealership)

    def test_cash_acquisition_posts_dr_inventory_cr_cash(self) -> None:
        vehicle = _mk_vehicle(self.dealership, "CC-081")
        acq = _mk_acquisition(self.dealership, vehicle, price="12800.00")

        # posted_at set inside the signal → guard for "no acquisition
        # without a posting."
        acq.refresh_from_db()
        self.assertIsNotNone(acq.posted_at)

        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith=f"Acquired #{vehicle.stock_number}",
        ).get()
        inventory_line = entry.lines.get(
            account__code=USED_VEHICLE_INVENTORY_ACCOUNT_CODE
        )
        cash_line = entry.lines.get(account__code=CASH_ACCOUNT_CODE)
        self.assertEqual(inventory_line.debit, Decimal("12800.00"))
        self.assertEqual(cash_line.credit, Decimal("12800.00"))
        # No floor plan touch on a cash acquisition.
        self.assertFalse(
            entry.lines.filter(
                account__code=FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
            ).exists()
        )

    def test_floored_acquisition_credits_floor_plan_payable(self) -> None:
        vehicle = _mk_vehicle(self.dealership, "CC-082")
        _mk_acquisition(
            self.dealership,
            vehicle,
            price="14200.00",
            is_floored=True,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith=f"Acquired #{vehicle.stock_number}",
        ).get()
        # Floor plan line present; cash line absent.
        floor_line = entry.lines.get(
            account__code=FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
        )
        self.assertEqual(floor_line.credit, Decimal("14200.00"))
        self.assertFalse(
            entry.lines.filter(account__code=CASH_ACCOUNT_CODE).exists()
        )

    def test_signal_is_idempotent_on_resave(self) -> None:
        vehicle = _mk_vehicle(self.dealership, "CC-083")
        acq = _mk_acquisition(self.dealership, vehicle, price="9800.00")
        entries_first = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith=f"Acquired #{vehicle.stock_number}",
        ).count()
        # Save again (update path) — the receiver only fires on
        # ``created=True``, and the verb also refuses when
        # ``posted_at`` is populated. Belt + suspenders.
        acq.notes = "changed"
        acq.save()
        entries_second = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith=f"Acquired #{vehicle.stock_number}",
        ).count()
        self.assertEqual(entries_first, entries_second)
        self.assertEqual(entries_first, 1)

    def test_description_reads_like_a_bookkeeper_wrote_it(self) -> None:
        # Task §7 — no milestone numbers in the entries this child
        # writes; the shape should read as
        # "Acquired #<stock> — <year make model> — <source label>".
        vehicle = _mk_vehicle(self.dealership, "CC-084")
        _mk_acquisition(self.dealership, vehicle, price="10500.00")
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith="Acquired #CC-084",
        ).get()
        self.assertNotIn("M2", entry.description)
        self.assertNotIn("M9", entry.description)
        self.assertNotIn("M13", entry.description)
        self.assertIn("Chevrolet", entry.description)
        self.assertIn("Silverado", entry.description)


class SaleNeverCreditsReconWipForFullBasisTests(TestCase):
    """Guard: no sale-booking line credits 122000 for total_investment."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="b1-relief-guard", name="Books-1 Sale Relief Guard"
        )
        seed_default_coa(self.dealership)

    def _record_sale_with_recon(self, stock: str) -> Sale:
        vehicle = _mk_vehicle(self.dealership, stock)
        _mk_acquisition(
            self.dealership, vehicle, price="10000.00", source=SOURCE_TRADE
        )
        # $500 of recon spend → RWIP transfer amount is 500. Post it
        # through the M13.2 verb so RWIP actually carries the debit
        # before the sale-booking journal fires the transfer credit.
        cost = VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            category=CATEGORY_PARTS,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
        post_vehicle_cost_journal(
            dealership=self.dealership, vehicle_cost=cost
        )
        return record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 15),
            sold_price=Decimal("14500.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )

    def test_sale_never_credits_rwip_for_full_basis(self) -> None:
        sale = self._record_sale_with_recon("B1-GUARD-A")
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        rwip_lines = entry.lines.filter(
            account__code=RECON_WIP_ACCOUNT_CODE
        )
        # Exactly one RWIP line — the credit that clears this car's
        # recon spend into inventory ($500). Never a credit for the
        # $10,500 full basis (the pre-fix pattern).
        self.assertEqual(rwip_lines.count(), 1)
        rwip_line = rwip_lines.get()
        self.assertEqual(rwip_line.credit, Decimal("500.00"))
        # Full basis relief is on inventory, not RWIP.
        inventory_credit = entry.lines.get(
            account__code=USED_VEHICLE_INVENTORY_ACCOUNT_CODE,
            credit=Decimal("10500.00"),
        )
        self.assertEqual(inventory_credit.debit, Decimal("0.00"))

    def test_trial_balance_rwip_stays_flat_after_sale(self) -> None:
        # Under the pre-fix behavior, this store would show RWIP as
        # a $10,500 debit-side asset (net negative on the natural
        # balance). Post-fix: RWIP washes to zero — the $500 recon
        # in offset the $500 clear on sale.
        self._record_sale_with_recon("B1-GUARD-B")
        tb = compute_trial_balance(dealership=self.dealership)
        rwip_row = next(
            (r for r in tb.rows if r.account_code == RECON_WIP_ACCOUNT_CODE),
            None,
        )
        # Either no row (no net activity) or net-zero natural balance.
        if rwip_row is not None:
            self.assertEqual(rwip_row.natural_balance, Decimal("0.00"))
        # Inventory shows a credit-side natural balance equal to the
        # sale's gross-of-basis: acquisition + recon in ($10,500),
        # relief out ($10,500) → net zero for the sold car. No
        # other activity on this tenant, so inventory nets to zero.
        inv_row = next(
            (
                r
                for r in tb.rows
                if r.account_code == USED_VEHICLE_INVENTORY_ACCOUNT_CODE
            ),
            None,
        )
        if inv_row is not None:
            self.assertEqual(inv_row.natural_balance, Decimal("0.00"))
