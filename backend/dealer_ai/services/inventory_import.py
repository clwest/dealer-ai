"""Inventory import service.

Pure functions used by the `import_inventory` management command. Kept here
(not in the command file) so they're testable in isolation and can be reused
by future ingest paths (JSON push, scraper, webhook) without subclassing.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from ..models import Dealership, Vehicle
from .tenancy import get_default_dealership

logger = logging.getLogger(__name__)


# Columns we consume from the CSV. Anything else is ignored.
CSV_FIELDS: Tuple[str, ...] = (
    "stock_number",
    "vin",
    "year",
    "make",
    "model",
    "trim",
    "condition",
    "price",
    "mileage",
    "body_style",
    "drivetrain",
    "fuel_type",
    "exterior_color",
    "interior_color",
    "transmission",
    "engine",
    "msrp",
    "image_url",
    "url",
    "description",
    "features",
)

REQUIRED_FIELDS: Tuple[str, ...] = ("year", "model", "price")
TRUE_VALUES = {"true", "yes", "1", "y", "t"}


# Body-style aliases the CSV might use.
BODY_STYLE_ALIASES: Dict[str, str] = {
    "pickup": "truck",
    "truck": "truck",
    "suv": "suv",
    "crossover": "suv",
    "sedan": "car",
    "coupe": "car",
    "hatch": "car",
    "hatchback": "car",
    "car": "car",
    "ev": "ev",
    "electric": "ev",
    "van": "van",
    "minivan": "van",
}

CONDITION_ALIASES: Dict[str, str] = {
    "new": "new",
    "used": "used",
    "pre-owned": "used",
    "preowned": "used",
    "second-hand": "used",
    "certified": "certified",
    "cpo": "certified",
    "certified pre-owned": "certified",
}


@dataclass
class RowError:
    line: int
    stock_number: str
    reason: str


@dataclass
class ImportSummary:
    source: str
    started_at: str
    dry_run: bool = False
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    marked_unavailable: int = 0
    invalid_rows: List[RowError] = field(default_factory=list)
    seen_stock_numbers: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "started_at": self.started_at,
            "dry_run": self.dry_run,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "marked_unavailable": self.marked_unavailable,
            "invalid_rows": [
                {"line": e.line, "stock_number": e.stock_number, "reason": e.reason}
                for e in self.invalid_rows
            ],
            "seen_stock_numbers": list(self.seen_stock_numbers),
        }


# ---- Row parsing ------------------------------------------------------------


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_int(value: Any) -> Optional[int]:
    text = _clean(value)
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _parse_decimal(value: Any) -> Optional[Decimal]:
    text = _clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_features(value: Any) -> List[str]:
    text = _clean(value)
    if not text:
        return []
    if text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
    # Pipe / semicolon / comma separated.
    for sep in ("|", ";", ","):
        if sep in text:
            return [p.strip() for p in text.split(sep) if p.strip()]
    return [text]


def _normalize_body_style(value: Any) -> str:
    text = _clean(value).lower()
    if not text:
        return ""
    return BODY_STYLE_ALIASES.get(text, text)


def _normalize_condition(value: Any) -> str:
    text = _clean(value).lower()
    if not text:
        return "used"
    return CONDITION_ALIASES.get(text, text)


def parse_row(raw: Dict[str, Any], *, line: int) -> Tuple[Optional[Dict[str, Any]], Optional[RowError]]:
    """Convert a raw CSV dict to a normalized vehicle dict, or (None, RowError)."""
    cleaned: Dict[str, Any] = {}
    stock = _clean(raw.get("stock_number"))
    vin = _clean(raw.get("vin"))

    if not stock and not vin:
        return None, RowError(line, "", "missing both stock_number and VIN")

    cleaned["stock_number"] = stock
    cleaned["vin"] = vin

    year = _parse_int(raw.get("year"))
    if year is None or year < 1980 or year > 2100:
        return None, RowError(line, stock or vin, f"invalid year: {raw.get('year')!r}")
    cleaned["year"] = year

    model_value = _clean(raw.get("model"))
    if not model_value:
        return None, RowError(line, stock or vin, "missing model")
    cleaned["model"] = model_value

    price = _parse_decimal(raw.get("price"))
    if price is None or price <= 0:
        return None, RowError(line, stock or vin, f"invalid price: {raw.get('price')!r}")
    cleaned["price"] = price

    msrp = _parse_decimal(raw.get("msrp"))
    if msrp is not None and msrp > 0:
        cleaned["msrp"] = msrp

    mileage = _parse_int(raw.get("mileage")) or 0
    cleaned["mileage"] = max(0, mileage)

    cleaned["make"] = _clean(raw.get("make")) or "Ford"
    cleaned["trim"] = _clean(raw.get("trim"))
    cleaned["body_style"] = _normalize_body_style(raw.get("body_style")) or "suv"
    cleaned["condition"] = _normalize_condition(raw.get("condition"))
    cleaned["drivetrain"] = _clean(raw.get("drivetrain"))
    cleaned["transmission"] = _clean(raw.get("transmission"))
    cleaned["fuel_type"] = _clean(raw.get("fuel_type")) or "Gasoline"
    cleaned["engine"] = _clean(raw.get("engine"))
    cleaned["exterior_color"] = _clean(raw.get("exterior_color"))
    cleaned["interior_color"] = _clean(raw.get("interior_color"))
    cleaned["description"] = _clean(raw.get("description"))
    cleaned["image_url"] = _clean(raw.get("image_url"))
    cleaned["url"] = _clean(raw.get("url"))
    cleaned["features"] = _parse_features(raw.get("features"))

    if not stock:
        # If we only have VIN, synthesize a deterministic placeholder so the
        # uniqueness constraint holds.
        cleaned["stock_number"] = f"VIN-{vin}"

    return cleaned, None


def read_csv_rows(file_path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    """Yield (line_number, raw_row_dict) pairs."""
    with open(file_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return
        for i, row in enumerate(reader, start=2):  # header is line 1
            yield i, row


# ---- Persistence ------------------------------------------------------------


def _find_existing(stock_number: str, vin: str) -> Optional[Vehicle]:
    if stock_number:
        v = Vehicle.objects.filter(stock_number=stock_number).first()
        if v:
            return v
    if vin:
        v = Vehicle.objects.filter(vin=vin).exclude(vin="").first()
        if v:
            return v
    return None


def _apply_row_to_vehicle(
    vehicle: Vehicle, fields: Dict[str, Any], *, source: str, now
) -> bool:
    """Set attributes on `vehicle` and return True if anything changed."""
    changed = False
    for key, value in fields.items():
        current = getattr(vehicle, key, None)
        if current != value:
            setattr(vehicle, key, value)
            changed = True

    if vehicle.source != source:
        vehicle.source = source
        changed = True
    if not vehicle.is_available:
        vehicle.is_available = True
        changed = True
    vehicle.last_seen_at = now
    if vehicle.imported_at is None:
        vehicle.imported_at = now
    return changed


def import_rows(
    rows: Iterable[Tuple[int, Dict[str, Any]]],
    *,
    source: str,
    dry_run: bool = False,
    mark_missing_unavailable: bool = True,
    dealership: Optional[Dealership] = None,
) -> ImportSummary:
    """Persist (or simulate) the import. Always runs inside a transaction; if
    `dry_run` is True the transaction is rolled back at the end.

    ``dealership`` scopes the created rows to a specific tenant. When
    omitted, the default tenancy resolver picks the single-tenant
    Dealership row — the same behavior every existing caller sees. The
    pre_save signal would also cover the unset case, but plumbing it
    through here keeps intent visible for future request-context
    callers and lets ``mark_missing_unavailable`` scope its stale-row
    query to the correct tenant.
    """
    tenant = dealership if dealership is not None else get_default_dealership()
    started_at = timezone.now()
    summary = ImportSummary(
        source=source,
        started_at=started_at.isoformat(),
        dry_run=dry_run,
    )

    seen_stock_numbers: List[str] = []
    with transaction.atomic():
        for line, raw in rows:
            cleaned, err = parse_row(raw, line=line)
            if err is not None:
                summary.invalid_rows.append(err)
                continue
            assert cleaned is not None  # for type-checkers

            existing = _find_existing(cleaned["stock_number"], cleaned["vin"])
            if existing is None:
                vehicle = Vehicle(**cleaned)
                vehicle.dealership = tenant
                vehicle.source = source
                vehicle.last_seen_at = started_at
                vehicle.imported_at = started_at
                vehicle.is_available = True
                vehicle.save()
                summary.created += 1
            else:
                changed = _apply_row_to_vehicle(
                    existing, cleaned, source=source, now=started_at
                )
                existing.save()
                if changed:
                    summary.updated += 1
                else:
                    summary.unchanged += 1
            seen_stock_numbers.append(cleaned["stock_number"])

        summary.seen_stock_numbers = seen_stock_numbers

        if mark_missing_unavailable and seen_stock_numbers:
            # Scope the stale-row sweep to the tenant we're importing
            # into so a multi-tenant future never marks another
            # dealer's inventory unavailable based on this import.
            stale = (
                Vehicle.objects.filter(
                    dealership=tenant,
                    source=source,
                    is_available=True,
                )
                .exclude(stock_number__in=seen_stock_numbers)
            )
            summary.marked_unavailable = stale.count()
            stale.update(is_available=False, updated_at=timezone.now())

        if dry_run:
            transaction.set_rollback(True)

    return summary


def import_csv(
    file_path: Path | str,
    *,
    source: Optional[str] = None,
    dry_run: bool = False,
    mark_missing_unavailable: bool = True,
    dealership: Optional[Dealership] = None,
) -> ImportSummary:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Inventory file not found: {path}")
    derived_source = source or f"csv:{path.stem}"
    return import_rows(
        list(read_csv_rows(path)),
        source=derived_source,
        dry_run=dry_run,
        mark_missing_unavailable=mark_missing_unavailable,
        dealership=dealership,
    )
