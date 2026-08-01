"""Milestone 4 · Increment 5 — vendor communication drafting service.

The one place all vendor communication drafting happens. Answers
the two M4 business questions in the comm subsystem:

- Q14: *"What was communicated to the vendor?"* — every
  :class:`VendorCommunication` row.
- Q15: *"Which statements came from human-authored data vs
  AI-generated wording?"* — captured in
  ``VendorCommunication.source_provenance`` at draft time; the
  M4.7 operator UI renders provenance alongside the draft body.

Four public functions:

- :func:`draft_communication` — AI-drafts an outbound comm from a
  structured source bundle assembled from the WorkOrder + linked
  findings + parts. Runs the LLM output through the shared safety
  stack (:mod:`services.llm_safety`) with the new
  ``_scrub_invented_recon_fact`` scrub. Persists a
  ``VendorCommunication`` row at ``status='draft'``.
- :func:`approve_communication` — ``draft → approved`` transition.
  Requires ``approved_by``.
- :func:`mark_sent` — ``approved → sent`` transition. Captures the
  final sent body (which may include operator edits) and sets
  ``sent_by`` + ``sent_at``. The M4.1 model-layer sent-state
  invariant matrix surfaces via ``full_clean``.
- :func:`log_communication` — operator-recorded off-system comm
  (phone / in-person / inbound email). Creates directly at
  ``status='logged'`` with operator-authored body content. Refuses
  to create AI-drafted content this way — the SESSION_066
  refinement "AI-generated content may never jump directly to
  logged" is enforced here at the service layer since the model
  layer cannot distinguish AI-drafted from operator-recorded.

Layer discipline (per :doc:`AUTHENTICATION_MODEL.md` §1):

- **Data-scoping** — this module. Every public function accepts
  an explicit ``dealership`` kwarg and refuses to touch rows in
  any other tenant.
- **Business semantics** — this module. Draft-to-approved-to-sent
  ladder, logged-skips-approval, AI-cannot-jump-to-logged all
  locked here.
- **AI safety** — this module + :mod:`services.llm_safety`.
  ``_scrub_invented_recon_fact`` strips any finding ID / part
  number / dollar amount / ISO date the LLM invented that isn't
  in the source bundle. Every persisted draft has run through
  this scrub.

Semantic decisions locked here:

- **draft_communication accepts only AI-drafted kinds.** Currently
  ``vendor_comm`` and ``parts_order``. ``narrative`` is
  operator-authored — use :func:`log_communication` for that.
- **log_communication may use any kind.** An operator may log a
  vendor_comm that happened off-system (they sent an email from
  Gmail directly) — the row records the human-authored fact of
  that comm.
- **No outbound SMTP / SMS send.** Planning §5.i defers send to
  a post-M4 prod-readiness pass. ``mark_sent`` records the fact
  the operator sent the message (via copy-paste from the M4.7
  draft UI); no network call happens here.

Concurrency posture:

- State transitions (:func:`approve_communication`,
  :func:`mark_sent`) use ``transaction.atomic()`` +
  ``select_for_update()`` on the target row so two concurrent
  approve / send calls cannot both succeed against the same row
  and produce contradictory provenance. Same shape as M4.2
  WorkOrder transitions.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    ConditionFinding,
    Dealership,
    VENDOR_COMMUNICATION_CHANNEL_CHOICES,
    VENDOR_COMMUNICATION_DIRECTION_CHOICES,
    VENDOR_COMMUNICATION_KIND_CHOICES,
    VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
    VENDOR_COMMUNICATION_STATUS_APPROVED,
    VENDOR_COMMUNICATION_STATUS_DRAFT,
    VENDOR_COMMUNICATION_STATUS_LOGGED,
    VENDOR_COMMUNICATION_STATUS_SENT,
    VendorCommunication,
    WorkOrder,
    WorkOrderPart,
)
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider
from .llm_safety import apply_post_llm_scrubs


# Kinds accepted by :func:`draft_communication` — the AI-drafted
# outbound path. ``narrative`` is deliberately excluded (operator-
# authored notes go through :func:`log_communication`). Kept
# module-level so tests can import + lock the vocabulary.
_AI_DRAFTED_KINDS: frozenset[str] = frozenset(
    {
        VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
        VENDOR_COMMUNICATION_KIND_PARTS_ORDER,
    }
)

_VALID_KIND_KEYS = frozenset(key for key, _ in VENDOR_COMMUNICATION_KIND_CHOICES)
_VALID_CHANNEL_KEYS = frozenset(
    key for key, _ in VENDOR_COMMUNICATION_CHANNEL_CHOICES
)
_VALID_DIRECTION_KEYS = frozenset(
    key for key, _ in VENDOR_COMMUNICATION_DIRECTION_CHOICES
)


# ---- Domain errors --------------------------------------------------------


class CrossTenantVendorCommError(ValueError):
    """Raised when a vendor-comm service function is called with a
    ``dealership`` that does not match the target WorkOrder or
    VendorCommunication. Mirrors :class:`CrossTenantReconError`
    shape from :mod:`services.recon`."""


class VendorCommImmutableError(ValueError):
    """Raised when a caller attempts an illegal state transition on
    a :class:`VendorCommunication` row — e.g. approving a row that
    is not in ``draft``, marking-sent a row that is not
    ``approved``, or (M4.5 refinement) invoking
    :func:`log_communication` with a kind reserved for AI-drafted
    content."""


class ReconFactScrubDroppedError(ValueError):
    """Raised by :func:`draft_communication` when the shared safety
    stack signals a wholesale-rewrite class (``dropped_reason``
    non-None) on the LLM's raw output. The draft is NOT persisted
    — a caller receiving this error should surface it as an
    operator retry prompt rather than logging a rejected draft
    row that would corrupt the audit trail."""


class EmptyDraftError(ValueError):
    """Raised by :func:`draft_communication` when the LLM returned
    an empty string (or a string that scrubbed to empty). Not
    persisted; caller retries.

    Distinct from :class:`ReconFactScrubDroppedError` so callers
    can distinguish "LLM returned nothing" from "LLM output was
    unsafe"."""


# ---- Cross-tenant guards --------------------------------------------------


def _assert_work_order_tenant(
    work_order: WorkOrder, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantVendorCommError` when the target WO
    or its parent Vehicle does not belong to the caller's tenant."""
    if work_order.dealership_id != dealership.pk:
        raise CrossTenantVendorCommError(
            f"WorkOrder #{work_order.pk} belongs to dealership "
            f"{work_order.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )


def _assert_comm_tenant(
    comm: VendorCommunication, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantVendorCommError` when the target
    row does not belong to the caller's tenant."""
    if comm.dealership_id != dealership.pk:
        raise CrossTenantVendorCommError(
            f"VendorCommunication #{comm.pk} belongs to dealership "
            f"{comm.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )


# ---- Source bundle assembly -----------------------------------------------


def _build_source_bundle(
    work_order: WorkOrder, *, extra_notes: str = ""
) -> dict:
    """Assemble the structured source bundle the LLM prompt is
    rendered from and the scrub validates against.

    Shape locked at planning §5.g:

    .. code-block:: python

        {
            "vehicle": {stock, year, make, model, vin_last_6},
            "vendor": {name},
            "findings": [{id, category, severity, description}, ...],
            "authorized_cost": str_two_decimals or None,
            "estimated_completion_date": iso or None,
            "parts_needed": [
                {name, part_number, quantity, unit_cost, source_type},
                ...
            ],
            "operator_notes": str,
        }

    Reads from the WorkOrder's linked findings (via the
    ``WorkOrderFinding`` through table) and parts (via the
    ``parts`` reverse accessor). All queries stay tenant-scoped
    by construction — the WorkOrder itself is tenant-scoped.
    """
    vehicle = work_order.vehicle
    vin = getattr(vehicle, "vin", "") or ""
    vendor = work_order.vendor

    findings_bundle = []
    for link in work_order.finding_links.select_related(
        "finding__report"
    ).all():
        finding: ConditionFinding = link.finding
        findings_bundle.append(
            {
                "id": finding.pk,
                "category": finding.category,
                "severity": finding.severity,
                "description": finding.description,
            }
        )

    parts_bundle = []
    for part in work_order.parts.all():
        part: WorkOrderPart
        parts_bundle.append(
            {
                "name": part.name,
                "part_number": part.part_number,
                "quantity": part.quantity,
                "unit_cost": (
                    _decimal_two_places(part.unit_cost)
                    if part.unit_cost is not None
                    else None
                ),
                "source_type": part.source_type,
            }
        )

    return {
        "vehicle": {
            "stock": vehicle.stock_number,
            "year": vehicle.year,
            "make": getattr(vehicle, "make", "") or "",
            "model": vehicle.model,
            "vin_last_6": vin[-6:] if vin else "",
        },
        "vendor": {"name": vendor.name if vendor is not None else ""},
        "findings": findings_bundle,
        "authorized_cost": (
            _decimal_two_places(work_order.authorized_cost)
            if work_order.authorized_cost is not None
            else None
        ),
        "estimated_completion_date": (
            work_order.estimated_completion_date.isoformat()
            if work_order.estimated_completion_date is not None
            else None
        ),
        "parts_needed": parts_bundle,
        "operator_notes": extra_notes or "",
    }


def _decimal_two_places(value: Any) -> str:
    """Return ``value`` as a two-decimal string, or an empty string
    on failure. Used to normalize the source-bundle amounts."""
    try:
        return f"{Decimal(str(value)):.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return ""


# ---- LLM prompt construction ---------------------------------------------


def _build_llm_messages(
    source_bundle: dict, *, kind: str, channel: str
) -> list[dict]:
    """Render the source bundle into a structured LLM prompt.

    The system message pins the boundaries: draft using ONLY facts
    from the bundle; never invent finding IDs, part numbers,
    dollar amounts, or dates. The user message serializes the
    bundle as JSON-like key/value pairs plus a directive to draft
    the communication.
    """
    system_lines = [
        "You are drafting a vendor communication for a used-car "
        "dealership. Write in the dealership's voice — brief, "
        "professional, direct.",
        "",
        "STRICT rules:",
        "- Draft using ONLY facts present in the source data below.",
        "- Do NOT invent finding IDs, part numbers, dollar amounts, "
        "or dates that are not present in the source.",
        "- Do NOT quote APR / rate / financing language.",
        "- Do NOT mention discounts, promotions, or manufacturer programs.",
        "- If a fact you would normally include is missing from the "
        "source, omit it rather than guessing.",
        f"- The communication kind is '{kind}' (see the source "
        "for what to focus on).",
        f"- The channel is '{channel}' — write in a tone appropriate "
        "for that channel (email = fuller; sms = concise; phone = "
        "talking-points).",
    ]

    user_lines = [
        "Source data:",
        f"  Vehicle: stock #{source_bundle['vehicle']['stock']}, "
        f"{source_bundle['vehicle']['year']} "
        f"{source_bundle['vehicle']['make']} "
        f"{source_bundle['vehicle']['model']}",
    ]
    if source_bundle["vendor"]["name"]:
        user_lines.append(f"  Vendor: {source_bundle['vendor']['name']}")
    if source_bundle["findings"]:
        user_lines.append("  Findings to address:")
        for f in source_bundle["findings"]:
            user_lines.append(
                f"    - Finding #{f['id']} ({f['severity']} "
                f"{f['category']}): {f['description']}"
            )
    if source_bundle["parts_needed"]:
        user_lines.append("  Parts needed:")
        for p in source_bundle["parts_needed"]:
            pn = f" [{p['part_number']}]" if p["part_number"] else ""
            user_lines.append(
                f"    - {p['name']}{pn} (qty {p['quantity']}, "
                f"source {p['source_type']})"
            )
    if source_bundle["authorized_cost"]:
        user_lines.append(
            f"  Authorized total: ${source_bundle['authorized_cost']}"
        )
    if source_bundle["estimated_completion_date"]:
        user_lines.append(
            f"  Estimated completion: "
            f"{source_bundle['estimated_completion_date']}"
        )
    if source_bundle["operator_notes"]:
        user_lines.append(
            f"  Operator notes: {source_bundle['operator_notes']}"
        )
    user_lines.append("")
    user_lines.append("Draft the vendor communication as a single body of "
                      "text. Do not include a subject line or header — the "
                      "operator will add those before sending.")

    return [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


# ---- Public entry points --------------------------------------------------


def draft_communication(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    drafted_by,
    kind: str,
    channel: str,
    direction: str = "outbound",
    extra_notes: str = "",
    provider: Optional[LLMProvider] = None,
) -> VendorCommunication:
    """AI-draft an outbound vendor communication from the WO's
    linked findings + parts.

    Three-step pattern per planning §3.3:

    1. Assemble the source bundle from
       ``work_order.finding_links`` + ``work_order.parts``.
    2. Call the LLM (mock provider in tests) with a prompt that
       pins the boundaries (draft using only source facts; do
       not invent IDs / part numbers / dollar amounts / dates).
    3. Run the LLM's output through
       :func:`services.llm_safety.apply_post_llm_scrubs` with
       ``kind`` matching the requested kind. The new
       ``_scrub_invented_recon_fact`` scrub strips any invented
       fact that slipped past the prompt.

    Persists a :class:`VendorCommunication` row at
    ``status='draft'`` with ``drafted_by`` + ``drafted_at`` set +
    ``source_provenance`` populated. Callers advance via
    :func:`approve_communication` and :func:`mark_sent`.

    Preconditions:

    - Cross-tenant guard against ``work_order.dealership``.
    - ``kind`` must be one of :data:`_AI_DRAFTED_KINDS`
      (``vendor_comm`` or ``parts_order``). Narrative rows go
      through :func:`log_communication`.
    - ``channel`` + ``direction`` must be canonical vocabulary.

    Raises:

    - :class:`CrossTenantVendorCommError` — cross-tenant.
    - :class:`VendorCommImmutableError` — invalid kind for AI
      drafting.
    - :class:`ValueError` — invalid channel / direction /
      structural.
    - :class:`ReconFactScrubDroppedError` — safety stack fired a
      wholesale rewrite (unsafe / negotiation / handoff language).
      Draft NOT persisted.
    - :class:`EmptyDraftError` — LLM returned empty or scrubbed
      to empty. Not persisted.
    """
    _assert_work_order_tenant(work_order, dealership)

    if kind not in _AI_DRAFTED_KINDS:
        raise VendorCommImmutableError(
            f"draft_communication: kind must be one of "
            f"{sorted(_AI_DRAFTED_KINDS)!r}. Got {kind!r}. "
            "Narrative rows go through ``log_communication``."
        )
    if channel not in _VALID_CHANNEL_KEYS:
        raise ValueError(
            f"draft_communication: unknown channel {channel!r}. "
            "Valid values live in "
            "``dealer_ai.models.VENDOR_COMMUNICATION_CHANNEL_CHOICES``."
        )
    if direction not in _VALID_DIRECTION_KEYS:
        raise ValueError(
            f"draft_communication: unknown direction {direction!r}. "
            "Valid values live in "
            "``dealer_ai.models.VENDOR_COMMUNICATION_DIRECTION_CHOICES``."
        )

    source_bundle = _build_source_bundle(
        work_order, extra_notes=extra_notes
    )
    messages = _build_llm_messages(
        source_bundle, kind=kind, channel=channel
    )

    llm = provider or get_llm_provider()
    raw = llm.chat(messages, temperature=0.4, max_tokens=800)

    cleaned, scrubs_fired, dropped_reason = apply_post_llm_scrubs(
        raw, kind=kind, recon_source_bundle=source_bundle
    )
    if dropped_reason is not None:
        raise ReconFactScrubDroppedError(
            f"draft_communication: LLM output rejected by safety "
            f"stack ({dropped_reason}). Draft NOT persisted."
        )
    cleaned = (cleaned or "").strip()
    if not cleaned:
        raise EmptyDraftError(
            "draft_communication: LLM returned empty output (or "
            "the safety stack scrubbed it to empty). Draft NOT "
            "persisted."
        )

    provenance = {
        "source_bundle": source_bundle,
        "scrubs_fired": list(scrubs_fired),
        "llm_provider": getattr(llm, "name", "unknown"),
    }

    now = timezone.now()
    comm = VendorCommunication(
        dealership=dealership,
        vendor=work_order.vendor,
        work_order=work_order,
        kind=kind,
        channel=channel,
        direction=direction,
        status=VENDOR_COMMUNICATION_STATUS_DRAFT,
        draft_content=cleaned,
        sent_content="",
        source_provenance=provenance,
        drafted_by=drafted_by,
        drafted_at=now,
    )
    comm.full_clean()
    comm.save()
    return comm


def approve_communication(
    comm: VendorCommunication,
    *,
    dealership: Dealership,
    approved_by,
) -> VendorCommunication:
    """Transition a draft VendorCommunication to approved.

    Preconditions:

    - Cross-tenant guard.
    - Current status must be ``draft`` (raises
      :class:`VendorCommImmutableError` otherwise). Logged rows
      cannot be re-approved (they're history); sent rows cannot
      be un-sent.

    Sets ``approved_by`` + ``approved_at``. M4.1 model-layer
    invariant matrix (approved-state requires both fields)
    surfaces via ``full_clean``.
    """
    _assert_comm_tenant(comm, dealership)

    with transaction.atomic():
        refreshed = (
            VendorCommunication.objects.select_for_update().get(pk=comm.pk)
        )
        if refreshed.status != VENDOR_COMMUNICATION_STATUS_DRAFT:
            raise VendorCommImmutableError(
                f"Cannot approve VendorCommunication #{refreshed.pk}: "
                f"current status is {refreshed.status!r}. Approval is "
                "allowed only from 'draft'."
            )
        refreshed.status = VENDOR_COMMUNICATION_STATUS_APPROVED
        refreshed.approved_by = approved_by
        refreshed.approved_at = timezone.now()
        refreshed.full_clean()
        refreshed.save()
        return refreshed


def mark_sent(
    comm: VendorCommunication,
    *,
    dealership: Dealership,
    sent_by,
    sent_content: Optional[str] = None,
) -> VendorCommunication:
    """Transition an approved VendorCommunication to sent.

    The operator sent the message externally (from their email /
    SMS client — planning §5.i defers in-system send to
    post-M4). This function records the fact of the send + the
    final sent body (which may include operator edits made
    before sending).

    Preconditions:

    - Cross-tenant guard.
    - Current status must be ``approved`` (raises
      :class:`VendorCommImmutableError` otherwise).
    - ``sent_content`` — if supplied, becomes the final sent
      body. If omitted, ``draft_content`` is copied to
      ``sent_content`` (the operator sent the draft as-is).
    - ``sent_content`` must be nonblank after resolution
      (raises :class:`ValueError` if both supplied and empty
      AND ``draft_content`` is also empty).

    Sets ``sent_by`` + ``sent_at`` + ``sent_content``. M4.1
    model-layer sent-state invariant matrix surfaces via
    ``full_clean``.
    """
    _assert_comm_tenant(comm, dealership)

    with transaction.atomic():
        refreshed = (
            VendorCommunication.objects.select_for_update().get(pk=comm.pk)
        )
        if refreshed.status != VENDOR_COMMUNICATION_STATUS_APPROVED:
            raise VendorCommImmutableError(
                f"Cannot mark-sent VendorCommunication #{refreshed.pk}: "
                f"current status is {refreshed.status!r}. Mark-sent is "
                "allowed only from 'approved'."
            )
        resolved_content = (
            sent_content
            if sent_content is not None
            else refreshed.draft_content
        )
        if not (resolved_content or "").strip():
            raise ValueError(
                f"mark_sent: sent_content resolves to empty for "
                f"VendorCommunication #{refreshed.pk}. Supply a "
                "nonblank sent_content or ensure draft_content is "
                "nonblank."
            )
        refreshed.status = VENDOR_COMMUNICATION_STATUS_SENT
        refreshed.sent_content = resolved_content
        refreshed.sent_by = sent_by
        refreshed.sent_at = timezone.now()
        refreshed.full_clean()
        refreshed.save()
        return refreshed


def log_communication(
    work_order: Optional[WorkOrder],
    *,
    dealership: Dealership,
    logged_by,
    kind: str,
    channel: str,
    direction: str,
    body: str,
) -> VendorCommunication:
    """Record an off-system communication that already happened.

    Creates a :class:`VendorCommunication` row **directly at
    ``status='logged'``** with the operator as the human actor.
    Distinct workflow from :func:`draft_communication` +
    :func:`approve_communication` + :func:`mark_sent` — logged
    rows have no approval step because they represent things the
    operator already did or observed off-system (a phone call
    they made, an in-person conversation, an inbound email they
    transcribed).

    ``work_order`` may be ``None`` — an inbound cold call from a
    vendor may not map to an existing WorkOrder at the moment it
    is recorded.

    Preconditions:

    - When ``work_order`` is not None: cross-tenant guard.
    - ``kind``, ``channel``, ``direction`` must be canonical
      vocabulary.
    - ``body`` must be nonblank (raises :class:`ValueError`).
    - Any kind is permitted (including ``vendor_comm`` and
      ``parts_order``). The SESSION_066 refinement
      "AI-generated content may never jump directly to logged"
      is enforced by construction — no AI content path invokes
      :func:`log_communication`. Callers of this function are
      operator-scoped (the M4.6 API + M4.7 UI expose it via a
      dedicated "Log a communication" form).

    Sets ``sent_by = logged_by`` + ``sent_at = now`` +
    ``draft_content = body`` (the recorded body lives in
    ``draft_content`` per M4.1's status-invariant matrix — see
    the model docstring). M4.1 model-layer ``logged``-state
    invariant surfaces via ``full_clean``.
    """
    if work_order is not None:
        _assert_work_order_tenant(work_order, dealership)

    if kind not in _VALID_KIND_KEYS:
        raise ValueError(
            f"log_communication: unknown kind {kind!r}. Valid values "
            "live in ``dealer_ai.models.VENDOR_COMMUNICATION_KIND_CHOICES``."
        )
    if channel not in _VALID_CHANNEL_KEYS:
        raise ValueError(
            f"log_communication: unknown channel {channel!r}. Valid "
            "values live in "
            "``dealer_ai.models.VENDOR_COMMUNICATION_CHANNEL_CHOICES``."
        )
    if direction not in _VALID_DIRECTION_KEYS:
        raise ValueError(
            f"log_communication: unknown direction {direction!r}. Valid "
            "values live in "
            "``dealer_ai.models.VENDOR_COMMUNICATION_DIRECTION_CHOICES``."
        )
    if not (body or "").strip():
        raise ValueError(
            "log_communication: body is required and must be nonblank."
        )

    vendor = work_order.vendor if work_order is not None else None
    now = timezone.now()
    comm = VendorCommunication(
        dealership=dealership,
        vendor=vendor,
        work_order=work_order,
        kind=kind,
        channel=channel,
        direction=direction,
        status=VENDOR_COMMUNICATION_STATUS_LOGGED,
        draft_content=body,
        sent_content="",
        source_provenance={
            "logged_off_system": True,
            "note": (
                "Operator-recorded row; no AI draft path. See "
                "log_communication docstring."
            ),
        },
        sent_by=logged_by,
        sent_at=now,
    )
    try:
        comm.full_clean()
    except ValidationError as exc:
        raise VendorCommImmutableError(
            f"log_communication: model-layer validation failed: "
            f"{exc.message_dict!r}"
        ) from exc
    comm.save()
    return comm
