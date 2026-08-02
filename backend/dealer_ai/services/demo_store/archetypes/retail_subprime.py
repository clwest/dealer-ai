"""Milestone 18 · Increment 2 (SESSION_148) — retail/subprime archetype.

**M18.1 stub only.** The full archetype ships at M18.2 per
``MILESTONE_18_PLANNING.md`` §7. This file is a placeholder so the
M18.1 dispatcher can register the archetype string without a
`NoneType is not callable` at scenario dispatch time.

Small used-car lot; low volume; heavy sub-prime lender usage;
walk-in buyers; cash-and-carry mix. Scope defined at
``MILESTONE_18_PLANNING.md`` §7 M18.2.
"""

from __future__ import annotations

from ....models import DEMO_ARCHETYPE_RETAIL_SUBPRIME, Dealership
from ..scenario_summary import ScenarioSummary
from .base import ArchetypeBuilder


class RetailSubprimeArchetypeBuilder(ArchetypeBuilder):
    """Placeholder — full builder ships at M18.2."""

    archetype = DEMO_ARCHETYPE_RETAIL_SUBPRIME

    def build(self, dealership: Dealership) -> ScenarioSummary:
        raise NotImplementedError(
            "RetailSubprimeArchetypeBuilder ships at M18.2 "
            "(see MILESTONE_18_PLANNING.md §7 M18.2). At M18.1 "
            "the archetype is registered as a dispatch target but "
            "the coherent-story builder is not yet implemented."
        )
