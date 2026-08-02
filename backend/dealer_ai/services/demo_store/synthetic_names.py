"""Milestone 18 · Increment 1 (SESSION_147) — synthetic pseudonym roster.

Per MILESTONE_18_PLANNING.md §5.g Option A (user-confirmed at
SESSION_146 open). Fixed roster of clearly-synthetic pseudonyms
for demo-store scenario builders (customer names, tester names,
salesperson names, etc.).

**Never use Faker.** Faker occasionally emits near-real values
that could accidentally trigger real-world side effects (real
ZIP+phone combos; valid-format SSNs). The fixed roster is
unmistakably synthetic and lets tests assert exact-set equality
per the M11-M17 fixed-vocab lesson.

**Naming convention.** First names are common but surnames are
obviously invented (Testworth / Demoson / Fictionton / etc.) so a
tester can never mistake a demo name for a real customer.

**Growth-only** per the M9-M17 growth-only-list lesson — future
milestones can append. Existing entries are stable (removing one
would break archetype-index-based lookups).
"""

from __future__ import annotations


# Fixed roster of ~40 synthetic pseudonyms. Add new names to the end
# of the list — indexed lookups by archetype builders rely on the
# ordering being stable.
SYNTHETIC_NAMES: tuple[str, ...] = (
    "Alexis Testworth",
    "Jamie Demoson",
    "Morgan Fictionton",
    "Riley Sampletree",
    "Casey Placeholderman",
    "Jordan Fauxwell",
    "Avery Mockington",
    "Quinn Stagerly",
    "Sage Trialstone",
    "Reese Testerman",
    "Blake Simulton",
    "Cameron Practiceworth",
    "Drew Rehearsalson",
    "Emerson Scenariofield",
    "Finley Storybrook",
    "Harper Draftly",
    "Indigo Sketchford",
    "Kai Blueprintworth",
    "Logan Prototypeton",
    "Maddox Diagrammer",
    "Nolan Fixturely",
    "Oakley Sandboxson",
    "Parker Rehearsalworth",
    "Quincy Stubfield",
    "Rowan Blankspace",
    "Sawyer Placeholderfield",
    "Tatum Testflight",
    "Umbria Rehearsalton",
    "Vale Dryrunson",
    "Wren Trialbrook",
    "Xander Fixtureworth",
    "Yael Mockville",
    "Zephyr Simulcrest",
    "Bailey Sampledale",
    "Cody Testgrove",
    "Daryl Fauxridge",
    "Elliott Draftshire",
    "Frankie Stubwood",
    "Gray Practicetown",
    "Hollis Rehearseborough",
)


# Sanity check at import time — if two names collide, an archetype
# builder's assumption of unique names is broken.
assert len(SYNTHETIC_NAMES) == len(set(SYNTHETIC_NAMES)), (
    "SYNTHETIC_NAMES roster contains duplicates — every entry must "
    "be unique so archetype builders can rely on unique lookups."
)


def get_synthetic_name(index: int) -> str:
    """Return the pseudonym at ``index`` (wrapping via modulo).

    Archetype builders pass a stable index (e.g. row number within
    the scenario) so re-running ``build()`` yields the same names.
    Wrapping means a large archetype never runs out of names.
    """
    return SYNTHETIC_NAMES[index % len(SYNTHETIC_NAMES)]
