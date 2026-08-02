"""Milestone 18 · Increment 3 (SESSION_149) — floor-planned archetype.

**M18.1 stub only.** The full archetype ships at M18.3 per
``MILESTONE_18_PLANNING.md`` §7. Mid-size independent; auction
floor-plan lender; outside-recon vendor relationships; active
recon overrun scenario for the recon lead role.
"""

from __future__ import annotations

from ....models import DEMO_ARCHETYPE_FLOOR_PLANNED, Dealership
from ..scenario_summary import ScenarioSummary
from .base import ArchetypeBuilder


class FloorPlannedArchetypeBuilder(ArchetypeBuilder):
    """Placeholder — full builder ships at M18.3."""

    archetype = DEMO_ARCHETYPE_FLOOR_PLANNED

    def build(self, dealership: Dealership) -> ScenarioSummary:
        raise NotImplementedError(
            "FloorPlannedArchetypeBuilder ships at M18.3 "
            "(see MILESTONE_18_PLANNING.md §7 M18.3)."
        )
