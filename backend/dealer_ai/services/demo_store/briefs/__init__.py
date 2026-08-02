"""Milestone 18 · Increment 5 (SESSION_151) — daily brief loader.

Per MILESTONE_18_PLANNING.md §7 M18.5. Each archetype ships a
directory of markdown daily briefs (one per operator role). This
module is the loader — a pure verb pair that lists available
briefs per archetype + reads brief content on demand.

**Structure.** Briefs live at
``services/demo_store/briefs/<archetype>/<role>.md``. Each brief
follows the standard structure per the M18 milestone brief:

- What happened before login.
- What the operator needs to accomplish today.
- What information is intentionally incomplete.
- Which shipped capabilities should help.
- What successful completion looks like.
- What must remain discoverable without a guided click path.

**Fixed vocab.** ``BRIEF_ROLES`` names the union of roles across
all archetypes. Individual archetypes may ship fewer files (e.g.
retail_subprime has no collector brief because it has no active
BHPH book).

**No LLM.** Briefs are hand-written markdown — no generation, no
external calls. The scanner test in
``tests/test_m181_demo_store_substrate.py`` enforces that
``services/demo_store/`` does not egress; briefs are consumed by
reading the file bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_BRIEFS_DIR = Path(__file__).resolve().parent


# Fixed vocab of roles a brief may exist for. Growth-only per the
# M9-M17 growth-only-list lesson. Exact-set assertion at test time.
BRIEF_ROLE_OWNER = "owner"
BRIEF_ROLE_SALES_MANAGER = "sales_manager"
BRIEF_ROLE_RECON = "recon"
BRIEF_ROLE_ACCOUNTING = "accounting"
BRIEF_ROLE_COLLECTOR = "collector"

BRIEF_ROLES: tuple[str, ...] = (
    BRIEF_ROLE_OWNER,
    BRIEF_ROLE_SALES_MANAGER,
    BRIEF_ROLE_RECON,
    BRIEF_ROLE_ACCOUNTING,
    BRIEF_ROLE_COLLECTOR,
)


class BriefNotFoundError(ValueError):
    """Raised when ``(archetype, role)`` has no brief file.

    Mapped to HTTP 404 at any endpoint layer that surfaces briefs
    (M18 does not currently ship an endpoint; the CLI + tests
    consume briefs directly).
    """


@dataclass(frozen=True)
class Brief:
    """A loaded daily brief.

    Fields:

    - ``archetype`` — one of ``DEMO_ARCHETYPE_*`` vocab members.
    - ``role`` — one of :data:`BRIEF_ROLES`.
    - ``content`` — the markdown source text (untransformed;
      renderers apply GFM at consumption time).
    """

    archetype: str
    role: str
    content: str


def list_briefs(archetype: str) -> tuple[str, ...]:
    """Return the tuple of role slugs that have briefs for ``archetype``.

    Deterministic ordering matches :data:`BRIEF_ROLES` (owner
    first, collector last). Roles without a corresponding markdown
    file are omitted — a real operator viewing the archetype only
    sees the briefs that apply to it.

    Raises :class:`BriefNotFoundError` if ``archetype`` has no
    directory (unknown archetype name).
    """
    archetype_dir = _BRIEFS_DIR / archetype
    if not archetype_dir.is_dir():
        raise BriefNotFoundError(
            f"No brief directory for archetype {archetype!r}. "
            f"Expected {archetype_dir}."
        )
    present = []
    for role in BRIEF_ROLES:
        if (archetype_dir / f"{role}.md").is_file():
            present.append(role)
    return tuple(present)


def get_brief(archetype: str, role: str) -> Brief:
    """Load the brief for ``(archetype, role)``.

    Raises :class:`BriefNotFoundError` when the file doesn't exist
    (unknown archetype, unknown role, or a role that this
    archetype doesn't ship — e.g. retail_subprime has no
    collector brief).
    """
    if role not in BRIEF_ROLES:
        raise BriefNotFoundError(
            f"Unknown role {role!r}. Valid roles: {BRIEF_ROLES!r}."
        )
    path = _BRIEFS_DIR / archetype / f"{role}.md"
    if not path.is_file():
        raise BriefNotFoundError(
            f"No brief for archetype {archetype!r} role {role!r}. "
            f"Expected {path}."
        )
    content = path.read_text(encoding="utf-8")
    return Brief(archetype=archetype, role=role, content=content)


__all__ = [
    "BRIEF_ROLES",
    "BRIEF_ROLE_ACCOUNTING",
    "BRIEF_ROLE_COLLECTOR",
    "BRIEF_ROLE_OWNER",
    "BRIEF_ROLE_RECON",
    "BRIEF_ROLE_SALES_MANAGER",
    "Brief",
    "BriefNotFoundError",
    "get_brief",
    "list_briefs",
]
