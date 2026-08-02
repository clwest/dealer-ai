"""Milestone 18 · Increment 1 (SESSION_147) — archetype dispatcher.

Per MILESTONE_18_PLANNING.md §5.d Option A + §7 M18.1. Maps the
archetype vocab string from ``models.DEMO_ARCHETYPE_CHOICES`` to
the concrete builder class. Consumed by
``services/demo_store/registry.py::create_demo_store`` +
``reset_demo_store``.

**M18.1 posture.** All three archetypes are registered as
dispatch targets. Their builders are stubs (raise
``NotImplementedError``) until M18.2 / M18.3 / M18.4 fill them
in. The M18.1 test suite asserts the dispatcher recognizes each
archetype string; the stub-implementation tests come with each
per-archetype increment.

**Fixed-vocab discipline** per M11-M17 lesson: adding a new
archetype requires (a) adding a constant + choice in
``models.py``, (b) adding a migration, (c) adding an
``ArchetypeBuilder`` subclass, (d) registering the mapping
here, (e) updating the exact-set test assertion in
``tests/test_m181_demo_store_substrate.py``. The multiple
touch-points prevent silent additions.
"""

from __future__ import annotations

from ....models import (
    DEMO_ARCHETYPE_BHPH,
    DEMO_ARCHETYPE_FLOOR_PLANNED,
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
)
from .base import ArchetypeBuilder
from .bhph import BhphArchetypeBuilder
from .floor_planned import FloorPlannedArchetypeBuilder
from .retail_subprime import RetailSubprimeArchetypeBuilder


# Archetype dispatch table. Fixed vocab per §5.b Option A.
ARCHETYPE_BUILDERS: dict[str, type[ArchetypeBuilder]] = {
    DEMO_ARCHETYPE_RETAIL_SUBPRIME: RetailSubprimeArchetypeBuilder,
    DEMO_ARCHETYPE_FLOOR_PLANNED: FloorPlannedArchetypeBuilder,
    DEMO_ARCHETYPE_BHPH: BhphArchetypeBuilder,
}


def get_archetype_builder(archetype: str) -> ArchetypeBuilder:
    """Return a fresh instance of the builder for ``archetype``.

    Raises :class:`ValueError` with a descriptive message if the
    archetype string is not in the dispatch table — signals a
    caller bug (unknown archetype); should never surface to end
    users because the archetype is validated upstream by the
    ``Dealership.demo_archetype`` CharField choices.
    """
    builder_class = ARCHETYPE_BUILDERS.get(archetype)
    if builder_class is None:
        raise ValueError(
            f"Unknown demo archetype {archetype!r}. "
            f"Known archetypes: {sorted(ARCHETYPE_BUILDERS)}."
        )
    return builder_class()


__all__ = [
    "ARCHETYPE_BUILDERS",
    "ArchetypeBuilder",
    "BhphArchetypeBuilder",
    "FloorPlannedArchetypeBuilder",
    "RetailSubprimeArchetypeBuilder",
    "get_archetype_builder",
]
