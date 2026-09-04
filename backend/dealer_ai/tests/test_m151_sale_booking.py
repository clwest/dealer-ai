"""Sale-booking GL post tests — receivable + revenue + inventory relief.

SESSION_241 books-1 refit: COGS now relieves 121000 Used Vehicle
Inventory (never 122000 Recon Work in Process). When the sold car
carries recon spend, the sale-booking entry also transfers the
recon amount from RWIP into inventory (DR 121000 / CR 122000)
before the COGS relief. RWIP only ever holds open recon-in-progress
after a sale — never a negative balance.

Coverage:

- Cash finance-type → 100000 debit + 400000 credit.
- Retail finance-type → 120000 debit + 400000 credit.
- BHPH finance-type → 123000 debit + 400000 credit.
- COGS pair uses 500000 debit + 121000 credit for
  ``total_investment``.
- Recon-carrying sale posts the RWIP → Inventory transfer alongside
  the COGS pair; RWIP is left flat.
- No sale-booking line ever credits 122000 Recon WIP for the full
  basis (the pre-fix behavior that drove RWIP negative).
- Balanced double-entry (even with the transfer lines).
- Cross-tenant Sale guard.
- Zero-total-investment path — revenue-only, warning.
- Un-posted VehicleCost flush.
- Missing default account raises ``MissingDefaultAccountError``.
- ``UnmappedFinanceTypeError`` raises when finance-type has no
  receivable-account mapping.
- ``posted_by_user`` propagation from view through service into
  JournalEntry FK.
- Atomic sibling posture — sale-booking failure rolls back the Sale
  row.
- Idempotency: second ``record_sale`` on same Vehicle raises
  ``SaleAlreadyExistsError`` BEFORE any GL work.
- M14.3 list endpoint returns the new sale-booking entries with
  ``posted_by_username`` populated.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    CATEGORY_PARTS,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    SOURCE_AUCTION,
    Dealership,
    GLAccount,
    JournalEntry,
    Sale,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from dealer_ai.services.accounting import (
    BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE,
    CASH_ACCOUNT_CODE,
    CONTRACTS_IN_TRANSIT_ACCOUNT_CODE,
    COST_OF_VEHICLE_SALES_ACCOUNT_CODE,
    RECON_WIP_ACCOUNT_CODE,
    USED_VEHICLE_INVENTORY_ACCOUNT_CODE,
    VEHICLE_SALES_RETAIL_ACCOUNT_CODE,
    CrossTenantGLAccountError,
    MissingDefaultAccountError,
    UnmappedFinanceTypeError,
    post_sale_booking_journal,
    seed_default_coa,
)
from dealer_ai.services.sale import (
    SaleAlreadyExistsError,
    record_sale,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)

User = get_user_model()


def _seed_vehicle_with_investment(
    dealership: Dealership,
    *,
    stock: str = "M151-1",
    purchase_price: str = "20000.00",
    extra_costs: list[str] | None = None,
    unposted_extras: list[str] | None = None,
) -> Vehicle:
    """Create a Vehicle with an acquisition + optional posted / unposted costs.

    ``extra_costs`` land as already-posted VehicleCost rows (via
    inline ``posted_at`` on save). ``unposted_extras`` land as
    ``posted_at=None`` rows — exercises the §5.d flush path.
    """
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("28000.00"),
        dealership=dealership,
    )
    VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal(purchase_price),
        purchase_date=dt.date(2026, 6, 1),
    )
    for amt in extra_costs or []:
        cost = VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_PARTS,
            amount=Decimal(amt),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
        # Mark as already posted so the §5.d flush skips it.
        cost.posted_at = timezone.now()
        cost.save(update_fields=["posted_at"])
    for amt in unposted_extras or []:
        VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_PARTS,
            amount=Decimal(amt),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
    return vehicle


def _get_line(entry: JournalEntry, *, account_code: str):
    return entry.lines.get(account__code=account_code)


class FinanceTypeMappingTests(TestCase):
    """§5.b Option A — receivable account picked by finance_type."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-fint", name="M15.1 Finance-type Test"
        )
        seed_default_coa(self.dealership)

    def test_cash_sale_debits_cash_account(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-CASH", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        receivable_line = _get_line(entry, account_code=CASH_ACCOUNT_CODE)
        self.assertEqual(receivable_line.debit, Decimal("25000.00"))
        self.assertEqual(receivable_line.credit, Decimal("0.00"))

    def test_retail_sale_debits_contracts_in_transit(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-RET", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
            lender_name="First National",
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        receivable_line = _get_line(
            entry, account_code=CONTRACTS_IN_TRANSIT_ACCOUNT_CODE
        )
        self.assertEqual(receivable_line.debit, Decimal("25000.00"))
        self.assertIn("First National", receivable_line.memo)

    def test_bhph_sale_debits_bhph_notes_receivable(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-BHPH", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_BHPH,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        receivable_line = _get_line(
            entry, account_code=BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE
        )
        self.assertEqual(receivable_line.debit, Decimal("25000.00"))


class RevenueAndCogsLineTests(TestCase):
    """Revenue always credits 400000; COGS uses 500000 / 122000 pair."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-rc", name="M15.1 Revenue+COGS"
        )
        seed_default_coa(self.dealership)

    def test_revenue_line_credits_vehicle_sales_retail(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-REV", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        revenue_line = _get_line(
            entry, account_code=VEHICLE_SALES_RETAIL_ACCOUNT_CODE
        )
        self.assertEqual(revenue_line.credit, Decimal("25000.00"))
        self.assertEqual(revenue_line.debit, Decimal("0.00"))

    def test_cogs_pair_uses_500000_and_121000(self) -> None:
        # purchase 20,000 → total_investment 20,000 (no recon) →
        # COGS pair posts DR 500000 20,000 / CR 121000 20,000. No
        # transfer line because the car had no VehicleCost.
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-COGS", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        cogs_line = _get_line(
            entry, account_code=COST_OF_VEHICLE_SALES_ACCOUNT_CODE
        )
        inventory_line = _get_line(
            entry, account_code=USED_VEHICLE_INVENTORY_ACCOUNT_CODE
        )
        self.assertEqual(cogs_line.debit, Decimal("20000.00"))
        self.assertEqual(inventory_line.credit, Decimal("20000.00"))

    def test_no_sale_line_credits_recon_wip_when_no_recon(self) -> None:
        # SESSION_241 books-1 guard — the sale-booking journal must
        # never credit 122000 for the full basis. A car with no recon
        # produces no RWIP touch at all.
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-NORWIP", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        rwip_lines = entry.lines.filter(account__code=RECON_WIP_ACCOUNT_CODE)
        self.assertEqual(rwip_lines.count(), 0)

    def test_recon_bearing_sale_transfers_rwip_to_inventory(self) -> None:
        # A car with $2,000 of recon posts a transfer pair
        # (DR 121000 2,000 / CR 122000 2,000) alongside the COGS pair
        # (DR 500000 17,000 / CR 121000 17,000). Total inventory
        # activity nets to a $15,000 credit (in - out) for this car.
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-RECON",
            purchase_price="15000.00",
            extra_costs=["800.00", "1200.00"],
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("22000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        rwip_lines = entry.lines.filter(
            account__code=RECON_WIP_ACCOUNT_CODE
        )
        # Exactly one RWIP line — the credit that clears the recon
        # spend into inventory. Never a credit for the full basis.
        self.assertEqual(rwip_lines.count(), 1)
        rwip_line = rwip_lines.get()
        self.assertEqual(rwip_line.credit, Decimal("2000.00"))
        self.assertEqual(rwip_line.debit, Decimal("0.00"))

        # Inventory line count: two — the transfer debit AND the COGS
        # credit for the full basis.
        inv_lines = entry.lines.filter(
            account__code=USED_VEHICLE_INVENTORY_ACCOUNT_CODE
        )
        self.assertEqual(inv_lines.count(), 2)
        inv_debit = sum(
            (ln.debit for ln in inv_lines), Decimal("0.00")
        )
        inv_credit = sum(
            (ln.credit for ln in inv_lines), Decimal("0.00")
        )
        self.assertEqual(inv_debit, Decimal("2000.00"))
        self.assertEqual(inv_credit, Decimal("17000.00"))

    def test_entry_is_balanced(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-BAL",
            purchase_price="15000.00",
            extra_costs=["800.00", "1200.00"],
        )
        # total_investment 15,000 + 800 + 1,200 = 17,000; recon = 2,000.
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("22000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        totals_debit = sum((ln.debit for ln in entry.lines.all()), Decimal("0.00"))
        totals_credit = sum(
            (ln.credit for ln in entry.lines.all()), Decimal("0.00")
        )
        self.assertEqual(totals_debit, totals_credit)
        # DR 22k receivable + DR 17k COGS + DR 2k transfer = 41k.
        self.assertEqual(totals_debit, Decimal("41000.00"))


class ZeroCostBasisPathTests(TestCase):
    """§5.c Option A — no total_investment → skip COGS pair, warn."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-zero", name="M15.1 Zero-Cost"
        )
        seed_default_coa(self.dealership)

    def test_zero_investment_skips_cogs_pair(self) -> None:
        # No VehicleAcquisition + no VehicleCost → total_investment == 0.
        vehicle = Vehicle.objects.create(
            stock_number="M151-ZERO",
            year=2024,
            model="Bronco",
            price=Decimal("30000.00"),
            dealership=self.dealership,
        )
        with self.assertLogs(
            "dealer_ai.accounting.sale_booking", level="WARNING"
        ):
            sale = record_sale(
                vehicle,
                dealership=self.dealership,
                sale_date=dt.date(2026, 8, 1),
                sold_price=Decimal("28000.00"),
                finance_type=SALE_FINANCE_TYPE_CASH,
            )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        # Only 2 lines — revenue pair only, no COGS pair.
        self.assertEqual(entry.lines.count(), 2)
        codes = set(entry.lines.values_list("account__code", flat=True))
        self.assertEqual(
            codes,
            {CASH_ACCOUNT_CODE, VEHICLE_SALES_RETAIL_ACCOUNT_CODE},
        )

    def test_zero_investment_entry_balances_revenue_only(self) -> None:
        vehicle = Vehicle.objects.create(
            stock_number="M151-ZBAL",
            year=2024,
            model="Bronco",
            price=Decimal("30000.00"),
            dealership=self.dealership,
        )
        with self.assertLogs(
            "dealer_ai.accounting.sale_booking", level="WARNING"
        ):
            sale = record_sale(
                vehicle,
                dealership=self.dealership,
                sale_date=dt.date(2026, 8, 1),
                sold_price=Decimal("28000.00"),
                finance_type=SALE_FINANCE_TYPE_RETAIL,
            )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        totals_debit = sum((ln.debit for ln in entry.lines.all()), Decimal("0.00"))
        totals_credit = sum(
            (ln.credit for ln in entry.lines.all()), Decimal("0.00")
        )
        self.assertEqual(totals_debit, Decimal("28000.00"))
        self.assertEqual(totals_credit, Decimal("28000.00"))


class UnpostedCostFlushTests(TestCase):
    """§5.d Option A — unposted VehicleCost rows flush inside record_sale."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-flush", name="M15.1 Flush"
        )
        seed_default_coa(self.dealership)

    def test_unposted_costs_post_before_sale_booking(self) -> None:
        # Two unposted costs on the vehicle. record_sale must flush
        # them via post_vehicle_cost_journal before the sale-booking
        # journal fires.
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-FLUSH",
            purchase_price="20000.00",
            unposted_extras=["500.00", "300.00"],
        )
        # Sanity: two costs are unposted before the sale.
        unposted_before = VehicleCost.objects.filter(
            vehicle=vehicle, posted_at__isnull=True
        ).count()
        self.assertEqual(unposted_before, 2)

        record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("28000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )

        # All costs now posted.
        unposted_after = VehicleCost.objects.filter(
            vehicle=vehicle, posted_at__isnull=True
        ).count()
        self.assertEqual(unposted_after, 0)
        # Four journal entries created: one acquisition JE (posted by
        # the SESSION_241 books-1 post_save signal on
        # VehicleAcquisition), two M13.2 cost accruals, and one
        # sale-booking entry.
        entries = JournalEntry.objects.filter(dealership=self.dealership)
        self.assertEqual(entries.count(), 4)

    def test_flush_scoped_to_this_vehicle_only(self) -> None:
        # A second vehicle with its own unposted cost — flush must
        # not touch it.
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-FLUSH-A",
            purchase_price="20000.00",
            unposted_extras=["500.00"],
        )
        other_vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-FLUSH-B",
            purchase_price="20000.00",
            unposted_extras=["700.00"],
        )
        record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        # `vehicle`'s cost posted; `other_vehicle`'s cost still unposted.
        self.assertEqual(
            VehicleCost.objects.filter(
                vehicle=vehicle, posted_at__isnull=True
            ).count(),
            0,
        )
        self.assertEqual(
            VehicleCost.objects.filter(
                vehicle=other_vehicle, posted_at__isnull=True
            ).count(),
            1,
        )


class CrossTenantGuardTests(TestCase):
    """Direct-call cross-tenant guard on post_sale_booking_journal."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-ct-a", name="Tenant A"
        )
        self.other = Dealership.objects.create(
            slug="m151-ct-b", name="Tenant B"
        )
        seed_default_coa(self.dealership)
        seed_default_coa(self.other)

    def test_cross_tenant_sale_raises(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership, stock="M151-CT", purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        # Mutate in memory to simulate a mis-scoped direct call.
        sale.dealership = self.other
        with self.assertRaises(CrossTenantGLAccountError):
            post_sale_booking_journal(
                dealership=self.dealership, sale=sale
            )


class MissingAccountErrorTests(TestCase):
    """Broken-invariant guard — a required COA account absent → error."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-miss", name="M15.1 Missing"
        )
        seed_default_coa(self.dealership)

    def test_missing_cash_account_raises(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-MISS",
            purchase_price="20000.00",
        )
        GLAccount.objects.filter(
            dealership=self.dealership, code=CASH_ACCOUNT_CODE
        ).update(is_active=False)
        sale = Sale.objects.create(
            dealership=self.dealership,
            vehicle=vehicle,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("5000.00"),
        )
        with self.assertRaises(MissingDefaultAccountError):
            post_sale_booking_journal(
                dealership=self.dealership, sale=sale
            )


class UnmappedFinanceTypeErrorTests(TestCase):
    """Broken-invariant guard — a finance_type without receivable mapping."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-unmapped", name="M15.1 Unmapped"
        )
        seed_default_coa(self.dealership)

    def test_unmapped_finance_type_raises(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-UNMAPPED",
            purchase_price="20000.00",
        )
        # Bypass record_sale (which validates finance_type against
        # SALE_FINANCE_TYPE_CHOICES) and craft a Sale with an
        # unmapped value directly, so we can exercise the sibling-
        # service verb's broken-invariant path.
        sale = Sale.objects.create(
            dealership=self.dealership,
            vehicle=vehicle,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("5000.00"),
        )
        sale.finance_type = "lease"  # not in _FINANCE_TYPE_TO_RECEIVABLE_CODE
        with self.assertRaises(UnmappedFinanceTypeError):
            post_sale_booking_journal(
                dealership=self.dealership, sale=sale
            )


class PostedByUserPropagationTests(TestCase):
    """§7 M15.1 — request.user propagates through record_sale into the JournalEntry."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-user", name="M15.1 User"
        )
        seed_default_coa(self.dealership)

    def test_posted_by_user_propagates_to_journal_entry(self) -> None:
        user = User.objects.create_user(
            username="m151-poster",
            email="m151-poster@example.com",
            password="x",
        )
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-USR",
            purchase_price="20000.00",
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            posted_by_user=user,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        self.assertEqual(entry.posted_by_user_id, user.pk)

    def test_default_posted_by_user_is_none(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-USR-NONE",
            purchase_price="20000.00",
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale.pk}",
        ).get()
        self.assertIsNone(entry.posted_by_user_id)


class AtomicRollbackTests(TestCase):
    """§7 M15.1 — sale-booking failure rolls back the Sale row."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-atom", name="M15.1 Atomic"
        )
        seed_default_coa(self.dealership)

    def test_sale_booking_failure_rolls_back_sale(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-ATOM",
            purchase_price="20000.00",
        )
        with patch(
            "dealer_ai.services.sale.computation.post_sale_booking_journal",
            side_effect=RuntimeError("simulated GL failure"),
        ):
            with self.assertRaises(RuntimeError):
                record_sale(
                    vehicle,
                    dealership=self.dealership,
                    sale_date=dt.date(2026, 8, 1),
                    sold_price=Decimal("25000.00"),
                    finance_type=SALE_FINANCE_TYPE_CASH,
                )
        # Sale row should not exist — atomic block rolled back.
        self.assertEqual(
            Sale.objects.filter(vehicle=vehicle).count(), 0
        )
        # No sale-booking journal entry either. The acquisition JE
        # (posted by the books-1 post_save signal on VehicleAcquisition
        # creation) is unrelated and stays committed — the rollback is
        # scoped to record_sale's atomic block.
        self.assertEqual(
            JournalEntry.objects.filter(
                dealership=self.dealership,
                description__startswith="Sold #",
            ).count(),
            0,
        )


class IdempotencyShortCircuitTests(TestCase):
    """§7 M15.1 — SaleAlreadyExistsError short-circuits BEFORE GL work."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m151-idem", name="M15.1 Idempotency"
        )
        seed_default_coa(self.dealership)

    def test_duplicate_sale_does_not_double_post(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-IDEM",
            purchase_price="20000.00",
        )
        record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        entries_before = JournalEntry.objects.filter(
            dealership=self.dealership
        ).count()
        with self.assertRaises(SaleAlreadyExistsError):
            record_sale(
                vehicle,
                dealership=self.dealership,
                sale_date=dt.date(2026, 8, 15),
                sold_price=Decimal("27000.00"),
                finance_type=SALE_FINANCE_TYPE_RETAIL,
            )
        entries_after = JournalEntry.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(entries_before, entries_after)


class ListEndpointSurfaceTests(TestCase):
    """M14.3 list endpoint surfaces the M15.1 entries with posted_by_username."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m151-ep")
        self.user = make_user(username="m151-ep-user")
        make_membership(
            user=self.user, dealership=self.dealership, role="sales_manager"
        )
        self.client = authenticated_client(self.user)

    def test_sale_booking_entry_appears_in_admin_list(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-EP",
            purchase_price="20000.00",
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
            posted_by_user=self.user,
        )
        response = self.client.get(
            reverse("dealer_ai:admin-journal-entry-list")
        )
        self.assertEqual(response.status_code, 200)
        entries = response.json()["journal_entries"]["entries"]
        # Find the sale-booking entry among the results.
        matching = [
            e for e in entries if f"Sale #{sale.pk}" in e["description"]
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(
            matching[0]["posted_by_username"], self.user.username
        )


class SaleCreateEndpointPropagationTests(TestCase):
    """M9 create endpoint propagates request.user into JournalEntry.posted_by_user."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m151-endp")
        self.user = make_user(username="m151-endp-user")
        make_membership(
            user=self.user, dealership=self.dealership, role="sales_manager"
        )
        self.client = authenticated_client(self.user)

    def test_endpoint_populates_posted_by_user_fk(self) -> None:
        vehicle = _seed_vehicle_with_investment(
            self.dealership,
            stock="M151-EPCR",
            purchase_price="20000.00",
        )
        response = self.client.post(
            reverse(
                "dealer_ai:admin-sale-create",
                kwargs={"stock_number": vehicle.stock_number},
            ),
            data={
                "sale_date": "2026-08-01",
                "sold_price": "25000.00",
                "finance_type": SALE_FINANCE_TYPE_CASH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        sale_pk = response.json()["sale"]["id"]
        entry = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__contains=f"Sale #{sale_pk}",
        ).get()
        self.assertEqual(entry.posted_by_user_id, self.user.pk)
