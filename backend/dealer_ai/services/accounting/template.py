"""Milestone 28 · Increment 1 (SESSION_195) — journal-entry template verbs.
Milestone 29 · Increment 1 (SESSION_198) — variable-amount relaxation.
Milestone 30 · Increment 1 (SESSION_201) — edit + soft-delete verbs.

Five verbs per MILESTONE_28_PLANNING.md §5.b M28.1 +
MILESTONE_30_PLANNING.md §5.b D1. Templates are *recipes*, not
*postings* — the actual posting still flows through
:func:`services.accounting.post_journal_entry` (M13.1) when an operator
instantiates a template. This module handles template CRUD.

- :func:`create_journal_entry_template` — atomic write of a
  JournalEntryTemplate + its lines. Refuses duplicate names within
  a tenant, unbalanced populated-line sets, cross-tenant account
  references, and empty / malformed lines.
- :func:`list_journal_entry_templates` — tenant-scoped active-only list.
- :func:`get_journal_entry_template` — tenant-scoped read; accepts
  ``include_inactive: bool = False`` (M30.1 symmetry with the list
  verb) so the future Restore-inactive path and internal
  edit / delete callers can opt into fetching soft-hidden rows.
- :func:`update_journal_entry_template` — M30.1. Atomic edit of a
  template's name / description / lines. Full-replace of lines
  (small ordered set, typically 2–5; partial patch adds serializer
  surface without operator value per M30.0 §5.b D1). Preserves
  ``is_active`` (activation is DELETE-only per D5). Same error
  surface as create.
- :func:`delete_journal_entry_template` — M30.1. Soft-delete —
  sets ``is_active = False`` and returns the updated row.
  Idempotent (DELETE of an already-inactive template returns the
  same row without state change; the endpoint layer maps to 204).
  Historical JournalEntry rows instantiated from this template
  are untouched by construction — no FK exists (M28.0 §5.b domain
  separation).

Immutability posture (per M28.0 §5.b architectural verification): a
JournalEntryTemplate is editable in principle — templates are recipes,
not the ledger. M30.1 spends the reservation: edit + soft-delete
operator surfaces land at the endpoint layer; the ``is_active`` flag
is now backed by a DELETE verb (no ``is_active`` mutation via edit —
that's a D5 design constraint).

**M29 variable-amount posture** (per MILESTONE_29_PLANNING.md §5.b D1).
A template line's ``amount`` may be ``None`` — the side + GL account
are fixed at create-time, but the amount is supplied at instantiation.
This spends the ``null=True`` schema reservation from M28.1 migration
0050. Three legitimate template shapes are accepted at create:

1. **Fully fixed** (M28.1 behavior preserved). Every line has an
   ``amount``; debit-side sum == credit-side sum.
2. **Fully variable.** Every line has ``amount = None``; balance
   check trivially passes (both sums zero).
3. **Mixed.** Some lines populated, some null. The populated lines'
   debit-side sum must equal their credit-side sum. Rationale: catches
   the "operator set one fixed amount without matching the other side"
   bug at create time rather than deferring to instantiate.

Full balance is always re-checked at instantiate time by the
:func:`post_journal_entry` (M13.1) service — the template service does
not need to enforce full balance for variable-inclusive templates
because the ledger boundary catches it.

Domain-error → HTTP mapping (consumed by ``views_accounting.py``):

- :class:`EmptyJournalEntryTemplateError` — 400.
- :class:`InvalidJournalEntryTemplateLineError` — 400.
- :class:`UnbalancedJournalEntryTemplateError` — 400.
- :class:`DuplicateJournalEntryTemplateNameError` — 409.
- :class:`CrossTenantGLAccountError` — 404 (reused from journal.py;
  fail-closed).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from ...models import (
    Dealership,
    GLAccount,
    JournalEntryTemplate,
    JournalEntryTemplateLine,
)
from .journal import CrossTenantGLAccountError


class EmptyJournalEntryTemplateError(ValueError):
    """Raised when ``lines`` is empty or has fewer than 2 lines.

    A template with fewer than 2 lines cannot represent a balanced
    posting shape. Mapped to HTTP 400.
    """


class InvalidJournalEntryTemplateLineError(ValueError):
    """Raised when a line has a malformed shape.

    Catch-all for negative / zero amounts (fixed lines only —
    ``amount = None`` is a valid *variable* line at M29), missing
    ``side``, and other line-shape issues. Mapped to HTTP 400.
    """


class UnbalancedJournalEntryTemplateError(ValueError):
    """Raised when ``sum(populated debit) != sum(populated credit)``.

    At M28 all lines had populated amounts and balance validated
    across every line. At M29 variable-inclusive templates validate
    only the populated (non-null) portion at create time; a
    fully-variable template trivially balances (both sums are zero).
    The instantiation flow re-validates full balance at posting time
    through :func:`post_journal_entry` (M13.1). Mapped to HTTP 400.
    """


class DuplicateJournalEntryTemplateNameError(ValueError):
    """Raised when a template's ``name`` collides with an existing
    template in the same tenant.

    Enforced at the DB layer via
    ``uniq_je_template_name_per_dealership`` unique constraint; this
    service-layer error is what the endpoint maps to HTTP 409.
    """


@dataclass(frozen=True)
class TemplateLineInput:
    """One template line input to :func:`create_journal_entry_template`.

    ``amount`` is nullable at both the type and service level as of
    M29 — a ``None`` amount marks the line as *variable* (side + GL
    account fixed, amount supplied at instantiate time). A non-null
    amount marks the line as *fixed* and must be > 0.
    """

    account: GLAccount
    side: str  # "debit" or "credit"
    amount: Optional[Decimal] = None
    memo: str = ""
    ordering: int = 0


_ZERO = Decimal("0.00")
_ALLOWED_SIDES = ("debit", "credit")


def _as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _validate_template_lines(
    dealership: Dealership, lines: list[TemplateLineInput]
) -> tuple[Decimal, Decimal]:
    """Return ``(populated_debit, populated_credit)``; raises on invariant break.

    Every line must have correct ``side`` and an account belonging
    to the tenant. Line ``amount`` is validated per M29 three-state
    logic:

    - ``None`` → variable line; skip balance contribution.
    - Positive Decimal → fixed line; contributes to populated total.
    - Zero or negative Decimal → reject as
      :class:`InvalidJournalEntryTemplateLineError`.

    Balance check runs against the populated (non-null) portion only:
    ``sum(populated debit) == sum(populated credit)``. A fully-variable
    template trivially balances (both sums are zero).
    """
    if len(lines) < 2:
        raise EmptyJournalEntryTemplateError(
            "JournalEntryTemplate requires at least two lines."
        )

    total_debit = _ZERO
    total_credit = _ZERO
    for idx, line in enumerate(lines):
        if line.side not in _ALLOWED_SIDES:
            raise InvalidJournalEntryTemplateLineError(
                f"Line {idx}: side must be one of {_ALLOWED_SIDES}."
            )
        if line.account.dealership_id != dealership.id:
            raise CrossTenantGLAccountError(
                f"Line {idx}: GLAccount {line.account.pk} belongs to "
                "another tenant."
            )
        if line.amount is None:
            # Variable line — amount deferred to instantiation.
            continue
        amount = _as_decimal(line.amount)
        if amount <= _ZERO:
            raise InvalidJournalEntryTemplateLineError(
                f"Line {idx}: amount must be positive (got {amount})."
            )
        if line.side == "debit":
            total_debit += amount
        else:
            total_credit += amount

    if total_debit != total_credit:
        raise UnbalancedJournalEntryTemplateError(
            f"Template unbalanced: populated debit-side={total_debit} != "
            f"populated credit-side={total_credit}."
        )
    return total_debit, total_credit


@transaction.atomic
def create_journal_entry_template(
    *,
    dealership: Dealership,
    name: str,
    description: str,
    lines: list[TemplateLineInput],
) -> JournalEntryTemplate:
    """Create a JournalEntryTemplate + its lines atomically.

    Refuses:

    - Fewer than 2 lines
      (:class:`EmptyJournalEntryTemplateError` — 400).
    - Any line with non-positive amount (zero or negative) or bad
      ``side`` value (:class:`InvalidJournalEntryTemplateLineError`
      — 400). ``amount = None`` is accepted at M29 as a *variable*
      line.
    - Any line whose ``account`` belongs to another tenant
      (:class:`CrossTenantGLAccountError` — 404).
    - Sum of populated debit-side amounts != sum of populated
      credit-side amounts
      (:class:`UnbalancedJournalEntryTemplateError` — 400). Fully-
      variable templates trivially balance (both sums zero).
    - Duplicate name within the tenant
      (:class:`DuplicateJournalEntryTemplateNameError` — 409;
      DB-enforced via unique constraint).
    """
    _validate_template_lines(dealership, lines)

    try:
        template = JournalEntryTemplate.objects.create(
            dealership=dealership,
            name=name,
            description=description,
        )
    except IntegrityError as exc:
        raise DuplicateJournalEntryTemplateNameError(
            f"A JournalEntryTemplate named '{name}' already exists "
            "in this dealership."
        ) from exc

    JournalEntryTemplateLine.objects.bulk_create(
        [
            JournalEntryTemplateLine(
                template=template,
                dealership=dealership,
                account=line.account,
                side=line.side,
                amount=_as_decimal(line.amount) if line.amount is not None else None,
                memo=line.memo,
                ordering=line.ordering,
            )
            for line in lines
        ]
    )
    return template


def list_journal_entry_templates(
    *, dealership: Dealership, include_inactive: bool = False
) -> QuerySet[JournalEntryTemplate]:
    """Tenant-scoped active-only JournalEntryTemplate list.

    Pure. Read-only. Ordered by ``name``. ``include_inactive`` accepts
    True but is currently only exercised by unit tests; endpoint
    exposure is deferred to a future milestone per §3 deferrals.
    """
    qs = JournalEntryTemplate.objects.filter(dealership=dealership)
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs.order_by("name")


def get_journal_entry_template(
    *,
    pk: int,
    dealership: Dealership,
    include_inactive: bool = False,
) -> Optional[JournalEntryTemplate]:
    """Tenant-scoped JournalEntryTemplate read.

    Returns ``None`` when the pk doesn't exist, belongs to another
    tenant, or is soft-deleted (``is_active = False``) unless
    ``include_inactive=True`` (fail-closed — the endpoint layer
    maps ``None`` to 404).

    The ``include_inactive`` kwarg mirrors
    :func:`list_journal_entry_templates` for API symmetry (M30.1).
    Internal callers that must operate on soft-hidden rows (edit,
    delete, future Restore) opt in explicitly; the default keeps
    the public endpoint surface fail-closed on deactivated
    templates.
    """
    qs = JournalEntryTemplate.objects.filter(
        pk=pk, dealership=dealership
    )
    if not include_inactive:
        qs = qs.filter(is_active=True)
    try:
        return qs.get()
    except JournalEntryTemplate.DoesNotExist:
        return None


@transaction.atomic
def update_journal_entry_template(
    *,
    pk: int,
    dealership: Dealership,
    name: str,
    description: str,
    lines: list[TemplateLineInput],
) -> Optional[JournalEntryTemplate]:
    """Full-replace edit of a JournalEntryTemplate + its lines.

    Fetches the template with ``include_inactive=True`` so soft-
    hidden rows remain editable in principle. Returns ``None`` when
    the pk doesn't exist or belongs to another tenant (endpoint
    layer maps to 404). ``is_active`` is preserved as-is — activation
    changes flow through :func:`delete_journal_entry_template`
    (soft-delete) or a future Restore verb.

    Refuses the same conditions as :func:`create_journal_entry_template`:

    - Fewer than 2 lines
      (:class:`EmptyJournalEntryTemplateError` — 400).
    - Any line with non-positive amount or bad ``side`` value
      (:class:`InvalidJournalEntryTemplateLineError` — 400).
      ``amount = None`` remains accepted as an M29 variable line.
    - Any line whose ``account`` belongs to another tenant
      (:class:`CrossTenantGLAccountError` — 404).
    - Sum of populated debit-side amounts != sum of populated
      credit-side amounts
      (:class:`UnbalancedJournalEntryTemplateError` — 400). Fully-
      variable templates trivially balance (both sums zero).
    - Duplicate name within the tenant
      (:class:`DuplicateJournalEntryTemplateNameError` — 409;
      DB-enforced via unique constraint).

    **Full-replace semantics** (per MILESTONE_30_PLANNING.md §5.b
    D1). All existing template lines are deleted; the new ``lines``
    argument becomes the complete replacement set. Rationale:
    template lines are a small ordered set (typically 2–5); a
    partial line patch adds serializer + service surface without
    operator value and risks silent line-ID reuse bugs. The
    ``JournalEntryTemplateLine.template`` FK uses ``CASCADE`` on
    template delete + this bulk-delete + bulk-create replacement
    is atomic within the ``@transaction.atomic`` decorator.
    """
    template = get_journal_entry_template(
        pk=pk, dealership=dealership, include_inactive=True
    )
    if template is None:
        return None

    _validate_template_lines(dealership, lines)

    template.name = name
    template.description = description
    try:
        template.save(update_fields=["name", "description", "updated_at"])
    except IntegrityError as exc:
        raise DuplicateJournalEntryTemplateNameError(
            f"A JournalEntryTemplate named '{name}' already exists "
            "in this dealership."
        ) from exc

    # Full-replace of lines: delete existing + bulk_create the new
    # set. Both operations run inside the @transaction.atomic
    # decorator so partial state is impossible on failure.
    template.lines.all().delete()
    JournalEntryTemplateLine.objects.bulk_create(
        [
            JournalEntryTemplateLine(
                template=template,
                dealership=dealership,
                account=line.account,
                side=line.side,
                amount=_as_decimal(line.amount) if line.amount is not None else None,
                memo=line.memo,
                ordering=line.ordering,
            )
            for line in lines
        ]
    )
    template.refresh_from_db()
    return template


def delete_journal_entry_template(
    *, pk: int, dealership: Dealership
) -> Optional[JournalEntryTemplate]:
    """Soft-delete a JournalEntryTemplate by setting ``is_active = False``.

    Fetches with ``include_inactive=True`` so a repeat DELETE on an
    already-inactive row returns the same soft-hidden row without
    state change (idempotent). Returns ``None`` when the pk doesn't
    exist or belongs to another tenant (endpoint layer maps to
    404); otherwise returns the updated row (endpoint layer maps
    to 204).

    **Soft-delete integrity** (per MILESTONE_30_PLANNING.md §4.7).
    No FK exists from :class:`JournalEntry` to
    :class:`JournalEntryTemplate` (M28.0 §5.b domain separation).
    Historical journal entries instantiated from this template are
    a snapshot copy of the template's line values at instantiation
    time and hold no back-reference. Setting ``is_active = False``
    therefore has zero effect on any existing journal entry, trial
    balance, snapshot, or JE list / detail surface. The
    :func:`list_journal_entry_templates` verb filters
    ``is_active=True`` by default, so operator-visible template
    lists automatically exclude soft-deleted rows on next refetch.
    """
    template = get_journal_entry_template(
        pk=pk, dealership=dealership, include_inactive=True
    )
    if template is None:
        return None
    if template.is_active:
        template.is_active = False
        template.save(update_fields=["is_active", "updated_at"])
    return template
