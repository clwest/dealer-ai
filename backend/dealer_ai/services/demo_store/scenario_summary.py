"""Milestone 18 · Increment 1 (SESSION_147) — scenario-summary dataclass.

Per MILESTONE_18_PLANNING.md §5.d Option A (user-confirmed at
SESSION_146 open). The return type of every archetype builder's
``build(dealership)`` verb — an explicit record of what the
scenario seeded, consumed by:

- The M18.5 daily briefs (which reference specific stock numbers
  + usernames + scenario slugs).
- The M18.6 retrospective for cross-archetype cataloging.
- Tests asserting scenario shape.

Immutable output (frozen dataclass) per M13.3 / M14.1 / M17.1
posture. Callers project into serialized shape rather than
mutating.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScenarioSummary:
    """Immutable record of what an archetype builder seeded.

    Fields:

    - ``archetype`` — one of ``DEMO_ARCHETYPE_*`` vocab members.
    - ``dealership_id`` — pk of the target Dealership.
    - ``dealership_slug`` — human-readable identifier.
    - ``seeded_stock_numbers`` — tuple of vehicle stock numbers
      the scenario created. Referenced by daily briefs.
    - ``seeded_user_usernames`` — tuple of Django User usernames
      the scenario created (owner / sales manager / advisors /
      collectors as applicable to the archetype).
    - ``seeded_scenario_slugs`` — tuple of per-brief scenario
      slug identifiers (e.g. ``recon_overrun`` for a floor-
      planned brief). Consumed by ``TesterFeedback.scenario_slug``
      when a tester submits observations.
    - ``notes`` — free-form archetype-specific notes for the
      retrospective / debugging (e.g. total row counts by
      table, timing observations). Not consumed by briefs.
    """

    archetype: str
    dealership_id: int
    dealership_slug: str
    seeded_stock_numbers: tuple[str, ...] = field(default_factory=tuple)
    seeded_user_usernames: tuple[str, ...] = field(default_factory=tuple)
    seeded_scenario_slugs: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
