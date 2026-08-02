"""Milestone 10 · Increment 1 (SESSION_106) — F&I service surface.

The one place all F&I write/read verbs live. Answers the Milestone
10 Q1 substrate question (*"what credit-app data do we capture, and
how do we retain it under legal safeguards?"*) via the credit-app
intake verb + retention-clock computation.

Layer discipline mirrors ``services.sale`` / ``services.delivery``:
identity + authorization live in the view layer; data-scoping +
business semantics live here. Every write function accepts an
explicit ``dealership`` kwarg and refuses to touch a parent (lead
or sale) in another tenant
(:class:`CrossTenantCreditApplicationError`).

Verbs shipped at M10.1:

- :func:`record_credit_application` — write path. Creates a
  :class:`CreditApplication` and computes ``retention_expires_at``
  from ``captured_at`` + retention policy.
- :func:`get_credit_application` — pure read verb by pk (tenant-
  scoped). Never mutates.
- :func:`compute_retention_expires_at` — pure verb. Returns
  ``captured_at + CREDIT_APP_RETENTION_YEARS``. Callable outside
  the write path so the invariant "retention window = 7 years from
  capture" is testable in isolation.

M10.2-M10.7 verbs (deal structure, lender submission, stipulation
tracking, contract, funding, chargeback) will land here as
sibling modules (``deal_structure.py``, ``lender.py``,
``stipulation.py``, ``contract.py``, ``funding.py``,
``chargeback.py``) — same pattern as ``services.analytics/`` from
M8.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §7 M10.1 for the
contract.
"""

from __future__ import annotations

from .credit_application import (
    CrossTenantCreditApplicationError,
    compute_retention_expires_at,
    get_credit_application,
    record_credit_application,
)
from .deal_structure import (
    CrossTenantDealStructureError,
    debt_to_income,
    get_deal_structure,
    loan_to_value,
    payment_to_income,
    record_deal_structure,
    recompute_ratios,
)
from .lender import (
    CrossTenantLenderSubmissionError,
    DuplicateLenderProgramError,
    get_lender_submission,
    list_active_lender_programs,
    list_submissions_for_deal_structure,
    record_lender_program,
    record_lender_submission,
    update_lender_submission_status,
)
from .stipulation import (
    CrossTenantStipulationError,
    get_stipulation,
    list_stipulations_for_submission,
    record_stipulation,
    update_stipulation_state,
)
from .contract import (
    ContractAlreadyVoidedError,
    CrossTenantContractError,
    get_contract,
    list_products_for_contract,
    record_back_end_product,
    record_contract,
    sign_contract,
    void_contract,
)
from .funding import (
    CrossTenantFundingError,
    FundingAlreadyExistsError,
    get_funding,
    mark_funded,
    record_funding,
)
from .chargeback import (
    CrossTenantChargebackError,
    get_chargeback,
    net_realized,
    record_chargeback,
)

__all__ = [
    # M10.1 — credit application
    "CrossTenantCreditApplicationError",
    "compute_retention_expires_at",
    "get_credit_application",
    "record_credit_application",
    # M10.2 — deal structure + ratio verbs
    "CrossTenantDealStructureError",
    "debt_to_income",
    "get_deal_structure",
    "loan_to_value",
    "payment_to_income",
    "record_deal_structure",
    "recompute_ratios",
    # M10.3 — lender catalog + submission
    "CrossTenantLenderSubmissionError",
    "DuplicateLenderProgramError",
    "get_lender_submission",
    "list_active_lender_programs",
    "list_submissions_for_deal_structure",
    "record_lender_program",
    "record_lender_submission",
    "update_lender_submission_status",
    # M10.4 — stipulation lifecycle
    "CrossTenantStipulationError",
    "get_stipulation",
    "list_stipulations_for_submission",
    "record_stipulation",
    "update_stipulation_state",
    # M10.5 — contract + back-end products + funding
    "ContractAlreadyVoidedError",
    "CrossTenantContractError",
    "CrossTenantFundingError",
    "FundingAlreadyExistsError",
    "get_contract",
    "get_funding",
    "list_products_for_contract",
    "mark_funded",
    "record_back_end_product",
    "record_contract",
    "record_funding",
    "sign_contract",
    "void_contract",
    # M10.6 — chargeback + net_realized
    "CrossTenantChargebackError",
    "get_chargeback",
    "net_realized",
    "record_chargeback",
]
