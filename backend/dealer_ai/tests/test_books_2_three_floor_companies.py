"""SESSION_243 books-2 guards — three floor companies, some cash held.

Per ``docs/_internal/TASK_books-2-three-floor-companies.md``:

- A car with a ``floor_plan_company`` posts credit to 210000 Floor
  Plan Payable and names the company in the memo.
- A car without a company posts credit to 100000 Cash on Hand
  (unchanged books-1 behaviour).
- ``VehicleAcquisition.is_floored`` is derived from
  ``floor_plan_company_id`` and cannot disagree (enforced in
  :meth:`VehicleAcquisition.save`).
- A floored car retires its own floor on sale — the sale-booking
  journal adds DR 210000 / CR 100000 for that car's floored
  principal.
- After a full seed, Floor Plan Payable equals the acquisition
  basis of floored cars still on the lot and nothing else.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    SALE_FINANCE_TYPE_CASH,
    SOURCE_AUCTION,
    Dealership,
    FloorPlanCompany,
    JournalEntry,
    Sale,
    Vehicle,
    VehicleAcquisition,
)
from dealer_ai.services.accounting import (
    CASH_ACCOUNT_CODE,
    FLOOR_PLAN_PAYABLE_ACCOUNT_CODE,
    USED_VEHICLE_INVENTORY_ACCOUNT_CODE,
    compute_trial_balance,
    seed_default_coa,
)
from dealer_ai.services.sale import record_sale


def _mk_vehicle(dealership: Dealership, stock: str, price: str = "18000.00") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        make="Ford",
        model="F-150",
        price=Decimal(price),
        dealership=dealership,
    )


def _mk_company(
    dealership: Dealership,
    *,
    name: str = "Desert Peak Capital",
    code: str = "DPC",
    apr: str = "0.0850",
) -> FloorPlanCompany:
    return FloorPlanCompany.objects.create(
        dealership=dealership,
        name=name,
        code=code,
        apr=Decimal(apr),
        is_active=True,
    )


class FloorPlanCompanyOnAcquisitionTests(TestCase):
    """The FK drives the credit side + memo; is_floored is derived."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="b2-fk", name="Books-2 FK Panel"
        )
        seed_default_coa(self.dealership)
        self.company = _mk_company(self.dealership)

    def test_cash_acquisition_when_no_company(self) -> None:
        vehicle = _mk_vehicle(self.dealership, "CC-201")
        acq = VehicleAcquisition.objects.create(
            dealership=self.dealership,
            vehicle=vehicle,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("12800.00"),
            purchase_date=dt.date(2026, 8, 1),
        )
        # is_floored is derived — no company means False.
        self.assertFalse(acq.is_floored)
        self.assertIsNone(acq.floor_plan_company_id)
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith=f"Acquired #{vehicle.stock_number}",
        ).get()
        self.assertTrue(
            entry.lines.filter(account__code=CASH_ACCOUNT_CODE).exists()
        )
        self.assertFalse(
            entry.lines.filter(
                account__code=FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
            ).exists()
        )

    def test_floored_acquisition_credits_floor_plan_with_company_memo(self) -> None:
        vehicle = _mk_vehicle(self.dealership, "CC-202")
        acq = VehicleAcquisition.objects.create(
            dealership=self.dealership,
            vehicle=vehicle,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("14200.00"),
            purchase_date=dt.date(2026, 8, 1),
            floor_plan_company=self.company,
        )
        # is_floored is derived — a company means True.
        self.assertTrue(acq.is_floored)
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith=f"Acquired #{vehicle.stock_number}",
        ).get()
        floor_line = entry.lines.get(
            account__code=FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
        )
        self.assertEqual(floor_line.credit, Decimal("14200.00"))
        # Company name AND short code land in the memo — like a
        # bookkeeper wrote it.
        self.assertIn(self.company.name, floor_line.memo)
        self.assertIn(self.company.code, floor_line.memo)

    def test_save_forces_is_floored_to_match_fk(self) -> None:
        """Any caller-supplied ``is_floored`` is overridden on save."""
        vehicle = _mk_vehicle(self.dealership, "CC-203")
        # Legacy caller sets is_floored=True but no FK. save() forces
        # it back to False. The two cannot disagree.
        acq = VehicleAcquisition(
            dealership=self.dealership,
            vehicle=vehicle,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("11000.00"),
            purchase_date=dt.date(2026, 8, 1),
        )
        acq.is_floored = True
        acq.save()
        acq.refresh_from_db()
        self.assertFalse(acq.is_floored)
        self.assertIsNone(acq.floor_plan_company_id)

    def test_assigning_company_flips_is_floored_on_save(self) -> None:
        vehicle = _mk_vehicle(self.dealership, "CC-204")
        acq = VehicleAcquisition.objects.create(
            dealership=self.dealership,
            vehicle=vehicle,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15500.00"),
            purchase_date=dt.date(2026, 8, 1),
        )
        self.assertFalse(acq.is_floored)
        acq.floor_plan_company = self.company
        acq.save()
        acq.refresh_from_db()
        self.assertTrue(acq.is_floored)


class SaleRetiresItsOwnFloorTests(TestCase):
    """A floored car that sells retires its own floor.

    ``post_sale_booking_journal`` adds DR 210000 / CR 100000 for the
    car's floored principal so the payable does not merely grow.
    """

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="b2-payoff", name="Books-2 Payoff"
        )
        seed_default_coa(self.dealership)
        self.company = _mk_company(self.dealership)

    def _record_sale(self, stock: str, *, principal: str, floored: bool) -> Sale:
        vehicle = _mk_vehicle(self.dealership, stock, price="20000.00")
        VehicleAcquisition.objects.create(
            dealership=self.dealership,
            vehicle=vehicle,
            source=SOURCE_AUCTION,
            purchase_price=Decimal(principal),
            purchase_date=dt.date(2026, 8, 1),
            floor_plan_company=self.company if floored else None,
        )
        return record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 15),
            sold_price=Decimal("18500.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )

    def test_sale_of_floored_car_includes_payoff_pair(self) -> None:
        sale = self._record_sale("PO-01", principal="12000.00", floored=True)
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        # DR 210000 for the acquisition basis.
        floor_dr = entry.lines.get(
            account__code=FLOOR_PLAN_PAYABLE_ACCOUNT_CODE,
            debit=Decimal("12000.00"),
        )
        self.assertIn(self.company.name, floor_dr.memo)
        # CR 100000 for the same amount — the payoff.
        cash_lines = entry.lines.filter(account__code=CASH_ACCOUNT_CODE)
        payoff_cr = cash_lines.filter(credit=Decimal("12000.00")).get()
        self.assertEqual(payoff_cr.memo, "Floor plan payoff on sale")

    def test_sale_of_cash_car_has_no_payoff_pair(self) -> None:
        sale = self._record_sale("PO-02", principal="9500.00", floored=False)
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        self.assertFalse(
            entry.lines.filter(
                account__code=FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
            ).exists()
        )


class FloorPlanPayableInvariantTests(TestCase):
    """Guard the books-2 headline invariant.

    After a full mixed sequence, ``210000 Floor Plan Payable`` on the
    trial balance equals the acquisition basis of floored cars still
    on the lot and nothing else. If the payoff pair ever gets
    dropped, this test goes red before an operator ever sees a
    lying report.
    """

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="b2-invariant", name="Books-2 Invariant"
        )
        seed_default_coa(self.dealership)
        self.company = _mk_company(self.dealership)

    def test_payable_equals_unsold_floored_basis(self) -> None:
        # Five floored acquisitions with different bases.
        principals = [
            Decimal("12000.00"),
            Decimal("15500.00"),
            Decimal("9800.00"),
            Decimal("18200.00"),
            Decimal("11400.00"),
        ]
        acquisitions: list[VehicleAcquisition] = []
        for i, principal in enumerate(principals):
            vehicle = _mk_vehicle(self.dealership, f"INV-{i:02d}")
            acquisitions.append(
                VehicleAcquisition.objects.create(
                    dealership=self.dealership,
                    vehicle=vehicle,
                    source=SOURCE_AUCTION,
                    purchase_price=principal,
                    purchase_date=dt.date(2026, 8, 1),
                    floor_plan_company=self.company,
                )
            )
        # Also one cash car — its sale must not touch 210000.
        cash_vehicle = _mk_vehicle(self.dealership, "INV-99")
        VehicleAcquisition.objects.create(
            dealership=self.dealership,
            vehicle=cash_vehicle,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("8000.00"),
            purchase_date=dt.date(2026, 8, 1),
        )

        # Sell three of the floored cars + the cash car. Two floored
        # cars stay on the lot.
        record_sale(
            acquisitions[0].vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 15),
            sold_price=Decimal("15000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        record_sale(
            acquisitions[2].vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 16),
            sold_price=Decimal("13000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        record_sale(
            acquisitions[4].vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 17),
            sold_price=Decimal("14500.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        record_sale(
            cash_vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 18),
            sold_price=Decimal("10500.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )

        # Cars still on the lot: acquisitions[1] ($15,500) and
        # acquisitions[3] ($18,200). Sum = $33,700.
        expected_payable = Decimal("15500.00") + Decimal("18200.00")

        tb = compute_trial_balance(dealership=self.dealership)
        payable_row = next(
            (
                r
                for r in tb.rows
                if r.account_code == FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
            ),
            None,
        )
        self.assertIsNotNone(payable_row)
        # 210000 is a liability — natural balance is credit-normal.
        self.assertEqual(
            payable_row.natural_balance, expected_payable,
            (
                "210000 Floor Plan Payable must equal the acquisition "
                "basis of floored cars still on the lot and nothing "
                "else. If this drifts, the sale-time payoff pair "
                "in ``post_sale_booking_journal`` has drifted."
            ),
        )
