"""Milestone 18 · Increment 1 (SESSION_147) — archetype builder ABC.

Per MILESTONE_18_PLANNING.md §5.d Option A (user-confirmed at
SESSION_146 open). Every archetype module exposes a
:class:`ArchetypeBuilder` subclass with a ``build(dealership)``
verb that constructs a coherent operational story across the
shipped M1-M17 surface.

**Coherence contract** per §1 Q6 + §Store-story coherence:
seeded records must tell connected operational stories. A
vehicle with a recon overrun must reconcile across its
acquisition record, investment ledger, condition findings, work
orders, lifecycle stage, projected gross, and accounting
activity. Random Faker-style row population is prohibited.

**Atomicity contract** per §5.c Option A + §0 engineering
practices: every ``build()`` invocation wraps in
``@transaction.atomic``. Partial demo stores are architecturally
impossible.

**Reset contract** per §5.c Option A: ``reset_demo_store`` in
``registry.py`` deletes the demo dealership's transitive row set
(CASCADE via ``Dealership.CASCADE`` on tenancy carriers) and
re-invokes ``build()`` to restore the canonical starting state.
Builders must be deterministic — same inputs, same outputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ....models import Dealership
from ..scenario_summary import ScenarioSummary


class ArchetypeBuilder(ABC):
    """Base class for demo-store archetype builders.

    Subclasses live in ``services/demo_store/archetypes/`` and
    are registered via the dispatcher in ``__init__.py``.
    """

    #: The archetype vocab string this builder handles. Must
    #: match a value in :data:`models.DEMO_ARCHETYPE_CHOICES`.
    archetype: str = ""

    @abstractmethod
    def build(self, dealership: Dealership) -> ScenarioSummary:
        """Construct the archetype's scenario story atomically.

        Called from :func:`services.demo_store.registry.create_demo_store`
        + :func:`services.demo_store.registry.reset_demo_store`
        inside an existing ``@transaction.atomic`` block; nested
        atomic is a no-op but keeps this verb self-contained for
        direct-call test paths.

        Returns a :class:`ScenarioSummary` naming the rows the
        builder created, consumed by daily briefs + tests.

        Callers guarantee ``dealership.is_demo=True`` before
        invoking; the belt-and-suspenders guard in
        ``registry.py`` enforces this.
        """
