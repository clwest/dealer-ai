"""Tests for the inventory import pipeline (service + management command)."""

from __future__ import annotations

from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from dealer_ai.models import Vehicle
from dealer_ai.services.inventory_import import (
    import_csv,
    parse_row,
)


CSV_HEADER = (
    "stock_number,vin,year,make,model,trim,condition,price,mileage,body_style,"
    "drivetrain,fuel_type,exterior_color,interior_color,transmission,engine,"
    "msrp,image_url,url,description,features"
)


def _write_csv(tmp_path: Path, rows: list[str], name: str = "inventory.csv") -> Path:
    path = tmp_path / name
    path.write_text(CSV_HEADER + "\n" + "\n".join(rows), encoding="utf-8")
    return path


# ---- parse_row -------------------------------------------------------------


class ParseRowTests(TestCase):
    def test_minimal_valid_row(self):
        cleaned, err = parse_row(
            {"stock_number": "S-1", "year": "2024", "model": "F-150", "price": "55000"},
            line=2,
        )
        self.assertIsNone(err)
        self.assertIsNotNone(cleaned)
        assert cleaned is not None
        self.assertEqual(cleaned["stock_number"], "S-1")
        self.assertEqual(cleaned["year"], 2024)
        self.assertEqual(cleaned["model"], "F-150")
        self.assertEqual(cleaned["price"], Decimal("55000"))
        self.assertEqual(cleaned["make"], "Ford")  # default
        self.assertEqual(cleaned["fuel_type"], "Gasoline")  # default
        self.assertEqual(cleaned["body_style"], "suv")  # default

    def test_features_pipe_separated(self):
        cleaned, _ = parse_row(
            {
                "stock_number": "S-1",
                "year": "2024",
                "model": "F-150",
                "price": "55000",
                "features": "Tow Package|Sync 4|Heated Seats",
            },
            line=2,
        )
        assert cleaned is not None
        self.assertEqual(
            cleaned["features"], ["Tow Package", "Sync 4", "Heated Seats"]
        )

    def test_features_json_array(self):
        cleaned, _ = parse_row(
            {
                "stock_number": "S-1",
                "year": "2024",
                "model": "F-150",
                "price": "55000",
                "features": '["Leather", "BlueCruise"]',
            },
            line=2,
        )
        assert cleaned is not None
        self.assertEqual(cleaned["features"], ["Leather", "BlueCruise"])

    def test_price_with_currency_and_commas(self):
        cleaned, _ = parse_row(
            {
                "stock_number": "S-1",
                "year": "2024",
                "model": "F-150",
                "price": "$55,995.00",
            },
            line=2,
        )
        assert cleaned is not None
        self.assertEqual(cleaned["price"], Decimal("55995.00"))

    def test_body_style_alias(self):
        cleaned, _ = parse_row(
            {
                "stock_number": "S-1",
                "year": "2024",
                "model": "F-150",
                "price": "55000",
                "body_style": "Pickup",
            },
            line=2,
        )
        assert cleaned is not None
        self.assertEqual(cleaned["body_style"], "truck")

    def test_condition_alias(self):
        cleaned, _ = parse_row(
            {
                "stock_number": "S-1",
                "year": "2024",
                "model": "F-150",
                "price": "55000",
                "condition": "Pre-Owned",
            },
            line=2,
        )
        assert cleaned is not None
        self.assertEqual(cleaned["condition"], "used")

    def test_missing_required_year(self):
        _, err = parse_row(
            {"stock_number": "S-1", "model": "F-150", "price": "1"}, line=2
        )
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("year", err.reason)

    def test_missing_model_rejected(self):
        _, err = parse_row(
            {"stock_number": "S-1", "year": "2024", "price": "1"}, line=2
        )
        assert err is not None
        self.assertIn("model", err.reason)

    def test_missing_stock_and_vin_rejected(self):
        _, err = parse_row(
            {"year": "2024", "model": "F-150", "price": "1"}, line=2
        )
        assert err is not None
        self.assertIn("stock_number", err.reason)

    def test_vin_only_synthesizes_stock_number(self):
        cleaned, err = parse_row(
            {"vin": "1FT12345", "year": "2024", "model": "F-150", "price": "55000"},
            line=2,
        )
        self.assertIsNone(err)
        assert cleaned is not None
        self.assertEqual(cleaned["stock_number"], "VIN-1FT12345")

    def test_invalid_price_rejected(self):
        _, err = parse_row(
            {
                "stock_number": "S-1",
                "year": "2024",
                "model": "F-150",
                "price": "abc",
            },
            line=2,
        )
        assert err is not None
        self.assertIn("price", err.reason)


# ---- import_csv (full pipeline) --------------------------------------------


class ImportCsvTests(TestCase):
    def test_new_import_creates_vehicles(self):
        path = _write_csv(
            Path(self._dir()),
            [
                "FF-CSV-1,VIN001,2024,Ford,F-150,XLT,new,55000,12,truck,4x4,Gasoline,White,Black,Auto,2.7L V6,56000,,,Demo,Tow|Sync 4",
                "FF-CSV-2,VIN002,2023,Ford,Maverick,XLT,used,28000,42000,truck,FWD,Gasoline,Blue,Black,Auto,2.5L Hybrid,,,,,",
            ],
        )
        summary = import_csv(path)
        self.assertEqual(summary.created, 2)
        self.assertEqual(summary.updated, 0)
        self.assertEqual(summary.invalid_rows, [])
        self.assertEqual(Vehicle.objects.filter(is_available=True).count(), 2)

        v = Vehicle.objects.get(stock_number="FF-CSV-1")
        self.assertEqual(v.source, f"csv:{path.stem}")
        self.assertIsNotNone(v.imported_at)
        self.assertIsNotNone(v.last_seen_at)
        self.assertEqual(v.features, ["Tow", "Sync 4"])

    def test_update_existing_by_stock_number(self):
        Vehicle.objects.create(
            stock_number="FF-CSV-1",
            year=2024,
            model="F-150",
            price=Decimal("50000"),
            source="csv:inventory",
            is_available=True,
        )
        path = _write_csv(
            Path(self._dir()),
            ["FF-CSV-1,,2024,Ford,F-150,XLT,new,55000,15,truck,,,,,,,,,,,Tow"],
        )
        summary = import_csv(path, source="csv:inventory")
        self.assertEqual(summary.created, 0)
        self.assertEqual(summary.updated, 1)
        v = Vehicle.objects.get(stock_number="FF-CSV-1")
        self.assertEqual(v.price, Decimal("55000"))
        self.assertEqual(v.trim, "XLT")

    def test_update_by_vin_when_stock_changes(self):
        Vehicle.objects.create(
            stock_number="OLDSTOCK",
            vin="VIN001",
            year=2024,
            model="F-150",
            price=Decimal("50000"),
            source="csv:inventory",
        )
        path = _write_csv(
            Path(self._dir()),
            ["NEWSTOCK,VIN001,2024,Ford,F-150,XLT,new,55000,15,truck,,,,,,,,,,,"],
        )
        summary = import_csv(path, source="csv:inventory")
        self.assertEqual(summary.updated, 1)
        self.assertEqual(Vehicle.objects.count(), 1)
        v = Vehicle.objects.get(vin="VIN001")
        self.assertEqual(v.stock_number, "NEWSTOCK")

    def test_marks_missing_as_unavailable_but_does_not_delete(self):
        # Pre-existing vehicle from the same source.
        Vehicle.objects.create(
            stock_number="OLDIE",
            year=2023,
            model="Edge",
            price=Decimal("30000"),
            source="csv:dealer",
            is_available=True,
        )
        # New CSV doesn't include OLDIE.
        path = _write_csv(
            Path(self._dir()),
            ["NEWBIE,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"],
        )
        summary = import_csv(path, source="csv:dealer")
        self.assertEqual(summary.marked_unavailable, 1)
        oldie = Vehicle.objects.get(stock_number="OLDIE")
        self.assertFalse(oldie.is_available)
        # Still in the database.
        self.assertEqual(Vehicle.objects.count(), 2)

    def test_does_not_mark_other_sources_unavailable(self):
        Vehicle.objects.create(
            stock_number="DEMO-1",
            year=2025,
            model="F-150",
            price=Decimal("60000"),
            source="demo_seed",
            is_available=True,
        )
        path = _write_csv(
            Path(self._dir()),
            ["NEWBIE,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"],
        )
        import_csv(path, source="csv:dealer")
        demo = Vehicle.objects.get(stock_number="DEMO-1")
        self.assertTrue(demo.is_available)

    def test_dry_run_persists_nothing(self):
        path = _write_csv(
            Path(self._dir()),
            ["DRY-1,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"],
        )
        summary = import_csv(path, dry_run=True)
        self.assertTrue(summary.dry_run)
        self.assertEqual(summary.created, 1)  # would have been created
        self.assertEqual(Vehicle.objects.count(), 0)

    def test_invalid_rows_collected_and_others_imported(self):
        path = _write_csv(
            Path(self._dir()),
            [
                "GOOD-1,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,",
                "BAD-1,,abc,Ford,Edge,SE,used,30000,80000,suv,,,,,,,,,,,",  # year invalid
                "BAD-2,,2024,Ford,,,,,,,,,,,,,,,,,",  # missing model + price
            ],
        )
        summary = import_csv(path)
        self.assertEqual(summary.created, 1)
        self.assertEqual(len(summary.invalid_rows), 2)
        reasons = {e.reason for e in summary.invalid_rows}
        self.assertTrue(any("year" in r for r in reasons))
        self.assertTrue(any("model" in r or "price" in r for r in reasons))

    def test_optional_fields_can_be_blank(self):
        path = _write_csv(
            Path(self._dir()),
            ["MIN-1,,2025,Ford,F-150,,,,,,,,,,,,,,,,"],
        )
        # year, make, model, price are required — this row has no price.
        summary = import_csv(path)
        self.assertEqual(summary.created, 0)
        self.assertEqual(len(summary.invalid_rows), 1)

        path2 = _write_csv(
            Path(self._dir()),
            ["MIN-2,,2025,Ford,F-150,,,55000,,,,,,,,,,,,,"],
            name="inventory2.csv",
        )
        summary = import_csv(path2)
        self.assertEqual(summary.created, 1)

    def test_idempotent_second_run_marks_no_changes(self):
        path = _write_csv(
            Path(self._dir()),
            ["ID-1,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"],
        )
        first = import_csv(path)
        self.assertEqual(first.created, 1)
        second = import_csv(path)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.updated, 0)
        self.assertEqual(second.unchanged, 1)
        self.assertEqual(second.marked_unavailable, 0)

    def test_re_import_after_unavailable_brings_back(self):
        path = _write_csv(
            Path(self._dir()),
            ["RE-1,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"],
        )
        import_csv(path)
        # Manually flip to unavailable to simulate a stale state.
        Vehicle.objects.filter(stock_number="RE-1").update(is_available=False)
        # Re-import: should bring it back available.
        summary = import_csv(path)
        v = Vehicle.objects.get(stock_number="RE-1")
        self.assertTrue(v.is_available)
        self.assertEqual(summary.updated, 1)

    def _dir(self) -> str:
        # Per-test temp dir provided by Django's TestCase isn't built-in; use
        # tempfile.
        import tempfile

        if not hasattr(self, "_tmp"):
            self._tmp = tempfile.mkdtemp(prefix="ff-import-")
        return self._tmp


# ---- Management command wrapper --------------------------------------------


class ImportCommandTests(TestCase):
    def test_command_runs_and_persists(self):
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="ff-cmd-"))
        path = _write_csv(
            tmp, ["CMD-1,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"]
        )
        out = StringIO()
        call_command("import_inventory", "--file", str(path), stdout=out)
        self.assertEqual(Vehicle.objects.filter(stock_number="CMD-1").count(), 1)
        output = out.getvalue()
        self.assertIn("Created:            1", output)

    def test_command_dry_run_does_not_persist(self):
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="ff-cmd-"))
        path = _write_csv(
            tmp, ["CMD-DRY,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"]
        )
        out = StringIO()
        call_command(
            "import_inventory", "--file", str(path), "--dry-run", stdout=out
        )
        self.assertEqual(Vehicle.objects.count(), 0)
        self.assertIn("[DRY-RUN]", out.getvalue())

    def test_command_json_output(self):
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="ff-cmd-"))
        path = _write_csv(
            tmp, ["CMD-J,,2025,Ford,F-150,XLT,new,55000,12,truck,,,,,,,,,,,"]
        )
        out = StringIO()
        call_command(
            "import_inventory", "--file", str(path), "--json", stdout=out
        )
        import json as _json

        data = _json.loads(out.getvalue())
        self.assertEqual(data["created"], 1)
        self.assertIn("source", data)
