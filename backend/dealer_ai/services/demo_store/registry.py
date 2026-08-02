"""Milestone 18 · Increment 1 (SESSION_147) — demo-store registry verbs.

Three verbs per MILESTONE_18_PLANNING.md §7 M18.1 + §5.c Option A
(user-confirmed at SESSION_146 open, recorded in §0.a):

- :func:`create_demo_store` — atomic create + archetype build.
- :func:`reset_demo_store` — atomic delete-then-rebuild.
- :func:`list_demo_stores` — pure read (``is_demo=True`` rows).

**Belt-and-suspenders guard** per §5.c Option A: the write paths
raise :class:`NonDemoResetError` when called with a Dealership
where ``is_demo=False`` AND ``assert dealership.is_demo`` fires
at the top of every write verb. The layered check prevents a
future refactor that accidentally weakens one guard from
compromising the invariant — a demo-store write path against a
non-demo dealership is architecturally impossible.

**Reset semantics.** ``reset_demo_store`` deletes the transitive
row set via ``Dealership`` CASCADE FKs on every tenancy carrier,
then re-invokes the archetype builder to restore canonical state.
The demo Dealership row itself is preserved (its pk stays
stable) — only the child rows churn. This preserves the tester's
login credentials + any bookmarks referencing the dealership pk.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction

from ...models import Dealership
from .archetypes import get_archetype_builder
from .errors import NonDemoResetError
from .scenario_summary import ScenarioSummary


_LOGGER = logging.getLogger("dealer_ai.demo_store.registry")


@transaction.atomic
def create_demo_store(
    *,
    slug: str,
    archetype: str,
    name: Optional[str] = None,
    actor=None,
) -> tuple[Dealership, ScenarioSummary]:
    """Create a fresh demo dealership + run the archetype builder.

    Atomic — either the Dealership row + every scenario row commits,
    or nothing does. Idempotency by ``slug`` unique constraint:
    calling ``create_demo_store`` twice with the same slug raises
    :class:`django.db.utils.IntegrityError` (mapped to a 409 shape
    at any endpoint layer per M17.1 pattern; the CLI surface just
    surfaces the DB error).

    ``archetype`` must be in :data:`models.DEMO_ARCHETYPE_CHOICES`;
    ``get_archetype_builder`` raises :class:`ValueError` for
    unknown archetypes.

    Returns a tuple of ``(Dealership, ScenarioSummary)`` — the new
    demo dealership and the summary of what the archetype builder
    seeded.
    """
    display_name = name or slug.replace("-", " ").title()
    dealership = Dealership.objects.create(
        slug=slug,
        name=display_name,
        is_demo=True,
        demo_archetype=archetype,
    )
    _LOGGER.info(
        "demo store created",
        extra={
            "dealership_slug": slug,
            "archetype": archetype,
            "actor": str(actor) if actor is not None else None,
        },
    )
    builder = get_archetype_builder(archetype)
    summary = builder.build(dealership)
    return dealership, summary


@transaction.atomic
def reset_demo_store(
    *,
    dealership: Dealership,
    actor=None,
) -> ScenarioSummary:
    """Reset a demo dealership to its canonical starting state.

    Belt-and-suspenders guard per §5.c Option A:

    1. :class:`NonDemoResetError` raised if
       ``dealership.is_demo=False``.
    2. ``assert dealership.is_demo`` fires at the top of the
       write path — a defensive second layer in case a future
       refactor introduces a code path that skips the explicit
       check.

    Deletes every tenanted row that CASCADEs from the Dealership
    FK, then re-invokes the archetype builder. The Dealership row
    itself + its ``is_demo`` + ``demo_archetype`` fields stay
    stable so tester logins + bookmarks referencing the dealership
    pk continue to work.

    Returns a fresh :class:`ScenarioSummary` naming the newly-
    seeded rows.
    """
    if not dealership.is_demo:
        raise NonDemoResetError(
            f"reset_demo_store refuses to touch dealership "
            f"{dealership.slug!r} (is_demo=False). Only demo "
            f"dealerships can be reset via this path."
        )
    assert dealership.is_demo, (
        "reset_demo_store belt-and-suspenders assert failed — "
        f"dealership {dealership.slug!r} reached the write path "
        "with is_demo=False. Broken invariant."
    )

    archetype = dealership.demo_archetype
    if not archetype:
        raise NonDemoResetError(
            f"reset_demo_store: dealership {dealership.slug!r} "
            "is marked is_demo=True but has no demo_archetype "
            "set — cannot dispatch to an archetype builder."
        )

    # Delete every tenanted child. The FKs use CASCADE, so
    # deleting them explicitly is a no-op if we just deleted the
    # Dealership — but we preserve the Dealership row, so we
    # iterate its reverse-FK related-name managers and delete the
    # child rows only. Cheaper + safer than "delete dealership,
    # create new dealership" because it preserves the pk.
    _delete_demo_store_children(dealership)

    _LOGGER.info(
        "demo store reset",
        extra={
            "dealership_slug": dealership.slug,
            "archetype": archetype,
            "actor": str(actor) if actor is not None else None,
        },
    )

    # Refetch to guarantee the builder sees the fully-cleared state.
    dealership.refresh_from_db()
    builder = get_archetype_builder(archetype)
    summary = builder.build(dealership)
    return summary


def _delete_demo_store_children(dealership: Dealership) -> None:
    """Delete every tenanted row keyed to ``dealership`` except the
    Dealership row itself.

    Iterates every tenancy carrier from :data:`_TENANT_CARRIER_MODEL_NAMES`
    and calls ``.filter(dealership=dealership).delete()``. Runs inside
    the caller's atomic block so a partial delete rolls back.

    Order matters for PROTECT FKs (e.g. ``JournalEntryLine.account``
    PROTECT vs ``GLAccount``), but Django's ORM handles cascade
    ordering via the collector. If a scenario builder ever
    introduces a row shape that PROTECT-blocks deletion, the reset
    path will raise a ``ProtectedError`` at the offending model —
    caught in the atomic block, rolled back, surfaced to the caller.
    """
    from django.apps import apps as django_apps

    from ..tenancy import _TENANT_CARRIER_MODEL_NAMES

    for model_name in _TENANT_CARRIER_MODEL_NAMES:
        Model = django_apps.get_model("dealer_ai", model_name)
        Model.objects.filter(dealership=dealership).delete()


def list_demo_stores() -> list[Dealership]:
    """Return every :class:`Dealership` where ``is_demo=True``.

    Pure. Read-only. Ordered by ``slug`` for deterministic output.
    Callers can inspect ``.demo_archetype`` on each row to
    distinguish archetypes.
    """
    return list(
        Dealership.objects.filter(is_demo=True).order_by("slug")
    )
