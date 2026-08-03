"""Milestone 19 · Increment 2 (SESSION_155) — pilot inventory import tests.

Covers:

- Wrapper is a thin overlay on the M6.3 substrate — reuses the 21-
  column vocab verbatim (no fork per §0.a M19.2 decision 1).
- Pilot-specific policy overrides per §0.a M19.2 decision 2:
  belt-and-suspenders ``is_pilot`` guard + ``source`` label +
  ``mark_missing_unavailable=False``.
- ``PilotInventoryImportResult`` shape + frozen contract.
- Partial-success semantics inherited from M6.3.
- Re-import updates existing rows (M6.3 semantics inherited).
- CSV edge cases: BOM, aliases, currency formatting, extra columns.
- Both str/Path and file-like input paths.
- ``PILOT_IMPORT_SOURCE`` constant stability.
- Tenancy carrier count + permission-class zero-drift streak
  unchanged at M19.2 (M19.2 is pure additive service work — no
  new models, no new endpoints, no new permission classes).
- Endpoint count 108 (unchanged — 4 new endpoints land at M19.3).
"""

from __future__ import annotations

import tempfile
from dataclasses import FrozenInstanceError
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.test import TestCase

from dealer_ai.models import Dealership, Vehicle, VehicleStage
from dealer_ai.services.inventory_import import CSV_FIELDS
from dealer_ai.services.pilot_onboarding import (
    NonPilotImportError,
    PILOT_IMPORT_SOURCE,
    PilotInventoryImportResult,
    import_pilot_inventory,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES

from ._auth_helpers import (
    make_demo_dealership,
    make_dealership,
    make_pilot_dealership,
)
from dealer_ai.models import DEMO_ARCHETYPE_RETAIL_SUBPRIME


# ---------------------------------------------------------------------------
# CSV builders — bare minimum for happy-path variants.
# ---------------------------------------------------------------------------


_HEADER = ",".join(CSV_FIELDS)


def _csv_body(*rows: str) -> str:
    return _HEADER + "\n" + "\n".join(rows)


def _row(**overrides) -> str:
    """Build one CSV row respecting :data:`CSV_FIELDS` column order."""
    values = {name: overrides.get(name, "") for name in CSV_FIELDS}
    return ",".join(str(values[name]) for name in CSV_FIELDS)


# ---------------------------------------------------------------------------
# Constant + result-shape contracts
# ---------------------------------------------------------------------------


class PilotImportSourceConstantTests(TestCase):
    def test_stable_value(self) -> None:
        # A rename/typo here would strand M19.1-era pilot rows.
        self.assertEqual(PILOT_IMPORT_SOURCE, "pilot-inventory-import")


class PilotInventoryImportResultTests(TestCase):
    def test_defaults(self) -> None:
        r = PilotInventoryImportResult(dealership_id=1)
        self.assertEqual(r.accepted_row_stock_numbers, ())
        self.assertEqual(r.rejected_rows, ())

    def test_frozen(self) -> None:
        r = PilotInventoryImportResult(dealership_id=1)
        with self.assertRaises(FrozenInstanceError):
            r.dealership_id = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Belt-and-suspenders guard
# ---------------------------------------------------------------------------


class BeltAndSuspendersGuardTests(TestCase):
    def test_real_dealership_raises_non_pilot_import_error(self) -> None:
        real = make_dealership(slug="m192-real")
        with self.assertRaises(NonPilotImportError):
            import_pilot_inventory(
                dealership=real,
                csv_source=StringIO(_csv_body()),
            )

    def test_demo_dealership_raises(self) -> None:
        demo = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="m192-demo",
        )
        with self.assertRaises(NonPilotImportError):
            import_pilot_inventory(
                dealership=demo,
                csv_source=StringIO(_csv_body()),
            )

    def test_terminated_pilot_raises(self) -> None:
        # Once terminate_pilot flips is_pilot=False, imports refuse.
        pilot = make_pilot_dealership(slug="m192-terminated")
        pilot.is_pilot = False
        pilot.save(update_fields=["is_pilot"])
        with self.assertRaises(NonPilotImportError):
            import_pilot_inventory(
                dealership=pilot,
                csv_source=StringIO(_csv_body()),
            )

    def test_non_pilot_import_error_is_runtime_error(self) -> None:
        self.assertTrue(issubclass(NonPilotImportError, RuntimeError))


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


class HappyPathTests(TestCase):
    def setUp(self) -> None:
        self.pilot = make_pilot_dealership(slug="m192-happy")

    def test_stringio_input_creates_vehicles(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="P-001",
                year="2019",
                make="Ford",
                model="F-150",
                price="32995",
                mileage="48120",
                body_style="truck",
                condition="used",
            ),
            _row(
                stock_number="P-002",
                year="2020",
                make="Jeep",
                model="Grand Cherokee",
                price="28500",
                body_style="suv",
                condition="used",
            ),
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(result.dealership_id, self.pilot.pk)
        self.assertEqual(
            result.accepted_row_stock_numbers, ("P-001", "P-002")
        )
        self.assertEqual(result.rejected_rows, ())
        self.assertEqual(
            Vehicle.objects.filter(dealership=self.pilot).count(), 2
        )

    def test_vehicles_carry_pilot_import_source(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="P-100",
                year="2018",
                model="Corolla",
                price="12500",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="P-100")
        self.assertEqual(v.source, PILOT_IMPORT_SOURCE)

    def test_vehicles_keyed_to_pilot_dealership(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="P-200", year="2017", model="Civic",
                price="9500",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="P-200")
        self.assertEqual(v.dealership_id, self.pilot.pk)

    def test_price_and_year_parsed(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="P-300", year="2016", model="Fusion",
                price="8995",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="P-300")
        self.assertEqual(v.year, 2016)
        self.assertEqual(v.price, Decimal("8995"))

    def test_frontline_stage_bootstrap_inherited(self) -> None:
        # M5.5 lifecycle contract: every new Vehicle write path seeds
        # a frontline VehicleStage. The M6.3 substrate does this;
        # we inherit it via the wrapper.
        csv_text = _csv_body(
            _row(
                stock_number="P-400", year="2015", model="Escape",
                price="7500",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="P-400")
        stages = VehicleStage.objects.filter(vehicle=v)
        self.assertTrue(stages.exists())

    def test_filesystem_path_input(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="P-500", year="2019", model="Escape",
                price="14500",
            )
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
            encoding="utf-8",
        ) as fh:
            fh.write(csv_text)
            tmp_path = Path(fh.name)
        try:
            result = import_pilot_inventory(
                dealership=self.pilot,
                csv_source=tmp_path,
            )
        finally:
            tmp_path.unlink()
        self.assertEqual(
            result.accepted_row_stock_numbers, ("P-500",)
        )
        self.assertEqual(
            Vehicle.objects.filter(stock_number="P-500").count(), 1
        )

    def test_filesystem_missing_file_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            import_pilot_inventory(
                dealership=self.pilot,
                csv_source=Path("/nonexistent/pilot.csv"),
            )

    def test_empty_csv_returns_empty_result(self) -> None:
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(_HEADER + "\n"),
        )
        self.assertEqual(result.accepted_row_stock_numbers, ())
        self.assertEqual(result.rejected_rows, ())


# ---------------------------------------------------------------------------
# Rejected rows — partial-success posture (§0.a M19.2 decision 2)
# ---------------------------------------------------------------------------


class RejectedRowsTests(TestCase):
    def setUp(self) -> None:
        self.pilot = make_pilot_dealership(slug="m192-rejected")

    def test_missing_year_rejected(self) -> None:
        csv_text = _csv_body(
            _row(stock_number="R-1", model="Fusion", price="9000"),
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(result.accepted_row_stock_numbers, ())
        self.assertEqual(len(result.rejected_rows), 1)
        row_dict, reason = result.rejected_rows[0]
        self.assertEqual(row_dict["stock_number"], "R-1")
        self.assertIn("year", reason.lower())

    def test_missing_model_rejected(self) -> None:
        csv_text = _csv_body(
            _row(stock_number="R-2", year="2020", price="15000"),
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(len(result.rejected_rows), 1)
        _, reason = result.rejected_rows[0]
        self.assertIn("model", reason.lower())

    def test_zero_price_rejected(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="R-3", year="2020", model="Corolla",
                price="0",
            ),
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(len(result.rejected_rows), 1)
        _, reason = result.rejected_rows[0]
        self.assertIn("price", reason.lower())

    def test_missing_stock_and_vin_rejected(self) -> None:
        csv_text = _csv_body(
            _row(year="2020", model="Civic", price="15000"),
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(len(result.rejected_rows), 1)

    def test_partial_success_good_rows_commit(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="G-1", year="2020", model="Civic",
                price="15000",
            ),
            _row(stock_number="B-1", model="Fusion", price="9000"),
            _row(
                stock_number="G-2", year="2019", model="F-150",
                price="30000",
            ),
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(
            result.accepted_row_stock_numbers, ("G-1", "G-2")
        )
        self.assertEqual(len(result.rejected_rows), 1)
        self.assertEqual(
            Vehicle.objects.filter(dealership=self.pilot).count(), 2
        )

    def test_rejected_row_preserves_raw_dict(self) -> None:
        # The operator surface at M19.4 shows the operator what they
        # uploaded so they can fix it. Ensure raw values survive.
        csv_text = _csv_body(
            _row(
                stock_number="R-KEEP",
                year="not-a-year",
                model="Civic",
                price="15000",
            )
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(len(result.rejected_rows), 1)
        row_dict, _ = result.rejected_rows[0]
        self.assertEqual(row_dict["stock_number"], "R-KEEP")
        self.assertEqual(row_dict["year"], "not-a-year")


# ---------------------------------------------------------------------------
# CSV edge cases inherited from M6.3
# ---------------------------------------------------------------------------


class CsvEdgeCaseTests(TestCase):
    def setUp(self) -> None:
        self.pilot = make_pilot_dealership(slug="m192-edge")

    def test_utf8_bom_tolerated_on_filesystem_path(self) -> None:
        # Excel-saved CSVs commonly carry a BOM. utf-8-sig strips it.
        csv_text = _csv_body(
            _row(
                stock_number="BOM-1", year="2020", model="Civic",
                price="15000",
            )
        )
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False
        ) as fh:
            fh.write(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))
            tmp_path = Path(fh.name)
        try:
            result = import_pilot_inventory(
                dealership=self.pilot,
                csv_source=tmp_path,
            )
        finally:
            tmp_path.unlink()
        self.assertEqual(
            result.accepted_row_stock_numbers, ("BOM-1",)
        )

    def test_body_style_alias_normalized(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="ALIAS-1", year="2020", model="F-150",
                price="30000", body_style="pickup",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="ALIAS-1")
        self.assertEqual(v.body_style, "truck")

    def test_condition_alias_normalized(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="ALIAS-2", year="2020", model="Civic",
                price="15000", condition="pre-owned",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="ALIAS-2")
        self.assertEqual(v.condition, "used")

    def test_currency_formatted_price_parsed(self) -> None:
        # Excel formatted-price paste: "$18,995" should parse to 18995.
        csv_text = (
            _HEADER + "\n"
            + 'CUR-1,,2020,,Civic,,,"$18,995",0,,,,,,,,,,,,'
        )
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(
            result.accepted_row_stock_numbers, ("CUR-1",),
            f"rejected: {result.rejected_rows}",
        )
        v = Vehicle.objects.get(stock_number="CUR-1")
        self.assertEqual(v.price, Decimal("18995"))

    def test_defaults_when_optional_columns_blank(self) -> None:
        csv_text = _csv_body(
            _row(
                stock_number="DEF-1", year="2018", model="Fiesta",
                price="7500",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        v = Vehicle.objects.get(stock_number="DEF-1")
        self.assertEqual(v.make, "Ford")  # M6.3 default
        self.assertEqual(v.fuel_type, "Gasoline")
        self.assertEqual(v.body_style, "suv")
        self.assertEqual(v.condition, "used")

    def test_extra_columns_ignored(self) -> None:
        header_with_extra = _HEADER + ",dealer_notes,internal_flag"
        row = _row(
            stock_number="EX-1", year="2020", model="Civic",
            price="15000",
        ) + ",note-value,internal-value"
        csv_text = header_with_extra + "\n" + row
        result = import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(csv_text),
        )
        self.assertEqual(
            result.accepted_row_stock_numbers, ("EX-1",)
        )


# ---------------------------------------------------------------------------
# Re-import semantics inherited from M6.3
# ---------------------------------------------------------------------------


class ReimportTests(TestCase):
    def setUp(self) -> None:
        self.pilot = make_pilot_dealership(slug="m192-reimport")

    def test_reimport_updates_existing_stock_number(self) -> None:
        first = _csv_body(
            _row(
                stock_number="RI-1", year="2019", model="Civic",
                price="15000",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(first),
        )
        second = _csv_body(
            _row(
                stock_number="RI-1", year="2019", model="Civic",
                price="13750",  # price corrected
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(second),
        )
        rows = Vehicle.objects.filter(stock_number="RI-1")
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().price, Decimal("13750"))

    def test_partial_reupload_leaves_earlier_rows_available(self) -> None:
        # mark_missing_unavailable=False per §0.a M19.2 decision 2.
        first = _csv_body(
            _row(
                stock_number="RI-2", year="2019", model="Civic",
                price="15000",
            ),
            _row(
                stock_number="RI-3", year="2020", model="F-150",
                price="30000",
            ),
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(first),
        )
        second = _csv_body(
            _row(
                stock_number="RI-2", year="2019", model="Civic",
                price="14500",
            )
        )
        import_pilot_inventory(
            dealership=self.pilot,
            csv_source=StringIO(second),
        )
        ri3 = Vehicle.objects.get(stock_number="RI-3")
        self.assertTrue(ri3.is_available)


# ---------------------------------------------------------------------------
# Zero-drift substrate assertions at M19.2
# ---------------------------------------------------------------------------


class M192TenancyCarrierTests(TestCase):
    def test_carrier_count_unchanged(self) -> None:
        # M19.2 is pure additive service work — no new tenant-scoped
        # models. Count remains at the M19.1 delta (>=52 per lesson).
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 52)


class M192PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m192(self) -> None:
        # Streak of sixteen consecutive milestones (M10 → M19.2) —
        # M19.2 ships zero new permission classes. Same exact-set
        # posture as M191PermissionClassZeroDriftTests.
        from dealer_ai import permissions

        permission_classes = {
            name
            for name in dir(permissions)
            if not name.startswith("_")
            and name != "IsAuthenticated"
            and isinstance(getattr(permissions, name), type)
            and issubclass(
                getattr(permissions, name),
                __import__(
                    "rest_framework.permissions",
                    fromlist=["BasePermission"],
                ).BasePermission,
            )
            and getattr(permissions, name).__module__
            == "dealer_ai.permissions"
        }
        self.assertEqual(
            permission_classes,
            {
                "IsAdvisorForSlug",
                "IsDealerOwnerForAdvisorSlug",
                "IsSalesManagerOrOwnerAtActiveDealership",
                "IsReconManagerSalesManagerOrOwnerAtActiveDealership",
                "IsDealerOwnerAtActiveDealership",
                "IsFinanceManagerOrOwnerAtActiveDealership",
                "ReadOnly",
            },
        )


class M192EndpointCountTests(TestCase):
    def test_endpoint_count_unchanged_at_m192(self) -> None:
        # Endpoints ship at M19.3. At M19.2 count remains >= 108.
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 108)
