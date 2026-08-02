"""Milestone 17 · Increment 1 (SESSION_145) — trial-balance materialization.

Three verbs per MILESTONE_17_PLANNING.md §7 M17.1 + §5.a-§5.f (all
as-recommended at SESSION_145 open):

- :func:`freeze_trial_balance` — atomic sync-sibling verb per §5.c
  Option A. Calls :func:`compute_trial_balance` with the operator's
  ``as_of``, materializes header (:class:`TrialBalanceSnapshot`) +
  child rows (:class:`TrialBalanceSnapshotRow`) in one transaction.
- :func:`list_trial_balance_snapshots` — paginated tenant-scoped
  list per M14.1 pattern.
- :func:`get_trial_balance_snapshot` — tenant-scoped retrieve.

Uniqueness discipline per §5.d Option A:
``TrialBalanceSnapshot(dealership, as_of)`` is unique. A duplicate
raises :class:`DuplicateTrialBalanceSnapshotError` (mapped to 409
at the endpoint layer). The DB-level ``UniqueConstraint`` is the
authoritative guard; the service verb catches
:class:`IntegrityError` from the constraint violation and re-raises
as the domain error.

Immutability posture per §5.f Option A: once frozen, snapshots are
never re-materialized in place. Backdated ``JournalEntry`` rows
continue to affect the *live*
:func:`compute_trial_balance` result but do NOT touch frozen rows.

Cross-tenant posture per M13.1 fail-closed convention: passing a
snapshot pk that belongs to another tenant returns ``None`` from
:func:`get_trial_balance_snapshot` (endpoint layer maps to 404).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from django.db import IntegrityError, transaction

from ...models import (
    Dealership,
    TrialBalanceSnapshot,
    TrialBalanceSnapshotRow,
)
from .snapshot import compute_trial_balance


class DuplicateTrialBalanceSnapshotError(ValueError):
    """Raised when ``(dealership, as_of)`` already has a snapshot.

    Mapped to HTTP 409 at the endpoint layer — the operator
    attempted to freeze a moment already captured. Second freeze
    at the exact same instant is either a UI double-click or an
    operational mistake worth surfacing per §5.d Option A.
    """


@dataclass(frozen=True)
class TrialBalanceSnapshotListPage:
    """One page of the paginated tenant-scoped snapshot list.

    Mirrors :class:`JournalEntryListPage` shape (M14.1 pattern).
    Zero-portfolio tenants return ``snapshots=()`` +
    ``total_count=0`` — not a 404.
    """

    snapshots: tuple[TrialBalanceSnapshot, ...]
    total_count: int
    page: int
    page_size: int


@transaction.atomic
def freeze_trial_balance(
    *,
    dealership: Dealership,
    as_of: dt.datetime,
    actor=None,
) -> TrialBalanceSnapshot:
    """Materialize a durable trial-balance snapshot for one tenant.

    Atomic — either the header + every child row commits, or
    nothing does. Calls :func:`compute_trial_balance` internally
    with the operator's ``as_of``; persists the header + rows in
    one transaction per §5.b Option B.

    Refuses:

    - Duplicate ``(dealership, as_of)`` —
      :class:`DuplicateTrialBalanceSnapshotError` (409).

    Zero-portfolio behavior per §0.a M13.3 decision 5 + §0.a M17
    Q3: a dealership with no postings still yields a valid
    snapshot with ``rows=[]``, balanced totals of zero. That's a
    legitimate record of "no activity through this date."

    Frozen row values (``account_code`` / ``account_name`` /
    ``account_type``) are captured from the current live
    :class:`GLAccount` state at freeze time. Later COA renames do
    not touch frozen rows per §3 item 12.

    Returns the persisted :class:`TrialBalanceSnapshot` with
    ``rows`` accessible via the reverse-FK related manager.
    """
    computation = compute_trial_balance(
        dealership=dealership, as_of=as_of
    )

    try:
        snapshot = TrialBalanceSnapshot.objects.create(
            dealership=dealership,
            as_of=computation.as_of,
            total_debits=computation.total_debits,
            total_credits=computation.total_credits,
            is_balanced=computation.is_balanced,
            created_by=actor,
        )
    except IntegrityError as exc:
        raise DuplicateTrialBalanceSnapshotError(
            f"TrialBalanceSnapshot for dealership {dealership.slug!r} "
            f"at as_of={computation.as_of.isoformat()} already exists."
        ) from exc

    TrialBalanceSnapshotRow.objects.bulk_create(
        [
            TrialBalanceSnapshotRow(
                dealership=dealership,
                snapshot=snapshot,
                account_code=row.account_code,
                account_name=row.account_name,
                account_type=row.account_type,
                debit_total=row.debit_total,
                credit_total=row.credit_total,
                natural_balance=row.natural_balance,
            )
            for row in computation.rows
        ]
    )

    return snapshot


def list_trial_balance_snapshots(
    *,
    dealership: Dealership,
    page: int = 1,
    page_size: int = 25,
) -> TrialBalanceSnapshotListPage:
    """Paginated tenant-scoped snapshot list.

    Pure. Read-only. Ordered ``-as_of, -created_at`` (recent-first)
    per :class:`TrialBalanceSnapshot.Meta.ordering`.

    Zero-portfolio semantics per M13 §6 lesson 8: a tenant with no
    snapshots returns ``snapshots=()`` + ``total_count=0``. Not a
    404.

    Callers trusted to pass ``page >= 1`` and ``1 <= page_size <=
    100``; the endpoint layer validates via serializer. Out-of-
    range slice into empty tuple rather than erroring.
    """
    qs = (
        TrialBalanceSnapshot.objects.filter(dealership=dealership)
        .select_related("created_by")
        .order_by("-as_of", "-created_at", "-id")
    )
    total_count = qs.count()
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return TrialBalanceSnapshotListPage(
        snapshots=tuple(qs[start:end]),
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


def get_trial_balance_snapshot(
    *,
    dealership: Dealership,
    snapshot_id: int,
) -> Optional[TrialBalanceSnapshot]:
    """Tenant-scoped snapshot retrieve.

    Returns the :class:`TrialBalanceSnapshot` with ``pk=snapshot_id``
    if it belongs to ``dealership``. Cross-tenant or missing lookups
    return ``None`` — the endpoint layer maps to 404 per fail-closed
    posture (do not confirm the cross-tenant snapshot's existence).

    Frozen rows come along via the reverse-FK related manager on
    ``.rows`` (ordered by ``account_code`` per
    :class:`TrialBalanceSnapshotRow.Meta.ordering`).
    """
    return (
        TrialBalanceSnapshot.objects.filter(
            dealership=dealership, pk=snapshot_id
        )
        .select_related("created_by")
        .first()
    )
