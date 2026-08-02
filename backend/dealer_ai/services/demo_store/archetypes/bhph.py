"""Milestone 18 · Increment 4 (SESSION_150) — BHPH archetype.

**M18.1 stub only.** The full archetype ships at M18.4 per
``MILESTONE_18_PLANNING.md`` §7. Small BHPH dealership; active
portfolio of ~30 notes; weekly and biweekly payment frequencies;
recent NSF + promise-to-pay activity; collector role central to
daily workflow.
"""

from __future__ import annotations

from ....models import DEMO_ARCHETYPE_BHPH, Dealership
from ..scenario_summary import ScenarioSummary
from .base import ArchetypeBuilder


class BhphArchetypeBuilder(ArchetypeBuilder):
    """Placeholder — full builder ships at M18.4."""

    archetype = DEMO_ARCHETYPE_BHPH

    def build(self, dealership: Dealership) -> ScenarioSummary:
        raise NotImplementedError(
            "BhphArchetypeBuilder ships at M18.4 "
            "(see MILESTONE_18_PLANNING.md §7 M18.4)."
        )
