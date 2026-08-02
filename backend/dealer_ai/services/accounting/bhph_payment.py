"""Milestone 16 · Increment 1 (SESSION_143) — BHPH payment GL detector.

Per MILESTONE_16_PLANNING.md §5 M16.1 + §0.a M16.0 decisions
(all as-recommended at SESSION_142 open):

- :func:`detect_unposted_bhph_payments` — pure query returning the
  unposted BhphPayment rows for one tenant. No writes.
- :func:`post_bhph_payment_journal` — atomic sibling-service verb.
  Posts a 2- or 3-line JournalEntry (DR 100000 Cash on Hand for the
  full payment ``amount``; CR 123000 BHPH Notes Receivable for
  ``applied_to_principal`` when non-zero; CR 430000 BHPH Interest
  Income for ``applied_to_interest`` when non-zero) and denormalizes
  ``posted_at`` on the source row.
- :func:`post_all_unposted_bhph_payments_for_dealership` —
  orchestrator. Iterates unposted rows for one tenant, posts each
  atomically, returns a summary matching M13.2's return shape.

**Uniform cash mapping.** Every payment DRs 100000 Cash on Hand
regardless of ``method`` (§5.c Option A). Method-aware fund-flow
routing (cash → 100000, ACH → 110000 Bank Operating, etc.) defers
pending a deposit-workflow milestone. Matches M13.2's uniform-mapping
posture.

**Zero-amount line handling.** Skip zero lines per §5.e Option A —
zero-interest payment posts a 2-line entry (DR Cash / CR Notes Rcv);
zero-principal (interest-only) payment posts a 2-line entry (DR Cash
/ CR Interest Income). Both-zero payments are architecturally
impossible upstream — :func:`services.bhph_payments.allocate_payment`
refuses zero-total amounts.

**Fees column asserted zero.** M12.2 keeps ``applied_to_fees`` at
``Decimal("0.00")`` (no fee-charging entity exists). M16.1 asserts
this invariant with :class:`UnexpectedBhphPaymentFeesError`; when a
future BhphFee milestone starts populating fees, that milestone will
extend this module with a CR fee-income line and remove the
assertion.

**Idempotency.** ``posted_at__isnull=True`` filter gives cross-run
idempotency naturally (matches M13.2). A row posted successfully has
``posted_at`` populated inside the same ``@transaction.atomic`` block
that inserts the JournalEntry — either both writes commit or neither
does.
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ...models import BhphPayment, Dealership, GLAccount
from .journal import (
    CrossTenantGLAccountError,
    JournalLineInput,
    post_journal_entry,
)
from .vehicle_cost import MissingDefaultAccountError


_LOGGER = logging.getLogger("dealer_ai.accounting.bhph_payment")


# Local account-code constants per M15.1 §0.a decision 3 (duplicate
# rather than promote to shared helper — evidence gate for a shared-
# constants module not tripped). Same values already declared in
# ``sale_booking.py`` for 100000 / 123000; ``430000`` is new to M16.1.
CASH_ACCOUNT_CODE = "100000"
BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE = "123000"
BHPH_INTEREST_INCOME_ACCOUNT_CODE = "430000"


class UnexpectedBhphPaymentFeesError(RuntimeError):
    """Raised when a BhphPayment carries a non-zero ``applied_to_fees``.

    Signals a broken invariant — M12.2 keeps ``applied_to_fees`` at
    ``Decimal("0.00")`` because no fee-charging entity exists yet.
    When a future BhphFee milestone ships, that milestone will extend
    :func:`post_bhph_payment_journal` with a fee-income line and
    remove this guard. Fires only if a future write path populates
    the column without wiring the GL side.
    """


def detect_unposted_bhph_payments(
    *, dealership: Dealership
) -> QuerySet[BhphPayment]:
    """Return the unposted BhphPayment rows for a tenant.

    Pure query — no writes. Filter matches the detector's write
    filter so ``list(detect_unposted_bhph_payments(...))`` is the
    exact set the next
    :func:`post_all_unposted_bhph_payments_for_dealership`
    invocation will act on.

    Per §5.d Option A idempotency posture (mirrors M13.2's
    ``detect_unposted_costs`` verbatim):

    - ``posted_at__isnull=True`` gives cross-run idempotency. A
      previously-posted row is skipped without needing detector-side
      state.

    Ordering matches ``paid_at, id`` so posting order is deterministic
    for tests + operator drill-back.
    """
    return BhphPayment.objects.filter(
        dealership=dealership,
        posted_at__isnull=True,
    ).order_by("paid_at", "id")


def _lookup_required_account(
    dealership: Dealership, code: str
) -> GLAccount:
    """Return the active :class:`GLAccount` with ``code`` for ``dealership``.

    Mirrors :func:`services.accounting.vehicle_cost._lookup_required_account`
    verbatim per M15.1 §0.a decision 3 (evidence gate for a shared
    helper not tripped). Raises
    :class:`MissingDefaultAccountError` when the account is absent or
    inactive — signals a broken seed-invariant, not a user error.
    """
    try:
        return GLAccount.objects.get(
            dealership=dealership, code=code, is_active=True
        )
    except GLAccount.DoesNotExist as exc:
        raise MissingDefaultAccountError(
            f"Required default COA account {code!r} missing (or "
            f"inactive) for dealership {dealership.slug!r}. Run "
            "services.accounting.seed_default_coa or re-activate "
            "the account before M16.1 BHPH-payment posting will succeed."
        ) from exc


@transaction.atomic
def post_bhph_payment_journal(
    *,
    dealership: Dealership,
    bhph_payment: BhphPayment,
    posted_at: Optional[dt.datetime] = None,
) -> BhphPayment:
    """Post the GL journal entry for one BhphPayment row.

    Atomic — either the JournalEntry insert AND the ``posted_at``
    denormalization commit, or neither does (matches M13.2's atomic-
    sibling-service posture per M12 §6 lesson 11).

    Refuses:

    - Cross-tenant BhphPayment
      (:class:`journal.CrossTenantGLAccountError` — 404-shape).
    - Missing default COA accounts
      (:class:`MissingDefaultAccountError` — signals a broken
      invariant, not a user error).
    - Non-zero ``applied_to_fees``
      (:class:`UnexpectedBhphPaymentFeesError` — asserts the M12
      zero-fees invariant; future BhphFee milestone extends this
      verb).

    Line composition per §5.c Option A + §5.e Option A:

    - **DR 100000 Cash on Hand** for the full ``amount`` (always
      present).
    - **CR 123000 BHPH Notes Receivable** for
      ``applied_to_principal`` (skipped when zero — early-payoff or
      interest-only payment case).
    - **CR 430000 BHPH Interest Income** for
      ``applied_to_interest`` (skipped when zero — early-payoff
      case).

    Returns the refreshed BhphPayment instance with ``posted_at``
    populated.
    """
    if bhph_payment.dealership_id != dealership.id:
        raise CrossTenantGLAccountError(
            f"BhphPayment {bhph_payment.pk} belongs to another tenant."
        )

    if bhph_payment.applied_to_fees != Decimal("0.00"):
        raise UnexpectedBhphPaymentFeesError(
            f"BhphPayment {bhph_payment.pk} has non-zero "
            f"applied_to_fees={bhph_payment.applied_to_fees}. M16.1 "
            "does not wire fee-income posting (no BhphFee entity "
            "exists at M12.2). A future BhphFee milestone must extend "
            "post_bhph_payment_journal with a fee-income line before "
            "populating this column."
        )

    cash = _lookup_required_account(dealership, CASH_ACCOUNT_CODE)

    note_pk = bhph_payment.note_id
    method_display = bhph_payment.get_method_display()
    description = (
        f"M12 BHPH payment intake — BhphPayment #{bhph_payment.pk} "
        f"against note #{note_pk} (${bhph_payment.amount} "
        f"{method_display})"
    )
    line_memo = f"BhphPayment #{bhph_payment.pk} — note #{note_pk}"

    lines: list[JournalLineInput] = [
        JournalLineInput(
            account=cash,
            debit=bhph_payment.amount,
            memo=f"{line_memo} — cash in",
        ),
    ]

    if bhph_payment.applied_to_principal > Decimal("0.00"):
        notes_rcv = _lookup_required_account(
            dealership, BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE
        )
        lines.append(
            JournalLineInput(
                account=notes_rcv,
                credit=bhph_payment.applied_to_principal,
                memo=f"{line_memo} — principal",
            )
        )

    if bhph_payment.applied_to_interest > Decimal("0.00"):
        interest_income = _lookup_required_account(
            dealership, BHPH_INTEREST_INCOME_ACCOUNT_CODE
        )
        lines.append(
            JournalLineInput(
                account=interest_income,
                credit=bhph_payment.applied_to_interest,
                memo=f"{line_memo} — interest",
            )
        )

    effective = posted_at or timezone.now()
    post_journal_entry(
        dealership=dealership,
        description=description,
        posted_at=effective,
        lines=lines,
    )

    bhph_payment.posted_at = effective
    bhph_payment.save(update_fields=["posted_at", "updated_at"])
    return bhph_payment


def post_all_unposted_bhph_payments_for_dealership(
    *,
    dealership: Dealership,
    now: Optional[dt.datetime] = None,
) -> dict[str, Any]:
    """Post every unposted BhphPayment for one tenant.

    Iterates :func:`detect_unposted_bhph_payments`. Each row is
    posted in its own :func:`post_bhph_payment_journal` transaction —
    a failure on row N does not roll back rows 1..N-1 (progress is
    preserved). Failures are logged and counted in the returned dict.

    Returns a summary matching M13.2's
    :func:`post_all_unposted_costs_for_dealership` shape exactly:
    ``{"dealership_id": ..., "dealership_slug": ..., "as_of": ...,
    "posted_count": ..., "failed_count": ..., "posted_ids": [...],
    "failed_ids": [...]}``.
    """
    effective = now or timezone.now()
    unposted = list(detect_unposted_bhph_payments(dealership=dealership))
    posted_ids: list[int] = []
    failed_ids: list[int] = []

    for payment in unposted:
        try:
            post_bhph_payment_journal(
                dealership=dealership,
                bhph_payment=payment,
                posted_at=effective,
            )
            posted_ids.append(payment.pk)
        except Exception:
            _LOGGER.exception(
                "accounting.bhph_payment.post failed for BhphPayment pk=%s",
                payment.pk,
            )
            failed_ids.append(payment.pk)

    _LOGGER.info(
        "accounting.bhph_payment.detector dealership=%s posted=%d failed=%d as_of=%s",
        dealership.slug,
        len(posted_ids),
        len(failed_ids),
        effective.isoformat(),
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": dealership.slug,
        "as_of": effective.isoformat(),
        "posted_count": len(posted_ids),
        "failed_count": len(failed_ids),
        "posted_ids": posted_ids,
        "failed_ids": failed_ids,
    }
