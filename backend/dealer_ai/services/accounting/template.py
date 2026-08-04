"""Milestone 28 · Increment 1 (SESSION_195) — journal-entry template verbs.

Three verbs per MILESTONE_28_PLANNING.md §5.b M28.1. Templates are
*recipes*, not *postings* — the actual posting still flows through
:func:`services.accounting.post_journal_entry` (M13.1) when an operator
instantiates a template. This module only handles template CRUD-adjacent
work (create, list, get).

- :func:`create_journal_entry_template` — atomic write of a
  JournalEntryTemplate + its lines. Refuses duplicate names within
  a tenant, unbalanced line sets (using non-null amounts only),
  cross-tenant account references, and empty / malformed lines.
- :func:`list_journal_entry_templates` — tenant-scoped active-only list.
- :func:`get_journal_entry_template` — tenant-scoped read.

Immutability posture (per M28.0 §5.b architectural verification): a
JournalEntryTemplate is editable in principle — templates are recipes,
not the ledger. At M28 no edit / update / delete endpoints are shipped
(§3 deferral); the ``is_active`` soft-hide flag exists at the DB layer
for future use. Future variable-amount templates (depreciation,
utilities, payroll accruals) can be shipped without a DB migration —
serializer relaxes the non-null-amount requirement + instantiation UI
prompts for missing amounts.

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
    """Raised when a line has a malformed shape at M28.

    At M28 the create serializer requires ``amount`` to be non-null
    and > 0. Future variable-amount work relaxes the non-null
    constraint; this error remains the catch-all for
    negative / zero amounts, missing ``side``, and other line-shape
    issues. Mapped to HTTP 400.
    """


class UnbalancedJournalEntryTemplateError(ValueError):
    """Raised when ``sum(debit-side amounts) != sum(credit-side amounts)``.

    At M28 all lines have populated amounts; the balance check
    validates against every line. Future variable-amount templates
    will only validate populated (non-null) amounts at template
    creation; the instantiation flow validates full balance at
    posting time. Mapped to HTTP 400.
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

    ``amount`` is nullable at the type level (matching the model's
    forward-compat schema), but at M28 the create serializer requires
    non-null. Future variable-amount work relaxes the requirement.
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
    """Return ``(total_debit_side, total_credit_side)``; raises on invariant break.

    At M28: every line must have non-null amount > 0, correct ``side``
    value, and an account belonging to the tenant. Debit-side and
    credit-side totals must equal.
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
        if line.amount is None:
            raise InvalidJournalEntryTemplateLineError(
                f"Line {idx}: amount is required at M28 (variable-amount "
                "templates deferred to a future milestone)."
            )
        amount = _as_decimal(line.amount)
        if amount <= _ZERO:
            raise InvalidJournalEntryTemplateLineError(
                f"Line {idx}: amount must be positive (got {amount})."
            )
        if line.account.dealership_id != dealership.id:
            raise CrossTenantGLAccountError(
                f"Line {idx}: GLAccount {line.account.pk} belongs to "
                "another tenant."
            )
        if line.side == "debit":
            total_debit += amount
        else:
            total_credit += amount

    if total_debit != total_credit:
        raise UnbalancedJournalEntryTemplateError(
            f"Template unbalanced: debit-side={total_debit} != "
            f"credit-side={total_credit}."
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
    - Any line with null / non-positive amount, bad ``side`` value
      (:class:`InvalidJournalEntryTemplateLineError` — 400).
    - Any line whose ``account`` belongs to another tenant
      (:class:`CrossTenantGLAccountError` — 404).
    - Sum of debit-side amounts != sum of credit-side amounts
      (:class:`UnbalancedJournalEntryTemplateError` — 400).
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
    *, pk: int, dealership: Dealership
) -> Optional[JournalEntryTemplate]:
    """Tenant-scoped JournalEntryTemplate read.

    Returns ``None`` when the pk doesn't exist or belongs to another
    tenant (fail-closed — the endpoint layer maps to 404).
    """
    try:
        return JournalEntryTemplate.objects.get(
            pk=pk, dealership=dealership
        )
    except JournalEntryTemplate.DoesNotExist:
        return None
