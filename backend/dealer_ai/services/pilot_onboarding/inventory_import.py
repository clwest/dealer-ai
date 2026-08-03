"""Milestone 19 · Increment 1 (SESSION_154) — pilot inventory import (stub).

Per MILESTONE_19_PLANNING.md §5.e Option A. **M19.1 stub only** —
the full implementation ships at M19.2 per §7 M19.2. This module
declares the :class:`PilotInventoryImportResult` frozen dataclass
contract so tests + downstream callers can wire against it now.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PilotInventoryImportResult:
    """Per §5.e Option A — per-row accepted / rejected + errors.

    Fields:

    - ``accepted_row_stock_numbers`` — stock numbers for Vehicle rows
      that landed. The scenario builder doesn't require the full
      Vehicle instances back; consumers project into serialized shape
      via the M6.3 substrate's admin views.
    - ``rejected_rows`` — tuple of (raw_row_dict, error_message). Chris
      surfaces these via the M19.4 admin surface for hand-cleanup +
      re-import.
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


def import_pilot_inventory(*, dealership, csv_source) -> PilotInventoryImportResult:
    """M19.1 stub — full implementation ships at M19.2.

    Raises :class:`NotImplementedError`. Callers pinning the M19.1
    substrate can construct :class:`PilotInventoryImportResult`
    directly for tests until M19.2 lands the real body.
    """
    raise NotImplementedError(
        "import_pilot_inventory ships at M19.2 (see "
        "MILESTONE_19_PLANNING.md §7 M19.2). At M19.1 the substrate "
        "declares the PilotInventoryImportResult return contract so "
        "tests + downstream callers can wire against it."
    )
