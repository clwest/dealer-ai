"""Milestone 19 · Increment 2 (SESSION_155) — pilot inventory import.

Per MILESTONE_19_PLANNING.md §5.e Option A + §7 M19.2 (user-
confirmed at SESSION_155 open, recorded as §0.a M19.2 decisions):

**Decision 1 (CSV column set).** Reuse the M6.3 substrate's 21-
column vocab verbatim. No fork. :data:`services.inventory_import.
CSV_FIELDS` remains the authoritative schema; ``PILOT_INVENTORY_TEMPLATE.md``
documents the shipping columns rather than authoring a new set.

**Decision 2 (pilot policy overlay).** :func:`import_pilot_inventory`
is a **thin wrapper** around :func:`services.inventory_import.
import_rows` with three pilot-specific overrides:

1. Belt-and-suspenders ``assert dealership.is_pilot`` at the top of
   the write verb + :class:`NonPilotImportError` domain guard.
2. ``mark_missing_unavailable=False`` — pilots build inventory over
   time; a partial CSV re-upload must not sweep earlier rows.
3. Stable ``source="pilot-inventory-import"`` label so pilot rows
   are isolatable from franchise-scraper rows in operator surfaces.

Partial-success semantics inherited from M6.3: accepted rows commit
inside the caller's atomic block; rejected rows surface with error
strings so the operator can fix + re-import without losing good rows.

Re-import behavior inherited from M6.3: a re-uploaded stock number
matching an existing Vehicle **updates** the existing row (rather
than rejecting). The dealer can correct a value + re-upload.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Union

from ...models import Dealership
from ..inventory_import import import_rows
from .errors import NonPilotImportError


_LOGGER = logging.getLogger("dealer_ai.pilot_onboarding.inventory_import")

PILOT_IMPORT_SOURCE = "pilot-inventory-import"

CsvSource = Union[str, Path, IO[str]]


@dataclass(frozen=True)
class PilotInventoryImportResult:
    """Per §5.e Option A — per-row accepted / rejected + errors.

    Fields:

    - ``accepted_row_stock_numbers`` — stock numbers for Vehicle rows
      that landed (created OR updated on re-import per M6.3
      semantics).
    - ``rejected_rows`` — tuple of ``(raw_row_dict, error_message)``.
      Chris surfaces these via the M19.4 admin surface for hand-
      cleanup + re-import.
    - ``dealership_id`` — pk of the target pilot Dealership.

    Immutable output per M13.3 / M14.1 / M17.1 / M18.1 aggregator
    posture. Callers project into serialized shape at the endpoint
    layer rather than mutating.
    """

    dealership_id: int
    accepted_row_stock_numbers: tuple[str, ...] = field(
        default_factory=tuple
    )
    rejected_rows: tuple[tuple[dict, str], ...] = field(
        default_factory=tuple
    )


def _read_csv_rows(csv_source: CsvSource):
    """Yield ``(line_number, raw_row_dict)`` pairs from a path or file-like.

    - ``str`` / ``Path`` — treated as a filesystem path. Opened with
      ``utf-8-sig`` encoding so a UTF-8 BOM (common in Excel-saved
      CSVs) is transparently stripped.
    - File-like (anything with ``.read``) — passed directly to
      :class:`csv.DictReader` when the first read returns text;
      wrapped in a :class:`io.TextIOWrapper` when the first read
      returns bytes (Django ``UploadedFile`` from the M19.4 endpoint
      layer reads as bytes). Test callers typically pass an
      :class:`io.StringIO`.

    Raises :class:`FileNotFoundError` for a non-existent path so
    the wrapper surfaces the failure clearly rather than continuing
    with an empty row set.
    """
    if hasattr(csv_source, "read"):
        # Peek the first chunk to detect bytes-mode file-like objects
        # (Django UploadedFile). Reset position after the probe so
        # DictReader sees the full stream.
        probe = csv_source.read(0)  # type: ignore[attr-defined]
        if isinstance(probe, bytes):
            text_stream = io.TextIOWrapper(
                csv_source,  # type: ignore[arg-type]
                encoding="utf-8-sig",
                newline="",
            )
            reader = csv.DictReader(text_stream)
        else:
            reader = csv.DictReader(csv_source)  # type: ignore[arg-type]
        for i, row in enumerate(reader, start=2):
            yield i, row
        return
    path = Path(csv_source)  # type: ignore[arg-type]
    if not path.is_file():
        raise FileNotFoundError(
            f"Pilot inventory CSV not found: {path}"
        )
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=2):
            yield i, row


def import_pilot_inventory(
    *,
    dealership: Dealership,
    csv_source: CsvSource,
    actor=None,
) -> PilotInventoryImportResult:
    """Import a pilot dealer's used-inventory CSV.

    Belt-and-suspenders guarded per §7 M19.2 + §0 posture:

    1. :class:`NonPilotImportError` raised if
       ``dealership.is_pilot=False`` (mirrors
       :class:`NonPilotTerminationError`).
    2. ``assert dealership.is_pilot`` fires at the top of the write
       path — defensive second layer per M17/M18/M19.1 pattern.

    Delegates row parsing + persistence to
    :func:`services.inventory_import.import_rows` with three pilot-
    specific overrides:

    - ``source=PILOT_IMPORT_SOURCE``
    - ``mark_missing_unavailable=False``
    - ``dealership`` pinned to the pilot tenant

    Accepts either a filesystem path (``str``/``Path``) or a file-
    like object with ``.read``. Test callers use :class:`io.StringIO`;
    the M19.3 endpoint layer will pass an :class:`UploadedFile`.

    Returns a frozen :class:`PilotInventoryImportResult`. Partial-
    success semantics: accepted rows commit; rejected rows are
    surfaced in ``rejected_rows`` with the M6.3 substrate's per-row
    error string.
    """
    if not dealership.is_pilot:
        raise NonPilotImportError(
            f"import_pilot_inventory refuses to touch dealership "
            f"{dealership.slug!r} (is_pilot=False). Only pilot "
            "dealerships accept imports via this path; franchise "
            "and demo tenants use the M6.3 import_inventory command "
            "or archetype builders respectively."
        )
    assert dealership.is_pilot, (
        "import_pilot_inventory belt-and-suspenders assert failed — "
        f"dealership {dealership.slug!r} reached the write path "
        "with is_pilot=False. Broken invariant."
    )

    rows = list(_read_csv_rows(csv_source))
    summary = import_rows(
        rows,
        source=PILOT_IMPORT_SOURCE,
        mark_missing_unavailable=False,
        dealership=dealership,
    )

    accepted = tuple(summary.seen_stock_numbers)
    rejected: list[tuple[dict, str]] = []
    for line, raw in rows:
        for err in summary.invalid_rows:
            if err.line == line:
                rejected.append((dict(raw), err.reason))
                break

    _LOGGER.info(
        "pilot inventory imported",
        extra={
            "dealership_slug": dealership.slug,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "created": summary.created,
            "updated": summary.updated,
            "unchanged": summary.unchanged,
            "actor": str(actor) if actor is not None else None,
        },
    )

    return PilotInventoryImportResult(
        dealership_id=dealership.pk,
        accepted_row_stock_numbers=accepted,
        rejected_rows=tuple(rejected),
    )
