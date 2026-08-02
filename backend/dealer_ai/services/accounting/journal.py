"""Milestone 13 · Increment 1 (SESSION_129) — journal entry verbs.

Three verbs per MILESTONE_13_PLANNING.md §7 M13.1. See package
``__init__`` for the domain-error → HTTP mapping contract.

- :func:`post_journal_entry` — atomic write of a JournalEntry + its
  lines. Refuses unbalanced entries + cross-tenant account references
  + missing lines.
- :func:`reverse_journal_entry` — atomic write of the reversal
  JournalEntry with inverted debits/credits.
- :func:`get_journal_entry` — tenant-scoped read.

Immutability posture (per §5.c Option A): a JournalEntry has no
update verb. Corrections happen via reversal. The absence of an
``update_journal_entry`` verb here is intentional and load-bearing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from ...models import (
    Dealership,
    GLAccount,
    JournalEntry,
    JournalEntryLine,
)


class UnbalancedJournalEntryError(ValueError):
    """Raised when ``sum(debits) != sum(credits)``.

    Mapped to HTTP 400 at the endpoint layer — caller-input error,
    not a fail-closed lookup miss.
    """


class EmptyJournalEntryError(ValueError):
    """Raised when ``lines`` is empty.

    A JournalEntry with no lines is meaningless (nothing to post) and
    would trivially "balance" at 0 == 0. Mapped to HTTP 400.
    """


class InvalidJournalLineError(ValueError):
    """Raised when a line has both debit AND credit populated, or
    neither (both zero).

    Each line represents exactly one side of a posting. Mapped to
    HTTP 400.
    """


class CrossTenantGLAccountError(ValueError):
    """Raised when a line's ``account`` belongs to a different tenant.

    Mapped to HTTP 404 at the endpoint layer — fail-closed lookup
    posture (do not confirm the cross-tenant account's existence).
    """


class CrossTenantJournalEntryError(ValueError):
    """Raised when :func:`reverse_journal_entry` or
    :func:`get_journal_entry` is called with a ``dealership`` that
    does not match the target entry's tenant.

    Mapped to HTTP 404 at the endpoint layer — fail-closed.
    """


class ImmutableJournalEntryError(ValueError):
    """Raised on any attempt to modify a posted JournalEntry.

    Per §5.c Option A journal entries are immutable — this error
    exists as an anchor for callers that mistakenly try to mutate.
    Currently only raised by :func:`reverse_journal_entry` when the
    ``reason`` argument is empty (every reversal must state its
    reason per audit-trail requirement). Mapped to HTTP 409 at
    the endpoint layer.
    """


@dataclass(frozen=True)
class JournalLineInput:
    """One (debit, credit) tuple to post against an account.

    Exactly one of ``debit`` / ``credit`` must be non-zero. Both zero
    or both non-zero raise :class:`InvalidJournalLineError` at post
    time.
    """

    account: GLAccount
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    memo: str = ""


_ZERO = Decimal("0.00")


def _as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _validate_lines(
    dealership: Dealership, lines: list[JournalLineInput]
) -> tuple[Decimal, Decimal]:
    """Return ``(total_debit, total_credit)``, raising on any invariant break."""
    if not lines:
        raise EmptyJournalEntryError(
            "JournalEntry requires at least one line."
        )

    total_debit = _ZERO
    total_credit = _ZERO
    for idx, line in enumerate(lines):
        debit = _as_decimal(line.debit)
        credit = _as_decimal(line.credit)
        if debit < _ZERO or credit < _ZERO:
            raise InvalidJournalLineError(
                f"Line {idx}: debit and credit must be non-negative."
            )
        if debit > _ZERO and credit > _ZERO:
            raise InvalidJournalLineError(
                f"Line {idx}: exactly one of debit / credit must be "
                "non-zero (both populated is not a valid posting)."
            )
        if debit == _ZERO and credit == _ZERO:
            raise InvalidJournalLineError(
                f"Line {idx}: exactly one of debit / credit must be "
                "non-zero (both zero is not a valid posting)."
            )
        if line.account.dealership_id != dealership.id:
            raise CrossTenantGLAccountError(
                f"Line {idx}: GLAccount {line.account.pk} belongs to "
                "another tenant."
            )
        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise UnbalancedJournalEntryError(
            f"Entry unbalanced: debits={total_debit} != credits={total_credit}."
        )
    return total_debit, total_credit


@transaction.atomic
def post_journal_entry(
    *,
    dealership: Dealership,
    description: str,
    lines: list[JournalLineInput],
    posted_at: Optional[dt.datetime] = None,
    posted_by_user=None,
) -> JournalEntry:
    """Post a balanced double-entry JournalEntry.

    Atomic — either the entry + every line commits, or nothing does.

    Refuses:

    - Empty ``lines`` (:class:`EmptyJournalEntryError` — 400).
    - Any line with both debit + credit set, both zero, or negative
      (:class:`InvalidJournalLineError` — 400).
    - Any line whose ``account`` belongs to another tenant
      (:class:`CrossTenantGLAccountError` — 404).
    - Unbalanced entry — ``sum(debits) != sum(credits)``
      (:class:`UnbalancedJournalEntryError` — 400).

    ``posted_at`` defaults to ``timezone.now()``. Callers posting
    accruals with an effective business date distinct from insertion
    time (e.g. Aug 3 posting of a Jul 31 accrual) supply it
    explicitly.
    """
    _validate_lines(dealership, lines)

    entry = JournalEntry.objects.create(
        dealership=dealership,
        description=description,
        posted_at=posted_at or timezone.now(),
        posted_by_user=posted_by_user,
    )
    JournalEntryLine.objects.bulk_create(
        [
            JournalEntryLine(
                dealership=dealership,
                entry=entry,
                account=line.account,
                debit=_as_decimal(line.debit),
                credit=_as_decimal(line.credit),
                memo=line.memo,
            )
            for line in lines
        ]
    )
    return entry


@transaction.atomic
def reverse_journal_entry(
    *,
    dealership: Dealership,
    entry: JournalEntry,
    reason: str,
    posted_at: Optional[dt.datetime] = None,
    posted_by_user=None,
) -> JournalEntry:
    """Post the reversal of a prior JournalEntry.

    Atomic — creates a new JournalEntry with ``reverses=entry`` and
    lines whose debits/credits are swapped from the original's lines.
    The original row is not modified (per §5.c Option A immutability).

    Refuses:

    - Cross-tenant target
      (:class:`CrossTenantJournalEntryError` — 404).
    - Empty ``reason``
      (:class:`ImmutableJournalEntryError` — 409). Every reversal
      must state its reason per audit-trail requirement.

    Reversing a reversal is legal — the double reversal restores the
    original economic effect. Both reversals remain in the audit trail.
    """
    if entry.dealership_id != dealership.id:
        raise CrossTenantJournalEntryError(
            f"JournalEntry {entry.pk} belongs to another tenant."
        )
    if not (reason or "").strip():
        raise ImmutableJournalEntryError(
            f"JournalEntry {entry.pk} is immutable; reversal requires "
            "a non-empty ``reason``."
        )

    reversal = JournalEntry.objects.create(
        dealership=dealership,
        description=f"Reversal of #{entry.pk}: {entry.description}",
        posted_at=posted_at or timezone.now(),
        posted_by_user=posted_by_user,
        reverses=entry,
        reason=reason.strip(),
    )
    original_lines = list(entry.lines.all())
    JournalEntryLine.objects.bulk_create(
        [
            JournalEntryLine(
                dealership=dealership,
                entry=reversal,
                account=line.account,
                # Swap debit <-> credit for the reversal.
                debit=line.credit,
                credit=line.debit,
                memo=f"Reversal: {line.memo}" if line.memo else "Reversal",
            )
            for line in original_lines
        ]
    )
    return reversal


def get_journal_entry(
    *, pk: int, dealership: Dealership
) -> Optional[JournalEntry]:
    """Tenant-scoped JournalEntry read.

    Returns ``None`` when the pk doesn't exist or belongs to another
    tenant (fail-closed — the endpoint layer maps to 404).
    """
    try:
        return JournalEntry.objects.get(pk=pk, dealership=dealership)
    except JournalEntry.DoesNotExist:
        return None


# --- Milestone 14 · Increment 1 (SESSION_134) — paginated list verb -----------


@dataclass(frozen=True)
class JournalEntryListPage:
    """One page of the paginated tenant-scoped JournalEntry list.

    Fields:

    - ``entries`` — the JournalEntry rows for this page, ordered
      ``-posted_at, -id`` (recent-first, stable secondary key for
      pagination). Each row carries a ``.total_debit`` annotation
      (sum of its lines' debits) for the list projection at the
      endpoint layer.
    - ``total_count`` — total matching rows across all pages for
      this tenant.
    - ``page`` — 1-indexed page number (echoes the caller's input).
    - ``page_size`` — rows per page (echoes the caller's input).

    Zero-portfolio semantics per M13 §6 lesson 8: a tenant with no
    postings returns ``entries=()`` + ``total_count=0``. Not a 404.
    """

    entries: tuple[JournalEntry, ...]
    total_count: int
    page: int
    page_size: int


def list_journal_entries(
    *,
    dealership: Dealership,
    page: int = 1,
    page_size: int = 25,
) -> JournalEntryListPage:
    """Paginated tenant-scoped JournalEntry list.

    Pure. Read-only. No filters at M14.1 per §5.b Option B — filter
    surface (date range, posted_by, reversal-only) layers at M15+
    when operator evidence names specific needs.

    Ordering ``-posted_at, -id`` gives recent-first with a stable
    secondary key so pagination is deterministic when many entries
    share a ``posted_at`` (bulk detector runs at 10:00 project-time
    stamp every VehicleCost post with the same timestamp).

    Each returned entry has a ``.total_debit`` annotation (sum of
    line debits) so the endpoint projection avoids per-row N+1
    queries. ``select_related("posted_by_user")`` keeps username
    access single-query.

    Callers are trusted to pass ``page >= 1`` and
    ``1 <= page_size <= 100``; the endpoint layer validates the
    query params via a DRF serializer. Out-of-range inputs slice
    into an empty tuple rather than erroring — the pagination
    contract is best-effort.
    """
    zero = Value(
        _ZERO,
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    qs = (
        JournalEntry.objects.filter(dealership=dealership)
        .select_related("posted_by_user")
        .annotate(total_debit=Coalesce(Sum("lines__debit"), zero))
        .order_by("-posted_at", "-id")
    )
    total_count = qs.count()
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return JournalEntryListPage(
        entries=tuple(qs[start:end]),
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
